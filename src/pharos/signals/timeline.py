"""Signal emergence timeline — *when* would this signal first have been flagged, and what hid it?

For a drug–reaction pair, rebuild the 2x2 table year by year using FDA *receive date*
(what the agency had in hand by 31 December of each year), then compute:

* the **yearly** PRR — that year's reports only (noisy, shows trend);
* the **cumulative** PRR — all reports received up to and including that year, which is
  what a pharmacovigilance scientist running the screen in that year would actually see;
* optionally a **masking-corrected** cumulative PRR, with one or more named drugs removed
  from the comparator background.

Masking is a documented failure mode of disproportionality methods (Maignen et al. 2014,
Wang et al. 2010): when one drug's reporting wave makes up most of a reaction's reports,
the background rate inflates and the same reaction is hidden for every other drug. In
FAERS, Vioxx litigation reports were ~70% of ALL myocardial-infarction reports in 2005–06,
which is exactly why Avandia's MI signal does not appear until 2007–08 under the standard
screen — and appears in 2005 once Vioxx is excluded. The timeline also *detects* masking by
listing the top contributing drugs to the reaction's reports each year.

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
from pharos.signals.stats import EVANS_2001, ContingencyTable, SignalCriteria, evaluate

OPENFDA_FIRST_YEAR = 2004  # FAERS data in openFDA begins 2004 Q1
ACTIONS_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "samples" / "regulatory_actions.yaml"
MASKING_ALERT_SHARE_PCT = 25.0  # one drug ≥ this share of a reaction's reports in a year → masking risk


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
    first_flag_year_adjusted: int | None = None
    actions: list[RegulatoryAction] = field(default_factory=list)
    generated_at: str = ""
    source: str = ""

    # ---------------------------------------------------------------- derived

    @property
    def first_action(self) -> RegulatoryAction | None:
        return min(self.actions, key=lambda a: a.date) if self.actions else None

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
            ex = ", ".join(self.exclude)
            if self.first_flag_year_adjusted is None:
                s += f" Excluding {ex} from the background, the criteria were still never met."
            else:
                row = self.table.set_index("year").loc[self.first_flag_year_adjusted]
                s += (f" Excluding {ex} from the background, the signal first met the criteria in {self.first_flag_year_adjusted} "
                      f"(PRR={row.cum_prr_adj:.2f}, chi²={row.cum_chi2_adj:.0f}).")
                s += self._lead_sentence(self.first_flag_year_adjusted, self.lead_time_years_adjusted)
                if self.first_flag_year_cumulative and self.first_flag_year_adjusted < self.first_flag_year_cumulative:
                    gained = self.first_flag_year_cumulative - self.first_flag_year_adjusted
                    s += f" Masking correction brings detection forward by {gained} year{'s' if gained != 1 else ''}."
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
            "first_flag_year_masking_corrected": self.first_flag_year_adjusted,
            "regulatory_actions": [a.as_dict() for a in self.actions],
            "lead_time_years_vs_first_action": self.lead_time_years,
            "lead_time_years_vs_first_action_masking_corrected": self.lead_time_years_adjusted,
            "worst_masking_year": self.max_masking,
            "headline": self.headline(),
            "rows": self.table.to_dict(orient="records"),
            "generated_at": self.generated_at,
            "data_source": f"openFDA ({self.source})",
            "notes": [
                "Years are FDA receive dates: cumulative PRR in year Y uses only reports the FDA had by 31 Dec Y.",
                "openFDA FAERS data begins in 2004; earlier regulatory actions cannot be evaluated prospectively.",
                "Yearly PRR is noisy for small counts; use the cumulative series for the first-flag claim.",
                "Masking: when one drug dominates a reaction's reports (see top_contributor per year), the background "
                "inflates and hides the same reaction for other drugs. Re-run with that drug excluded to correct.",
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
        exclude: drug names to remove from the comparator background (masking correction).
        detect_masking: also fetch the top drugs contributing to the reaction's reports each year.

    Request budget per year: 4 (total, drug, reaction, drug∧reaction) + 2 if ``exclude``
    + 1 if ``detect_masking``. Total and reaction counts are drug-independent and cache across drugs.
    """
    if isinstance(names, str):
        names = [names]
    names = [n for n in names if n and n.strip()]
    if not names:
        raise ValueError("At least one drug name is required.")
    exclude = [e for e in (exclude or []) if e and e.strip()]
    client = client or OpenFDAClient()
    end_year = end_year or datetime.now(timezone.utc).year
    start_year = max(start_year, OPENFDA_FIRST_YEAR)
    if end_year < start_year:
        raise ValueError("end_year must be >= start_year")

    drug_expr = client.drug_expression(names)
    rx_expr = client.reaction_expression(reaction)
    ex_expr = client.drug_expression(exclude) if exclude else None
    own = {n.strip().upper() for n in names}
    reaction_u = reaction.strip().upper()

    rows = []
    cum = {"a": 0, "drug": 0, "event": 0, "n": 0, "event_adj": 0, "n_adj": 0}
    first_cum = first_year = first_adj = None
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

        if ex_expr:
            n_ex = client.report_count(client.and_(ex_expr, yr))
            e_ex = client.report_count(client.and_(ex_expr, rx_expr, yr))
            n_total_adj = max(n_total - n_ex, n_drug)
            n_event_adj = max(n_event - e_ex, a)
            yearly_adj = _eval(a, n_drug, n_event_adj, n_total_adj, criteria)
            cum["event_adj"] += n_event_adj
            cum["n_adj"] += n_total_adj
            cumulative_adj = _eval(cum["a"], cum["drug"], cum["event_adj"], cum["n_adj"], criteria)
            if cumulative_adj and cumulative_adj.is_signal and first_adj is None:
                first_adj = year
            row.update(
                {
                    "excluded_reports": n_ex,
                    "excluded_event_reports": e_ex,
                    "excluded_share_of_event_pct": (100 * e_ex / n_event) if n_event else 0.0,
                    "background_adj_pct": 100 * n_event_adj / n_total_adj if n_total_adj else 0.0,
                    "prr_year_adj": yearly_adj.prr if yearly_adj else None,
                    "cum_prr_adj": cumulative_adj.prr if cumulative_adj else None,
                    "cum_prr_adj_ci_low": cumulative_adj.prr_ci_low if cumulative_adj else None,
                    "cum_prr_adj_ci_high": cumulative_adj.prr_ci_high if cumulative_adj else None,
                    "cum_chi2_adj": cumulative_adj.chi2 if cumulative_adj else None,
                    "cum_signal_adj": bool(cumulative_adj.is_signal) if cumulative_adj else False,
                }
            )

        if detect_masking:
            contributors = [c for c in client.drug_contributors(client.and_(rx_expr, yr), limit=top_contributors + len(own) + 2)
                            if c["term"].upper() not in own][:top_contributors]
            for c in contributors:
                c["share_pct"] = (100 * c["count"] / n_event) if n_event else 0.0
            top = contributors[0] if contributors else None
            row.update(
                {
                    "top_contributor": top["term"] if top else "",
                    "top_contributor_share_pct": top["share_pct"] if top else 0.0,
                    "masking_alert": bool(top and top["share_pct"] >= MASKING_ALERT_SHARE_PCT),
                    "contributors": contributors,
                }
            )

        rows.append(row)

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
        exclude=[e.strip().upper() for e in exclude],
        first_flag_year_adjusted=first_adj,
        actions=actions if actions is not None else actions_for(names),
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        source=client.last_source,
    )
