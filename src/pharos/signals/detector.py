"""Scan a drug across every reaction reported with it and rank the signals."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterable

import pandas as pd

from pharos.faers.client import OpenFDAClient
from pharos.signals.stats import EVANS_2001, ContingencyTable, SignalCriteria, evaluate

# Reaction terms that describe how a product was used rather than a clinical event.
# They dominate FAERS counts and are noise for safety-signal purposes, so they are
# excluded from the signal flag by default (still shown, still computed).
ADMINISTRATIVE_TERMS = {
    "DRUG INEFFECTIVE",
    "OFF LABEL USE",
    "PRODUCT USED FOR UNKNOWN INDICATION",
    "DRUG DOSE OMISSION",
    "INCORRECT DOSE ADMINISTERED",
    "WRONG TECHNIQUE IN PRODUCT USAGE PROCESS",
    "PRODUCT USE ISSUE",
    "PRODUCT SUBSTITUTION ISSUE",
    "INTENTIONAL PRODUCT USE ISSUE",
    "DRUG INTERACTION",
    "TREATMENT NONCOMPLIANCE",
    "INAPPROPRIATE SCHEDULE OF PRODUCT ADMINISTRATION",
    "THERAPY CESSATION",
    "NO ADVERSE EVENT",
    "EXPIRED PRODUCT ADMINISTERED",
    "MEDICATION ERROR",
    "DRUG INEFFECTIVE FOR UNAPPROVED INDICATION",
    "PRODUCT QUALITY ISSUE",
    "CONDITION AGGRAVATED",
    "ILLNESS",
    "ADVERSE EVENT",
    "ADVERSE DRUG REACTION",
    "DEATH",  # an outcome, not a reaction; kept visible but not flagged as a signal on its own
}

COLUMNS = [
    "reaction",
    "n_cases",
    "drug_total",
    "event_total",
    "prr",
    "prr_ci_low",
    "prr_ci_high",
    "ror",
    "ror_ci_low",
    "ror_ci_high",
    "chi2",
    "is_signal",
    "tier",
    "is_administrative",
    "haldane_corrected",
    "ic",
    "ic025",
    "is_signal_ic",
    "methods_agree",
]


@dataclass
class ScanResult:
    drug: str
    names: list[str]
    total_reports: int
    drug_reports: int
    table: pd.DataFrame
    criteria: SignalCriteria
    generated_at: str
    source: str  # "live" or "cache"
    skipped_reactions: list[str] = field(default_factory=list)

    def signals(self, include_administrative: bool = False) -> pd.DataFrame:
        df = self.table[self.table["is_signal"]]
        if not include_administrative:
            df = df[~df["is_administrative"]]
        return df.reset_index(drop=True)

    def as_dict(self, top: int | None = None) -> dict:
        rows = self.table if top is None else self.table.head(top)
        return {
            "drug": self.drug,
            "names_searched": self.names,
            "total_reports_in_faers": self.total_reports,
            "reports_mentioning_drug": self.drug_reports,
            "criteria": self.criteria.as_dict(),
            "generated_at": self.generated_at,
            "data_source": f"openFDA ({self.source})",
            "n_reactions_evaluated": int(len(self.table)),
            "n_signals": int(self.table["is_signal"].sum()),
            "n_clinical_signals": int(len(self.signals())),
            "n_methods_disagree": int((~self.table["methods_agree"]).sum()) if not self.table.empty else 0,
            "rows": rows.to_dict(orient="records"),
            "skipped_reactions": self.skipped_reactions,
        }


def scan_drug(
    names: str | Iterable[str],
    client: OpenFDAClient | None = None,
    top_n: int = 100,
    criteria: SignalCriteria = EVANS_2001,
    max_extra_lookups: int = 40,
) -> ScanResult:
    """Run disproportionality analysis for one drug against every reaction reported with it.

    Request budget: 3 requests fixed (grand total, drug total, background top-1000) plus one
    ``count`` request for the drug's reactions, plus at most ``max_extra_lookups`` single
    requests for reactions rare enough to fall outside the top-1000 background list.
    """
    if isinstance(names, str):
        names = [names]
    names = [n for n in names if n and n.strip()]
    if not names:
        raise ValueError("At least one drug name is required.")
    display = names[0].strip().upper()
    client = client or OpenFDAClient()

    total = client.total_reports()
    drug_total = client.drug_report_count(names)
    # Fixed at 500 (the keyless maximum) rather than "as many as the key allows" so the cache
    # URL is identical with or without OPENFDA_API_KEY — offline mode then always hits.
    reaction_counts = client.drug_reaction_counts(names, limit=500)[:top_n]
    background = client.background_reaction_counts(limit=500)

    rows: list[dict] = []
    skipped: list[str] = []
    extra_lookups = 0
    for entry in reaction_counts:
        term, a = entry["term"], entry["count"]
        event_total = background.get(term)
        if event_total is None:
            if extra_lookups >= max_extra_lookups:
                skipped.append(term)
                continue
            event_total = client.reaction_report_count(term)
            extra_lookups += 1
        # ``count`` tallies term occurrences, which can (rarely) exceed report totals when a
        # report repeats a term. Clamp so the table stays consistent.
        a = min(a, drug_total, event_total)
        try:
            tbl = ContingencyTable.from_counts(a, drug_total, event_total, total)
        except ValueError:
            skipped.append(term)
            continue
        res = evaluate(tbl, criteria)
        rows.append(
            {
                "reaction": term,
                "n_cases": res.n_cases,
                "drug_total": drug_total,
                "event_total": event_total,
                "prr": res.prr,
                "prr_ci_low": res.prr_ci_low,
                "prr_ci_high": res.prr_ci_high,
                "ror": res.ror,
                "ror_ci_low": res.ror_ci_low,
                "ror_ci_high": res.ror_ci_high,
                "chi2": res.chi2,
                "is_signal": res.is_signal,
                "tier": res.tier,
                "is_administrative": term in ADMINISTRATIVE_TERMS,
                "haldane_corrected": res.haldane_corrected,
                "ic": res.ic,
                "ic025": res.ic025,
                "is_signal_ic": res.is_signal_ic,
                "methods_agree": res.methods_agree,
            }
        )

    df = pd.DataFrame(rows, columns=COLUMNS)
    if not df.empty:
        # Clinical signals first, then by PRR, so the worklist reads top-down.
        df["_rank"] = (df["is_signal"] & ~df["is_administrative"]).astype(int) * 2 + df["is_signal"].astype(int)
        df = df.sort_values(["_rank", "prr"], ascending=[False, False]).drop(columns="_rank").reset_index(drop=True)

    return ScanResult(
        drug=display,
        names=[n.strip().upper() for n in names],
        total_reports=total,
        drug_reports=drug_total,
        table=df,
        criteria=criteria,
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        source=client.last_source,
        skipped_reactions=skipped,
    )


def compute_pair(
    names: str | Iterable[str],
    reaction: str,
    client: OpenFDAClient | None = None,
    criteria: SignalCriteria = EVANS_2001,
) -> dict:
    """Full 2x2 analysis for a single drug–reaction pair, using an exact AND query for cell a."""
    if isinstance(names, str):
        names = [names]
    client = client or OpenFDAClient()
    total = client.total_reports()
    drug_total = client.drug_report_count(names)
    event_total = client.reaction_report_count(reaction)
    a = client.drug_reaction_report_count(names, reaction)
    tbl = ContingencyTable.from_counts(a, drug_total, event_total, total)
    res = evaluate(tbl, criteria)
    out = res.as_dict()
    out.update(
        {
            "drug": names[0].strip().upper(),
            "names_searched": [n.strip().upper() for n in names],
            "reaction": reaction.strip().upper(),
            "is_administrative": reaction.strip().upper() in ADMINISTRATIVE_TERMS,
            "data_source": f"openFDA ({client.last_source})",
            "summary": res.summary_line(reaction.strip().upper(), names[0].strip().upper()),
        }
    )
    return out
