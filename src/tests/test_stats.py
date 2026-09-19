import math

import pytest

from pharos.signals.stats import (
    ContingencyTable,
    SignalCriteria,
    chi_square,
    evaluate,
    ic,
    ic025,
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


# ---------------------------------------------------------------------------
# WHO-UMC IC tests — all expected values derived by hand.
# ---------------------------------------------------------------------------

# Reference table (same as above):
#   a=10, drug_total=100, event_total=110, total=10_000
#   b=90, c=100, d=9800, N=10000
#   E = (a+b)*(a+c)/N = 100*110/10000 = 1.1
#   IC = log2(10.5 / (1.1+0.5)) = log2(10.5/1.6) = log2(6.5625) = 2.7142
#   IC025 = 2.7142 - 3.3/sqrt(10.5) - 2/10.5^1.5
#         = 2.7142 - 3.3/3.2404 - 2/34.024
#         = 2.7142 - 1.0184 - 0.0588
#         = 1.6370


def test_ic_matches_hand_calculation():
    assert ic(REF) == pytest.approx(2.7142, abs=1e-3)


def test_ic025_matches_hand_calculation():
    assert ic025(REF) == pytest.approx(1.6370, abs=1e-3)


def test_ic_signal_true_for_strong_signal():
    r = evaluate(REF)
    assert r.is_signal_ic is True
    assert r.methods_agree is True  # Evans also fires: PRR=9.9


# Null association: from_counts(1, 100, 100, 10_000)
#   b=99, c=99, d=9801, N=10000
#   E = 100*100/10000 = 1.0
#   IC = log2(1.5/1.5) = log2(1.0) = 0.0
#   IC025 = 0.0 - 3.3/sqrt(1.5) - 2/1.5^1.5
#         = 0.0 - 2.6941 - 1.0887
#         = -3.7828  → no IC signal


def test_ic_no_signal_for_null_association():
    t = ContingencyTable.from_counts(1, 100, 100, 10_000)
    assert ic(t) == pytest.approx(0.0, abs=1e-3)
    assert ic025(t) == pytest.approx(-3.7828, abs=1e-3)
    r = evaluate(t)
    assert r.is_signal_ic is False


# Small count: from_counts(3, 50, 200, 100_000)
#   b=47, c=197, d=99753, N=100000
#   E = 50*200/100000 = 0.1
#   IC = log2(3.5 / (0.1+0.5)) = log2(3.5/0.6) = log2(5.8333) = 2.5443
#   IC025 = 2.5443 - 3.3/sqrt(3.5) - 2/3.5^1.5
#         = 2.5443 - 3.3/1.8708 - 2/6.5484
#         = 2.5443 - 1.7641 - 0.3054
#         = 0.4748  → IC signal fires


def test_ic_signal_fires_for_small_count_table():
    t = ContingencyTable.from_counts(3, 50, 200, 100_000)
    assert ic(t) == pytest.approx(2.5443, abs=1e-3)
    assert ic025(t) == pytest.approx(0.4748, abs=1e-3)
    r = evaluate(t)
    assert r.is_signal_ic is True


# Zero cell: a=0 must not raise and is_signal_ic must be False (IC025 will be very negative).


def test_ic_zero_a_cell_does_not_raise():
    t = ContingencyTable.from_counts(0, 100, 100, 10_000)
    assert math.isfinite(ic(t))
    assert math.isfinite(ic025(t))
    r = evaluate(t)
    assert r.is_signal_ic is False


# Disagreement: Evans fires but IC025 <= 0.
#   from_counts(10, 100, 4900, 100_000)
#   b=90, c=4890, d=95010, N=100000
#   E = 100*4900/100000 = 4.9
#   PRR ≈ (10/100)/(4890/99900) = 0.1/0.04895 = 2.042  ≥ 2 ✓
#   chi² ≈ 4.546  ≥ 4 ✓  n=10 ≥ 3 ✓  → Evans is_signal = True
#   IC = log2(10.5/(4.9+0.5)) = log2(10.5/5.4) = log2(1.9444) = 0.9590
#   IC025 = 0.9590 - 3.3/sqrt(10.5) - 2/10.5^1.5
#         = 0.9590 - 1.0184 - 0.0588 = -0.1182  < 0  → is_signal_ic = False


def test_methods_disagree_when_evans_fires_but_ic025_negative():
    t = ContingencyTable.from_counts(10, 100, 4900, 100_000)
    r = evaluate(t)
    assert r.is_signal is True        # Evans fires
    assert r.is_signal_ic is False    # WHO IC025 < 0
    assert r.methods_agree is False


def test_summary_line_includes_ic025_and_disagree_warning():
    # REF gives agreement, so no warning
    line_agree = evaluate(REF).summary_line("EVENT", "DRUG")
    assert "IC025=" in line_agree
    assert "⚠" not in line_agree

    # Disagreement table gets the warning
    t_disagree = ContingencyTable.from_counts(10, 100, 4900, 100_000)
    line_disagree = evaluate(t_disagree).summary_line("EVENT", "DRUG")
    assert "IC025=" in line_disagree
    assert "⚠ methods disagree" in line_disagree


# Regression: existing reference values must be unchanged.


def test_existing_reference_values_unchanged():
    r = evaluate(REF)
    assert r.prr == pytest.approx(9.9, rel=1e-9)
    assert r.chi2 == pytest.approx(65.514, abs=0.01)
    assert r.is_signal is True
