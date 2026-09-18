"""Hidden-signal finder — which signals is the standard screen missing because of masking?

Disproportionality compares a drug with *all other drugs*. When one product's reporting wave
(litigation, media, a recall) makes up a large share of a reaction's reports, the background
rate inflates and the same reaction is hidden for every other drug. This is "masking"
(Maignen et al. 2014; Wang et al. 2010). It is time-local: across all of FAERS Vioxx is ~10% of
myocardial-infarction reports, but in 2004-06 it was ~70% — so the check has to be windowed.

For one drug and one time window this module:

1. runs the standard screen for the drug's most-reported reactions;
2. for each, asks openFDA which products dominate that reaction's reports in the window;
3. if any single product holds >= ``min_share_pct`` (default 25%), removes it — and its known
   brand/generic aliases — from the comparator and recomputes;
4. classifies each reaction: **unmasked** (no signal -> signal), **strengthened** (signal both ways,
   PRR up >= 25%), **masked, sub-threshold**, or **no masking**.

The masker is chosen by a fixed rule, not by an analyst. That removes the main caveat on the
Avandia timeline result, and turns a one-off finding into a screen that runs on any drug.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd

from pharos.faers.client import OpenFDAClient
from pharos.signals.detector import ADMINISTRATIVE_TERMS
from pharos.signals.stats import EVANS_2001, ContingencyTable, SignalCriteria, evaluate

OPENFDA_FIRST_YEAR = 2004
DEFAULT_MIN_SHARE_PCT = 25.0
STRENGTHENED_RATIO = 1.25
DEMO_DRUGS_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "samples" / "demo_drugs.txt"

# Brand -> generic for products with well-known stimulated-reporting waves in FAERS. The verbatim
# drug field mixes brands and generics, so excluding "VIOXX" without "ROFECOXIB" would
# under-correct. Small on purpose; extended at runtime from data/samples/demo_drugs.txt.
BRAND_TO_GENERIC = {
    "VIOXX": "ROFECOXIB", "CELEBREX": "CELECOXIB", "BEXTRA": "VALDECOXIB",
    "AVANDIA": "ROSIGLITAZONE", "ACTOS": "PIOGLITAZONE",
    "BAYCOL": "CERIVASTATIN", "LIPITOR": "ATORVASTATIN", "ZOCOR": "SIMVASTATIN", "CRESTOR": "ROSUVASTATIN",
    "XARELTO": "RIVAROXABAN", "PRADAXA": "DABIGATRAN", "COUMADIN": "WARFARIN",
    "ZANTAC": "RANITIDINE", "CHANTIX": "VARENICLINE", "ACCUTANE": "ISOTRETINOIN",
    "YAZ": "DROSPIRENONE", "YASMIN": "DROSPIRENONE", "FOSAMAX": "ALENDRONATE",
    "HUMIRA": "ADALIMUMAB", "ENBREL": "ETANERCEPT", "REMICADE": "INFLIXIMAB", "TYSABRI": "NATALIZUMAB",
    "SEROQUEL": "QUETIAPINE", "ZYPREXA": "OLANZAPINE", "PAXIL": "PAROXETINE", "OXYCONTIN": "OXYCODONE",
    "MERIDIA": "SIBUTRAMINE", "DARVON": "PROPOXYPHENE", "DARVOCET": "PROPOXYPHENE",
}


def _alias_groups() -> list[set[str]]:
    groups: list[set[str]] = []
    by_generic: dict[str, set[str]] = {}
    for brand, generic in BRAND_TO_GENERIC.items():
        by_generic.setdefault(generic, {generic}).add(brand)
    groups.extend(by_generic.values())
    if DEMO_DRUGS_PATH.exists():
        for line in DEMO_DRUGS_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split("|")]
            names = {parts[0].upper()}
            if len(parts) > 1:
                names |= {a.strip().upper() for a in parts[1].split(",") if a.strip()}
            groups.append(names)
    merged: list[set[str]] = []
    for g in groups:
        for m in merged:
            if m & g:
                m |= g
                break
        else:
            merged.append(set(g))
    return merged


_GROUPS: list[set[str]] | None = None


def alias_group(term: str) -> set[str]:
    """Every known name for the same product, e.g. 'VIOXX' -> {'VIOXX', 'ROFECOXIB'}."""
    global _GROUPS
    if _GROUPS is None:
        _GROUPS = _alias_groups()
    t = term.strip().upper()
    for g in _GROUPS:
        if t in g:
            return set(g)
    return {t}


def _eval(a, drug, event, total, criteria):
    if drug <= 0 or total <= 0 or event < a:
        return None
    try:
        return evaluate(ContingencyTable.from_counts(a, drug, event, total), criteria)
    except ValueError:
        return None


@dataclass
class HiddenSignalResult:
    drug: str
    names: list[str]
    start_year: int
    end_year: int
    n_total: int
    n_drug: int
    table: pd.DataFrame
    criteria: SignalCriteria
    min_share_pct: float
    reactions_checked: int
    generated_at: str = ""
    source: str = ""

    def _by(self, status: str) -> pd.DataFrame:
        if self.table.empty:
            return self.table
        return self.table[self.table["status"] == status].reset_index(drop=True)

    @property
    def unmasked(self) -> pd.DataFrame:
        return self._by("unmasked")

    @property
    def strengthened(self) -> pd.DataFrame:
        return self._by("strengthened")

    @property
    def n_standard_signals(self) -> int:
        if self.table.empty:
            return 0
        return int((self.table["signal_std"] & ~self.table["is_administrative"]).sum())

    def headline(self) -> str:
        window = f"{self.start_year}-{self.end_year}"
        n = self.n_standard_signals
        s = (f"{self.drug}, reports received {window}: the standard screen shows {n} clinical "
             f"signal{'s' if n != 1 else ''} among {len(self.table)} reactions.")
        um = self.unmasked
        if um.empty:
            s += f" Pharos checked {self.reactions_checked} reactions for masking and found no hidden signals."
        else:
            parts = []
            for _, r in um.head(4).iterrows():
                parts.append(f"{r['reaction']} (PRR {r['prr_std']:.2f} -> {r['prr_adj']:.2f} once {r['maskers']}, "
                             f"{r['excluded_share_pct']:.0f}% of its reports, is excluded)")
            s += (f" Pharos found {len(um)} MORE that the standard screen hides because another product floods the "
                  f"background: " + "; ".join(parts) + ("; ..." if len(um) > 4 else "") + ".")
        st = self.strengthened
        if not st.empty:
            s += (f" A further {len(st)} existing signal{'s are' if len(st) != 1 else ' is'} understated by "
                  f">=25% for the same reason.")
        return s

    def as_dict(self, top: int | None = None) -> dict:
        rows = self.table if top is None else self.table.head(top)
        return {
            "drug": self.drug,
            "names_searched": self.names,
            "window": {"start_year": self.start_year, "end_year": self.end_year},
            "reports_in_window": self.n_total,
            "drug_reports_in_window": self.n_drug,
            "criteria": self.criteria.as_dict(),
            "masking_rule": (f"exclude any single product with >= {self.min_share_pct:.0f}% of a reaction's reports "
                             f"in the window, plus its known aliases"),
            "reactions_evaluated": int(len(self.table)),
            "reactions_checked_for_masking": self.reactions_checked,
            "n_standard_clinical_signals": self.n_standard_signals,
            "n_unmasked": int(len(self.unmasked)),
            "n_strengthened": int(len(self.strengthened)),
            "headline": self.headline(),
            "rows": rows.to_dict(orient="records"),
            "generated_at": self.generated_at,
            "data_source": f"openFDA ({self.source})",
            "notes": [
                "The masker is selected by a fixed share rule, not by an analyst.",
                "Exclusion removes the masking product's reports from the comparator only; the drug's own row is untouched.",
                "'Unmasked' means the pair meets the same Evans criteria once the comparator is corrected - still a "
                "reporting association, not causation.",
                "Windows are FDA receive dates, so an as-of year reproduces what was knowable at that year-end.",
            ],
        }


COLUMNS = [
    "reaction", "n_cases", "event_total", "prr_std", "chi2_std", "signal_std", "is_administrative", "checked",
    "top_contributor", "top_contributor_share_pct", "maskers", "excluded_names", "excluded_share_pct",
    "prr_adj", "prr_adj_ci_low", "prr_adj_ci_high", "chi2_adj", "signal_adj", "status",
]
_STATUS_ORDER = {"unmasked": 0, "strengthened": 1, "masked, sub-threshold": 2, "no masking": 3, "not checked": 4}


def find_hidden_signals(
    names: str | Iterable[str],
    client: OpenFDAClient | None = None,
    as_of_year: int | None = None,
    start_year: int = OPENFDA_FIRST_YEAR,
    top_n: int = 60,
    max_checks: int = 30,
    min_share_pct: float = DEFAULT_MIN_SHARE_PCT,
    criteria: SignalCriteria = EVANS_2001,
    max_rare_lookups: int = 15,
) -> HiddenSignalResult:
    """Standard screen + automatic masking correction for one drug in one receive-date window.

    Request budget: 4 fixed + 1 per reaction checked (``max_checks``) + 2 per reaction that has a masker.
    """
    if isinstance(names, str):
        names = [names]
    names = [n for n in names if n and n.strip()]
    if not names:
        raise ValueError("At least one drug name is required.")
    client = client or OpenFDAClient()
    end_year = as_of_year or datetime.now(timezone.utc).year
    start_year = max(start_year, OPENFDA_FIRST_YEAR)
    if end_year < start_year:
        raise ValueError("as_of_year must be >= start_year")

    own: set[str] = set()
    for n in names:
        own |= alias_group(n)

    window = client.window_expression(start_year, end_year)
    drug_expr = client.drug_expression(names)
    n_total = client.report_count(window)
    n_drug = client.report_count(client.and_(drug_expr, window))
    rx_counts = client.reaction_counts(client.and_(drug_expr, window), limit=500)[:top_n]
    background = {r["term"]: r["count"] for r in client.reaction_counts(window, limit=500)}

    rows: list[dict] = []
    checks = rare = 0
    for entry in rx_counts:
        term, a = entry["term"], entry["count"]
        rx_expr = client.reaction_expression(term)
        n_event = background.get(term)
        if n_event is None:
            if rare >= max_rare_lookups:
                continue
            n_event = client.report_count(client.and_(rx_expr, window))
            rare += 1
        a = min(a, n_drug, n_event)
        std = _eval(a, n_drug, n_event, n_total, criteria)
        if std is None:
            continue
        admin = term in ADMINISTRATIVE_TERMS
        row = {
            "reaction": term, "n_cases": a, "event_total": n_event,
            "prr_std": std.prr, "chi2_std": std.chi2, "signal_std": bool(std.is_signal),
            "is_administrative": admin, "checked": False,
            "top_contributor": "", "top_contributor_share_pct": 0.0, "maskers": "", "excluded_names": "",
            "excluded_share_pct": 0.0, "prr_adj": None, "prr_adj_ci_low": None, "prr_adj_ci_high": None,
            "chi2_adj": None, "signal_adj": None, "status": "not checked",
        }

        if not admin and a >= criteria.min_cases and checks < max_checks:
            checks += 1
            row["checked"] = True
            contributors = [c for c in client.drug_contributors(client.and_(rx_expr, window), limit=10)
                            if c["term"].upper() not in own]
            for c in contributors:
                c["share_pct"] = 100 * c["count"] / n_event if n_event else 0.0
            if contributors:
                row["top_contributor"] = contributors[0]["term"]
                row["top_contributor_share_pct"] = contributors[0]["share_pct"]
            maskers = [c for c in contributors if c["share_pct"] >= min_share_pct]
            row["status"] = "no masking"
            if maskers:
                ex_names: set[str] = set()
                for m in maskers:
                    ex_names |= alias_group(m["term"])
                ex_names -= own
                ex_expr = client.drug_expression(sorted(ex_names))
                n_ex = client.report_count(client.and_(ex_expr, window))
                e_ex = client.report_count(client.and_(ex_expr, rx_expr, window))
                adj = _eval(a, n_drug, max(n_event - e_ex, a), max(n_total - n_ex, n_drug), criteria)
                row["maskers"] = ", ".join(m["term"] for m in maskers)
                row["excluded_names"] = ", ".join(sorted(ex_names))
                row["excluded_share_pct"] = 100 * e_ex / n_event if n_event else 0.0
                if adj is not None:
                    row.update({"prr_adj": adj.prr, "prr_adj_ci_low": adj.prr_ci_low, "prr_adj_ci_high": adj.prr_ci_high,
                                "chi2_adj": adj.chi2, "signal_adj": bool(adj.is_signal)})
                    if adj.is_signal and not std.is_signal:
                        row["status"] = "unmasked"
                    elif adj.is_signal and std.is_signal and adj.prr >= STRENGTHENED_RATIO * std.prr:
                        row["status"] = "strengthened"
                    elif not adj.is_signal:
                        row["status"] = "masked, sub-threshold"
        rows.append(row)

    df = pd.DataFrame(rows, columns=COLUMNS)
    if not df.empty:
        df["_o"] = df["status"].map(_STATUS_ORDER).fillna(9)
        df["_p"] = df["prr_adj"].fillna(df["prr_std"])
        df = df.sort_values(["_o", "_p"], ascending=[True, False]).drop(columns=["_o", "_p"]).reset_index(drop=True)

    return HiddenSignalResult(
        drug=names[0].strip().upper(), names=[n.strip().upper() for n in names],
        start_year=start_year, end_year=end_year, n_total=n_total, n_drug=n_drug, table=df,
        criteria=criteria, min_share_pct=min_share_pct, reactions_checked=checks,
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"), source=client.last_source,
    )
