import math

import pytest

from pharos.signals.stats import (
    ContingencyTable,
    SignalCriteria,
    chi_square,
    evaluate,
    prr,
    prr_ci,
    ror,
    ror_ci,
)


# Hand-computed reference case:
#   a=10 (drug & event), drug total=100, event total=110, N=10,000
#   → b=90, c=100, d=9,800
#   PRR = (10/100)/(100/9900) = 9.9
#   ROR = (10*9800)/(90*100) = 10.888…
#   chi² (Yates) = N(|ad−bc|−N/2)² / ((a+b)(c+d)(a+c)(b+d)) = 65.51…
REF = ContingencyTable.from_counts(drug_event=10, drug_total=100, event_total=110, total=10_000)


def test_from_counts_fills_cells():
    assert (REF.a, REF.b, REF.c, REF.d) == (10, 90, 100, 9800)
    assert REF.n == 10_000


def test_from_counts_rejects_inconsistent_marginals():
    with pytest.raises(ValueError):
        ContingencyTable.from_counts(drug_event=50, drug_total=40, event_total=100, total=1000)


def test_prr_matches_hand_calculation():
    assert prr(REF) == pytest.approx(9.9, rel=1e-9)


def test_ror_matches_hand_calculation():
    assert ror(REF) == pytest.approx(98000 / 9000, rel=1e-9)


def test_chi_square_yates_matches_hand_calculation():
    assert chi_square(REF) == pytest.approx(65.514, abs=0.01)


def test_chi_square_without_yates_is_larger():
    assert chi_square(REF, yates=False) > chi_square(REF, yates=True)


def test_confidence_intervals_bracket_point_estimates():
    lo, hi = prr_ci(REF)
    assert lo < prr(REF) < hi
    lo, hi = ror_ci(REF)
    assert lo < ror(REF) < hi
    # log-symmetric: geometric mean of bounds equals the point estimate
    assert math.sqrt(lo * hi) == pytest.approx(ror(REF), rel=1e-9)


def test_evaluate_flags_signal_with_evans_criteria():
    r = evaluate(REF)
    assert r.is_signal
    assert r.tier == "strong"
    assert r.n_cases == 10
    assert not r.haldane_corrected


def test_null_association_is_not_a_signal():
    # drug's event rate equals background: 1/100 vs 99/9900 = 1% vs 1%
    t = ContingencyTable.from_counts(drug_event=1, drug_total=100, event_total=100, total=10_000)
    r = evaluate(t)
    assert r.prr == pytest.approx(1.0, abs=0.01)
    assert not r.is_signal
    assert r.tier == "none"


def test_min_cases_rule_blocks_tiny_counts():
    # PRR is huge but only 2 cases → Evans says no
    t = ContingencyTable.from_counts(drug_event=2, drug_total=20, event_total=4, total=100_000)
    assert not evaluate(t).is_signal
    assert evaluate(t, SignalCriteria(min_cases=2)).is_signal


def test_zero_cell_triggers_haldane_correction_and_stays_finite():
    t = ContingencyTable.from_counts(drug_event=5, drug_total=5, event_total=5, total=1000)  # b=0, c=0
    r = evaluate(t)
    assert r.haldane_corrected
    assert math.isfinite(r.prr) and math.isfinite(r.ror) and math.isfinite(r.chi2)


def test_summary_line_mentions_verdict():
    line = evaluate(REF).summary_line("MYOCARDIAL INFARCTION", "ROFECOXIB")
    assert "ROFECOXIB × MYOCARDIAL INFARCTION" in line
    assert "SIGNAL" in line
