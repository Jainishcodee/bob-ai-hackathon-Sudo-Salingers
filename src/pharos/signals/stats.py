"""Disproportionality statistics for spontaneous adverse-event reports.

Everything here operates on the classic 2x2 contingency table:

                    | event Y | not event Y |
    ----------------+---------+-------------+
    drug X          |    a    |      b      |
    all other drugs |    c    |      d      |

Metrics implemented (all standard in pharmacovigilance, none invented here):

* PRR  — Proportional Reporting Ratio (Evans, Waller & Davis 2001). The share of
         drug-X reports that mention event Y, divided by the same share among all
         other drugs.
* ROR  — Reporting Odds Ratio, with 95% CI (preferred by EMA / Eudravigilance).
* chi² — Pearson chi-square with Yates' continuity correction, as used in the
         original Evans criteria.

Signal criteria default to Evans (2001): PRR >= 2, chi² >= 4, and at least 3 cases.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field

Z95 = 1.959963984540054  # two-sided 95% normal quantile


@dataclass(frozen=True)
class ContingencyTable:
    """2x2 table. Cells are floats so the Haldane–Anscombe 0.5 correction is representable."""

    a: float  # drug & event
    b: float  # drug & not event
    c: float  # not drug & event
    d: float  # not drug & not event

    @classmethod
    def from_counts(
        cls, drug_event: int, drug_total: int, event_total: int, total: int
    ) -> "ContingencyTable":
        """Build the table from the four marginal counts openFDA gives us directly."""
        a = drug_event
        b = drug_total - drug_event
        c = event_total - drug_event
        d = total - drug_total - c
        if min(a, b, c, d) < 0:
            raise ValueError(
                f"Inconsistent counts: drug_event={drug_event}, drug_total={drug_total}, "
                f"event_total={event_total}, total={total} produce a negative cell."
            )
        return cls(float(a), float(b), float(c), float(d))

    @property
    def n(self) -> float:
        return self.a + self.b + self.c + self.d

    @property
    def has_zero_cell(self) -> bool:
        return 0 in (self.a, self.b, self.c, self.d)

    def haldane_corrected(self) -> "ContingencyTable":
        """Add 0.5 to every cell — the conventional fix when a cell is zero."""
        return ContingencyTable(self.a + 0.5, self.b + 0.5, self.c + 0.5, self.d + 0.5)

    def as_dict(self) -> dict:
        return {"a": self.a, "b": self.b, "c": self.c, "d": self.d, "n": self.n}


@dataclass(frozen=True)
class SignalCriteria:
    """Thresholds that turn statistics into a yes/no signal flag."""

    min_cases: int = 3
    prr_threshold: float = 2.0
    chi2_threshold: float = 4.0

    def as_dict(self) -> dict:
        return asdict(self)


EVANS_2001 = SignalCriteria()


def prr(t: ContingencyTable) -> float:
    return (t.a / (t.a + t.b)) / (t.c / (t.c + t.d))


def prr_ci(t: ContingencyTable) -> tuple[float, float]:
    """95% CI for PRR via the log-normal approximation."""
    se = math.sqrt(1 / t.a - 1 / (t.a + t.b) + 1 / t.c - 1 / (t.c + t.d))
    log_prr = math.log(prr(t))
    return math.exp(log_prr - Z95 * se), math.exp(log_prr + Z95 * se)


def ror(t: ContingencyTable) -> float:
    return (t.a * t.d) / (t.b * t.c)


def ror_ci(t: ContingencyTable) -> tuple[float, float]:
    se = math.sqrt(1 / t.a + 1 / t.b + 1 / t.c + 1 / t.d)
    log_ror = math.log(ror(t))
    return math.exp(log_ror - Z95 * se), math.exp(log_ror + Z95 * se)


def chi_square(t: ContingencyTable, yates: bool = True) -> float:
    """Pearson chi-square on the 2x2 table, Yates-corrected by default."""
    n = t.n
    diff = abs(t.a * t.d - t.b * t.c)
    if yates:
        diff = max(0.0, diff - n / 2)
    denom = (t.a + t.b) * (t.c + t.d) * (t.a + t.c) * (t.b + t.d)
    if denom == 0:
        return 0.0
    return n * diff * diff / denom


def strength_tier(prr_value: float, chi2_value: float, n_cases: float, is_signal: bool) -> str:
    """Coarse prioritisation tier. A triage heuristic for ranking a worklist —
    NOT a regulatory classification, and documented as such."""
    if not is_signal:
        return "none"
    if prr_value >= 5 and chi2_value >= 20 and n_cases >= 10:
        return "strong"
    if prr_value >= 3:
        return "moderate"
    return "weak"


@dataclass
class DisproportionalityResult:
    table: ContingencyTable
    n_cases: int
    prr: float
    prr_ci_low: float
    prr_ci_high: float
    ror: float
    ror_ci_low: float
    ror_ci_high: float
    chi2: float
    is_signal: bool
    tier: str
    haldane_corrected: bool
    criteria: SignalCriteria = field(default_factory=SignalCriteria)

    def as_dict(self) -> dict:
        d = asdict(self)
        d["table"] = self.table.as_dict()
        d["criteria"] = self.criteria.as_dict()
        return d

    def summary_line(self, reaction: str, drug: str) -> str:
        flag = "SIGNAL" if self.is_signal else "no signal"
        return (
            f"{drug} × {reaction}: n={self.n_cases}, PRR={self.prr:.2f} "
            f"[{self.prr_ci_low:.2f}–{self.prr_ci_high:.2f}], ROR={self.ror:.2f}, "
            f"chi²={self.chi2:.1f} → {flag} ({self.tier})"
        )


def evaluate(
    table: ContingencyTable, criteria: SignalCriteria = EVANS_2001
) -> DisproportionalityResult:
    """Compute every metric on a 2x2 table and apply the signal criteria.

    The signal decision uses the *uncorrected* case count (a) for the min-cases rule, but
    if any cell is zero the ratios are computed on the Haldane-corrected table so they
    stay finite.
    """
    n_cases = int(round(table.a))
    work = table.haldane_corrected() if table.has_zero_cell else table
    corrected = table.has_zero_cell

    prr_v = prr(work)
    prr_lo, prr_hi = prr_ci(work)
    ror_v = ror(work)
    ror_lo, ror_hi = ror_ci(work)
    chi2_v = chi_square(table)  # chi-square is well-defined with zeros; use the real table

    is_signal = (
        n_cases >= criteria.min_cases
        and prr_v >= criteria.prr_threshold
        and chi2_v >= criteria.chi2_threshold
    )
    tier = strength_tier(prr_v, chi2_v, n_cases, is_signal)

    return DisproportionalityResult(
        table=table,
        n_cases=n_cases,
        prr=prr_v,
        prr_ci_low=prr_lo,
        prr_ci_high=prr_hi,
        ror=ror_v,
        ror_ci_low=ror_lo,
        ror_ci_high=ror_hi,
        chi2=chi2_v,
        is_signal=is_signal,
        tier=tier,
        haldane_corrected=corrected,
        criteria=criteria,
    )
