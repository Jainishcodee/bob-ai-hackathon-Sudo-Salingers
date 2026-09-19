"""Signal emergence timeline — *when* would this signal first have been flagged, and what hid it?

For a drug–reaction pair, rebuild the 2x2 table year by year using FDA *receive date*
(what the agency had in hand by 31 December of each year), then compute:

* the **yearly** PRR — that year's reports only (noisy, shows trend);
* the **cumulative** PRR — all reports received up to and including that year, which is
  what a pharmacovigilance scientist running the screen in that year would actually see;
* optionally a **masking-corrected** cumulative PRR, with one or more products removed
  from the comparator background.

Masking is a documented failure mode of disproportionality methods (Maignen et al. 2014,
Wang et al. 2010): when one drug's reporting wave makes up most of a reaction's reports,
the background rate inflates and the same reaction is hidden for every other drug. In
FAERS, Vioxx litigation reports were ~70% of ALL myocardial-infarction reports in 2005–06,
which is exactly why Avandia's MI signal does not appear until 2008 under the standard
screen — and appears in 2006 once Vioxx is excluded.

Exclusion can be **manual** (``exclude=["rofecoxib", "vioxx"]``) or **rule-based**
(``exclude=["auto"]``). The automatic rule is applied *prospectively, with no look-ahead*: in
year Y only products that had already reached the alert share of the reaction's reports in some
year <= Y are excluded. Anything else would let knowledge of the future leak into a claim about
what was detectable in the past.

**Publicity-stimulated reporting flag:** separately from masking, a row is marked
``stimulated_reporting=True`` when the reaction's *share of the drug's own reports* jumps to
≥ 2× its pre-action mean once a regulatory action has occurred. This is a convention (not a
published standard) for flagging years where media and litigation are likely driving reports
rather than a genuine new risk. The flag is computed entirely from data already fetched; it
adds zero API calls.

Analogy: the "first seen" field in error monitoring (Sentry), or a control chart in
manufacturing SPC — it turns a snapshot into a detection history.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd
import yaml

from pharos.faers.client import OpenFDAClient
from pharos.signals.masking import alias_group
from pharos.signals.stats import EVANS_2001, ContingencyTable, SignalCriteria, evaluate

OPENFDA_FIRST_YEAR = 2004  # FAERS data in openFDA begins 2004 Q1
ACTIONS_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "samples" / "regulatory_actions.yaml"
MASKING_ALERT_SHARE_PCT = 25.0  # one drug >= this share of a reaction's reports in a year -> masking risk


@dataclass
class RegulatoryAction:
    date: date
    label: str
    source: str = ""

    @property
    def year(self) -> int:
        return self.date.year

    def as_dict(self) -> dict:
        return {"date": self.date.isoformat(), "year": self.year, "label": self.label, "source": self.source}


@dataclass
class TimelineResult:
    drug: str
    names: list[str]
    reaction: str
    start_year: int
    end_year: int
    table: pd.DataFrame
    criteria: SignalCriteria
    first_flag_year_cumulative: int | None
    first_flag_year_yearly: int | None
    exclude: list[str] = field(default_factory=list)
    auto_excluded: bool = False
    exclusion_schedule: list[dict] = field(default_factory=list)  # [{from_year, names}] — when each product entered
    first_flag_year_adjusted: int | None = None
    actions: list[RegulatoryAction] = field(default_factory=list)
    generated_at: str = ""
    source: str = ""

    # ---------------------------------------------------------------- derived

    @property
    def first_action(self) -> RegulatoryAction | None:
        return min(self.actions, key=lambda a: a.date) if self.actions else None

    @property
    def stimulated_years(self) -> list[int]:
        """Years flagged as likely publicity-stimulated (share >= 2× pre-action baseline)."""
        if "stimulated_reporting" not in self.table.columns or self.table.empty:
            return []
        return [int(y) for y in self.table.loc[self.table["stimulated_reporting"], "year"]]

    def _lead(self, flag_year: int | None) -> int | None:
        if flag_year is None or self.first_action is None:
            return None
        return self.first_action.year - flag_year

    @property
    def lead_time_years(self) -> int | None:
        """Years between the cumulative first-flag and the first regulatory action (positive = earlier)."""
        return self._lead(self.first_flag_year_cumulative)

    @property
    def lead_time_years_adjusted(self) -> int | None:
        return self._lead(self.first_flag_year_adjusted)

    @property
    def max_masking(self) -> dict | None:
        """The single worst masking year: {year, drug, share_pct}."""
        if "top_contributor_share_pct" not in self.table or self.table.empty:
            return None
        row = self.table.loc[self.table["top_contributor_share_pct"].idxmax()]
        if not row["top_contributor"]:
            return None
        return {"year": int(row["year"]), "drug": row["top_contributor"], "share_pct": float(row["top_contributor_share_pct"])}

    # ---------------------------------------------------------------- text

    def _lead_sentence(self, flag_year: int | None, lead: int | None) -> str:
        fa = self.first_action
        if fa is None or flag_year is None:
            return ""
        if fa.year < self.start_year:
            return (f" The first regulatory action — {fa.label} ({fa.date.isoformat()}) — predates the data window "
                    f"({self.start_year}), so this is a retrospective check, not a detection claim.")
        if lead is not None and lead > 0:
            return f" That is {lead} year{'s' if lead != 1 else ''} BEFORE the first regulatory action — {fa.label} ({fa.date.isoformat()})."
        if lead == 0:
            return f" The first regulatory action came the same year — {fa.label} ({fa.date.isoformat()})."
        return (f" That is {-lead} year{'s' if lead != -1 else ''} AFTER the first regulatory action — {fa.label} "
                f"({fa.date.isoformat()}). The standard screen did not lead here.")

    def _exclusion_phrase(self) -> str:
        if not self.auto_excluded:
            return "Excluding " + ", ".join(self.exclude) + " from the background"
        steps = "; ".join(f"{', '.join(s['names'])} from {s['from_year']}" for s in self.exclusion_schedule)
        return (f"Applying the >={MASKING_ALERT_SHARE_PCT:.0f}% exclusion rule prospectively, with no look-ahead "
                f"({steps})")

    def headline(self) -> str:
        pair = f"{self.drug} × {self.reaction}"
        if self.first_flag_year_cumulative is None:
            s = f"{pair}: cumulative PRR never met the signal criteria between {self.start_year} and {self.end_year}."
        else:
            row = self.table.set_index("year").loc[self.first_flag_year_cumulative]
            s = (f"{pair}: standard cumulative PRR first met the signal criteria in {self.first_flag_year_cumulative} "
                 f"(n={int(row.cum_a)}, PRR={row.cum_prr:.2f}, chi²={row.cum_chi2:.0f}).")
            s += self._lead_sentence(self.first_flag_year_cumulative, self.lead_time_years)

        mm = self.max_masking
        if mm and mm["share_pct"] >= MASKING_ALERT_SHARE_PCT:
            s += (f" MASKING ALERT: in {mm['year']}, {mm['drug']} accounted for {mm['share_pct']:.0f}% of all "
                  f"{self.reaction} reports in FAERS, inflating the background this drug is compared against.")

        if self.exclude:
            if self.first_flag_year_adjusted is None:
                s += f" {self._exclusion_phrase()}, the criteria were still never met."
            else:
                row = self.table.set_index("year").loc[self.first_flag_year_adjusted]
                s += (f" {self._exclusion_phrase()}, the signal first met the criteria in {self.first_flag_year_adjusted} "
                      f"(PRR={row.cum_prr_adj:.2f}, chi²={row.cum_chi2_adj:.0f}).")
                s += self._lead_sentence(self.first_flag_year_adjusted, self.lead_time_years_adjusted)
                if self.first_flag_year_cumulative and self.first_flag_year_adjusted < self.first_flag_year_cumulative:
                    gained = self.first_flag_year_cumulative - self.first_flag_year_adjusted
                    s += f" Masking correction brings detection forward by {gained} year{'s' if gained != 1 else ''}."
        elif self.auto_excluded:
            s += " The automatic rule found no product above the exclusion threshold, so no correction was applied."

        sy = self.stimulated_years
        if sy:
            fa = self.first_action
            action_year = fa.year if fa else sy[0]
            s += (f" From {sy[0]} onward this reaction's share of the drug's reports is at least double its"
                  f" pre-{action_year} level — consistent with publicity-stimulated reporting;"
                  f" treat later PRRs with caution.")
        return s

    def as_dict(self) -> dict:
        return {
            "drug": self.drug,
            "names_searched": self.names,
            "reaction": self.reaction,
            "start_year": self.start_year,
            "end_year": self.end_year,
            "criteria": self.criteria.as_dict(),
            "first_flag_year_cumulative": self.first_flag_year_cumulative,
            "first_flag_year_yearly": self.first_flag_year_yearly,
            "excluded_from_background": self.exclude,
            "exclusion_selected_automatically": self.auto_excluded,
            "exclusion_schedule": self.exclusion_schedule,
            "first_flag_year_masking_corrected": self.first_flag_year_adjusted,
            "regulatory_actions": [a.as_dict() for a in self.actions],
            "lead_time_years_vs_first_action": self.lead_time_years,
            "lead_time_years_vs_first_action_masking_corrected": self.lead_time_years_adjusted,
            "worst_masking_year": self.max_masking,
            "stimulated_reporting_years": self.stimulated_years,
            "stimulated_reporting_note": (
                "A year is flagged 'stimulated_reporting' when it falls on or after the first regulatory action "
                "AND the reaction's share of the drug's reports is >= 2× the mean share in pre-action years. "
                "This is a convention (not a published standard) for identifying years likely driven by publicity "
                "or litigation rather than new pharmacological risk. Treat PRRs in these years with caution."
            ),
            "headline": self.headline(),
            "rows": self.table.to_dict(orient="records"),
            "generated_at": self.generated_at,
            "data_source": f"openFDA ({self.source})",
            "notes": [
                "Years are FDA receive dates: cumulative PRR in year Y uses only reports the FDA had by 31 Dec Y.",
                "openFDA FAERS data begins in 2004; earlier regulatory actions cannot be evaluated prospectively.",
                "Yearly PRR is noisy for small counts; use the cumulative series for the first-flag claim.",
                "Masking: when one drug dominates a reaction's reports (see top_contributor per year), the background "
                "inflates and hides the same reaction for other drugs.",
                "exclude_drugs='auto' applies the share rule prospectively: a product is excluded in year Y only if it had "
                "already reached the threshold in some year <= Y. No look-ahead.",
                "Reporting is stimulated by publicity and litigation; a sharp late rise often reflects that, not new risk.",
            ],
        }


# ------------------------------------------------------------------ regulatory actions


def load_regulatory_actions(path: Path = ACTIONS_PATH) -> dict[str, list[RegulatoryAction]]:
    if not path.exists():
        return {}
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    out: dict[str, list[RegulatoryAction]] = {}
    for drug, items in (raw.get("drugs") or {}).items():
        acts = []
        for it in items or []:
            d = it["date"]
            d = d if isinstance(d, date) else datetime.strptime(str(d), "%Y-%m-%d").date()
            acts.append(RegulatoryAction(date=d, label=str(it["label"]), source=str(it.get("source", "") or "")))
        out[drug.strip().upper()] = sorted(acts, key=lambda a: a.date)
    return out


def actions_for(names: Iterable[str], path: Path = ACTIONS_PATH) -> list[RegulatoryAction]:
    table = load_regulatory_actions(path)
    for n in names:
        if n.strip().upper() in table:
            return table[n.strip().upper()]
    return []


# ------------------------------------------------------------------ the timeline


def _eval(a: int, drug: int, event: int, total: int, criteria: SignalCriteria):
    if drug <= 0 or total <= 0 or event < a:
        return None
    try:
        return evaluate(ContingencyTable.from_counts(a, drug, event, total), criteria)
    except ValueError:
        return None


def signal_timeline(
    names: str | Iterable[str],
    reaction: str,
    client: OpenFDAClient | None = None,
    start_year: int = OPENFDA_FIRST_YEAR,
    end_year: int | None = None,
    criteria: SignalCriteria = EVANS_2001,
    actions: list[RegulatoryAction] | None = None,
    exclude: Iterable[str] | None = None,
    detect_masking: bool = True,
    top_contributors: int = 3,
) -> TimelineResult:
    """Year-by-year and cumulative disproportionality for one drug–reaction pair.

    Args:
        exclude: products to remove from the comparator background (masking correction). Names are
            expanded to their known brand/generic aliases. The special value ``"auto"`` selects
            maskers by rule, prospectively (see module docstring); it may be combined with names.
        detect_masking: also fetch the top drugs contributing to the reaction's reports each year
            (forced on when ``"auto"`` is used).

    Request budget per year: 4 (total, drug, reaction, drug∧reaction) + 1 if ``detect_masking``
    + 2 per distinct exclusion set active up to that year.
    """
    if isinstance(names, str):
        names = [names]
    names = [n for n in names if n and n.strip()]
    if not names:
        raise ValueError("At least one drug name is required.")
    exclude_in = [e for e in (exclude or []) if e and e.strip()]
    auto = any(e.strip().lower() == "auto" for e in exclude_in)
    if auto:
        detect_masking = True
    client = client or OpenFDAClient()
    end_year = end_year or datetime.now(timezone.utc).year
    start_year = max(start_year, OPENFDA_FIRST_YEAR)
    if end_year < start_year:
        raise ValueError("end_year must be >= start_year")

    own: set[str] = set()
    for n in names:
        own |= alias_group(n)
    manual: set[str] = set()
    for e in exclude_in:
        if e.strip().lower() != "auto":
            manual |= alias_group(e)
    manual -= own

    drug_expr = client.drug_expression(names)
    rx_expr = client.reaction_expression(reaction)
    reaction_u = reaction.strip().upper()

    # ---------------------------------------------------------------- phase 1: the standard screen
    rows: list[dict] = []
    year_maskers: dict[int, set[str]] = {}
    cum = {"a": 0, "drug": 0, "event": 0, "n": 0}
    first_cum = first_year = None
    for year in range(start_year, end_year + 1):
        yr = client.year_expression(year)
        n_total = client.report_count(yr)
        if n_total == 0:  # future / not yet loaded
            continue
        n_drug = client.report_count(client.and_(drug_expr, yr))
        n_event = client.report_count(client.and_(rx_expr, yr))
        a = min(client.report_count(client.and_(drug_expr, rx_expr, yr)), n_drug, n_event)

        yearly = _eval(a, n_drug, n_event, n_total, criteria)
        cum["a"] += a
        cum["drug"] += n_drug
        cum["event"] += n_event
        cum["n"] += n_total
        cumulative = _eval(cum["a"], cum["drug"], cum["event"], cum["n"], criteria)
        if yearly and yearly.is_signal and first_year is None:
            first_year = year
        if cumulative and cumulative.is_signal and first_cum is None:
            first_cum = year

        row = {
            "year": year,
            "n_total": n_total,
            "n_drug": n_drug,
            "n_event": n_event,
            "a": a,
            "share_of_drug_reports_pct": (100 * a / n_drug) if n_drug else 0.0,
            "background_pct": 100 * n_event / n_total,
            "prr_year": yearly.prr if yearly else None,
            "chi2_year": yearly.chi2 if yearly else None,
            "signal_year": bool(yearly.is_signal) if yearly else False,
            "cum_a": cum["a"],
            "cum_drug": cum["drug"],
            "cum_prr": cumulative.prr if cumulative else None,
            "cum_prr_ci_low": cumulative.prr_ci_low if cumulative else None,
            "cum_prr_ci_high": cumulative.prr_ci_high if cumulative else None,
            "cum_chi2": cumulative.chi2 if cumulative else None,
            "cum_signal": bool(cumulative.is_signal) if cumulative else False,
        }

        if detect_masking:
            contributors = [c for c in client.drug_contributors(client.and_(rx_expr, yr), limit=top_contributors + len(own) + 2)
                            if c["term"].upper() not in own][:top_contributors]
            for c in contributors:
                c["share_pct"] = (100 * c["count"] / n_event) if n_event else 0.0
            top = contributors[0] if contributors else None
            year_maskers[year] = {c["term"].upper() for c in contributors if c["share_pct"] >= MASKING_ALERT_SHARE_PCT}
            row.update(
                {
                    "top_contributor": top["term"] if top else "",
                    "top_contributor_share_pct": top["share_pct"] if top else 0.0,
                    "masking_alert": bool(year_maskers[year]),
                    "contributors": contributors,
                }
            )
        rows.append(row)

    # ---------------------------------------------------------------- phase 2: masking correction
    # active[Y] = the exclusion set in force in year Y. Manual names apply to every year; automatic ones
    # enter only in the first year they reach the threshold — never earlier (no look-ahead).
    running: set[str] = set(manual)
    active: dict[int, frozenset[str]] = {}
    schedule: list[dict] = []
    if manual:
        schedule.append({"from_year": rows[0]["year"] if rows else start_year, "names": sorted(manual)})
    for row in rows:
        if auto:
            new: set[str] = set()
            for m in year_maskers.get(row["year"], set()):
                new |= alias_group(m)
            new -= own | running
            if new:
                running |= new
                schedule.append({"from_year": row["year"], "names": sorted(new)})
        active[row["year"]] = frozenset(running)

    first_adj = None
    if any(active.values()):
        ex_cache: dict[tuple[frozenset[str], int], tuple[int, int]] = {}

        def ex_counts(s: frozenset[str], y: int) -> tuple[int, int]:
            if (s, y) not in ex_cache:
                expr = client.drug_expression(sorted(s))
                yr = client.year_expression(y)
                ex_cache[(s, y)] = (client.report_count(client.and_(expr, yr)),
                                    client.report_count(client.and_(expr, rx_expr, yr)))
            return ex_cache[(s, y)]

        for i, row in enumerate(rows):
            s = active[row["year"]]
            if s:
                n_ex, e_ex = ex_counts(s, row["year"])
            else:
                n_ex = e_ex = 0
            n_total_adj = max(row["n_total"] - n_ex, row["n_drug"])
            n_event_adj = max(row["n_event"] - e_ex, row["a"])
            yearly_adj = _eval(row["a"], row["n_drug"], n_event_adj, n_total_adj, criteria)

            # Cumulative to this year, using the set in force THIS year for every earlier year too.
            c_event = c_total = 0
            for prev in rows[: i + 1]:
                p_n_ex, p_e_ex = ex_counts(s, prev["year"]) if s else (0, 0)
                c_total += max(prev["n_total"] - p_n_ex, prev["n_drug"])
                c_event += max(prev["n_event"] - p_e_ex, prev["a"])
            cumulative_adj = _eval(row["cum_a"], row["cum_drug"], c_event, c_total, criteria)
            if cumulative_adj and cumulative_adj.is_signal and first_adj is None:
                first_adj = row["year"]
            row.update(
                {
                    "excluded_as_of_year": ", ".join(sorted(s)),
                    "excluded_reports": n_ex,
                    "excluded_event_reports": e_ex,
                    "excluded_share_of_event_pct": (100 * e_ex / row["n_event"]) if row["n_event"] else 0.0,
                    "background_adj_pct": 100 * n_event_adj / n_total_adj if n_total_adj else 0.0,
                    "prr_year_adj": yearly_adj.prr if yearly_adj else None,
                    "cum_prr_adj": cumulative_adj.prr if cumulative_adj else None,
                    "cum_prr_adj_ci_low": cumulative_adj.prr_ci_low if cumulative_adj else None,
                    "cum_prr_adj_ci_high": cumulative_adj.prr_ci_high if cumulative_adj else None,
                    "cum_chi2_adj": cumulative_adj.chi2 if cumulative_adj else None,
                    "cum_signal_adj": bool(cumulative_adj.is_signal) if cumulative_adj else False,
                }
            )

    # ---------------------------------------------------------------- phase 3: publicity-spike flag
    # Resolve actions now so the flag can reference them before building the result.
    resolved_actions: list[RegulatoryAction] = actions if actions is not None else actions_for(names)
    first_act = min(resolved_actions, key=lambda a: a.date) if resolved_actions else None

    if first_act is not None and rows:
        pre_rows = [r for r in rows if r["year"] < first_act.year]
        if pre_rows:
            baseline = sum(r["share_of_drug_reports_pct"] for r in pre_rows) / len(pre_rows)
            threshold = 2.0 * baseline
            for r in rows:
                stimulated = (
                    baseline > 0
                    and r["year"] >= first_act.year
                    and r["share_of_drug_reports_pct"] >= threshold
                )
                r["stimulated_reporting"] = stimulated
                r["share_vs_baseline"] = (r["share_of_drug_reports_pct"] / baseline) if baseline > 0 else 0.0
        else:
            # No rows before the first action — can't establish a baseline.
            for r in rows:
                r["stimulated_reporting"] = False
                r["share_vs_baseline"] = 0.0
    else:
        # No regulatory actions recorded — flag is undefined; default to False.
        for r in rows:
            r["stimulated_reporting"] = False
            r["share_vs_baseline"] = 0.0

    df = pd.DataFrame(rows)
    return TimelineResult(
        drug=names[0].strip().upper(),
        names=[n.strip().upper() for n in names],
        reaction=reaction_u,
        start_year=start_year,
        end_year=int(df["year"].max()) if not df.empty else end_year,
        table=df,
        criteria=criteria,
        first_flag_year_cumulative=first_cum,
        first_flag_year_yearly=first_year,
        exclude=sorted(running),
        auto_excluded=auto,
        exclusion_schedule=schedule,
        first_flag_year_adjusted=first_adj,
        actions=resolved_actions,
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        source=client.last_source,
    )
