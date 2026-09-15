"""Timeline tests — offline, against a fake client with a hand-built year-by-year universe."""

from datetime import date
from pathlib import Path

import pytest

from pharos.signals.timeline import RegulatoryAction, load_regulatory_actions, signal_timeline

SAMPLES = Path(__file__).resolve().parent.parent / "data" / "samples"


class FakeYearClient:
    """A drug whose reaction share climbs 1% → 2% → 4% → 8% (2004–2007) against a 1% background.

    A second drug, MASKER, contributes 600 of the 1,000 reaction reports every year (60%) and
    10,000 of the 100,000 total — so the *true* background without it is 400/90,000 = 0.44%.
    """

    last_source = "fake"
    share = {2004: 0.01, 2005: 0.02, 2006: 0.04, 2007: 0.08}
    N, N_DRUG, N_EVENT, N_EX, E_EX = 100_000, 1_000, 1_000, 10_000, 600

    @staticmethod
    def drug_expression(names):
        names = [names] if isinstance(names, str) else list(names)
        return "EX" if any(n.upper() == "MASKER" for n in names) else "DRUG"

    @staticmethod
    def reaction_expression(reaction):
        return "RX"

    @staticmethod
    def year_expression(year):
        return f"Y{year}"

    @staticmethod
    def and_(*exprs):
        return "+".join(exprs)

    def _year(self, expr):
        return int([p for p in expr.split("+") if p.startswith("Y")][0][1:])

    def report_count(self, expr=None):
        year = self._year(expr)
        if year not in self.share:
            return 0  # future years: no data yet
        parts = set(expr.split("+"))
        a = int(round(self.N_DRUG * self.share[year]))
        if {"DRUG", "RX"} <= parts:
            return a
        if {"EX", "RX"} <= parts:
            return self.E_EX
        if "DRUG" in parts:
            return self.N_DRUG
        if "EX" in parts:
            return self.N_EX
        if "RX" in parts:
            return self.N_EVENT
        return self.N

    def drug_contributors(self, expr, limit=8):
        year = self._year(expr)
        a = int(round(self.N_DRUG * self.share.get(year, 0)))
        return [{"term": "MASKER", "count": self.E_EX}, {"term": "DRUG", "count": a}, {"term": "ASPIRIN", "count": 50}]


def test_cumulative_first_flag_year_is_computed():
    res = signal_timeline("drug", "rx", client=FakeYearClient(), start_year=2004, end_year=2010, actions=[])
    df = res.table.set_index("year")
    assert list(df.index) == [2004, 2005, 2006, 2007]  # future years with zero total are dropped
    # cumulative 2005: 30/2000 = 1.5% vs 1% → PRR 1.5, no; 2006: 70/3000 = 2.3% → PRR > 2.
    assert not df.loc[2004, "cum_signal"]
    assert res.first_flag_year_cumulative == 2006
    assert df.loc[2006, "cum_prr"] > 2.0
    assert df.loc[2007, "cum_a"] == 10 + 20 + 40 + 80


def test_yearly_first_flag_precedes_or_equals_cumulative():
    res = signal_timeline("drug", "rx", client=FakeYearClient(), start_year=2004, end_year=2007, actions=[])
    assert res.first_flag_year_yearly is not None
    assert res.first_flag_year_yearly <= res.first_flag_year_cumulative


def test_lead_time_against_regulatory_action():
    action = RegulatoryAction(date=date(2008, 5, 1), label="Boxed warning", source="test")
    res = signal_timeline("drug", "rx", client=FakeYearClient(), start_year=2004, end_year=2007, actions=[action])
    assert res.lead_time_years == 2008 - 2006 == 2
    assert "2 years BEFORE" in res.headline()
    d = res.as_dict()
    assert d["first_flag_year_cumulative"] == 2006
    assert d["regulatory_actions"][0]["label"] == "Boxed warning"


def test_flag_after_action_is_worded_honestly():
    action = RegulatoryAction(date=date(2005, 1, 1), label="Early warning", source="test")
    res = signal_timeline("drug", "rx", client=FakeYearClient(), start_year=2004, end_year=2007, actions=[action])
    assert res.lead_time_years == -1
    assert "1 year AFTER" in res.headline()
    assert "predates" not in res.headline()


def test_action_before_data_window_is_retrospective():
    action = RegulatoryAction(date=date(2001, 8, 8), label="Withdrawn", source="test")
    res = signal_timeline("drug", "rx", client=FakeYearClient(), start_year=2004, end_year=2007, actions=[action])
    assert "predates the data window" in res.headline()


def test_masking_detection_lists_top_contributor_and_alerts():
    res = signal_timeline("drug", "rx", client=FakeYearClient(), start_year=2004, end_year=2007, actions=[])
    df = res.table.set_index("year")
    assert df.loc[2005, "top_contributor"] == "MASKER"  # own drug filtered out of the list
    assert df.loc[2005, "top_contributor_share_pct"] == pytest.approx(60.0)
    assert bool(df.loc[2005, "masking_alert"])
    assert res.max_masking["drug"] == "MASKER"
    assert "MASKING ALERT" in res.headline()


def test_masking_correction_brings_detection_forward():
    res = signal_timeline("drug", "rx", client=FakeYearClient(), start_year=2004, end_year=2007, actions=[], exclude=["masker"])
    df = res.table.set_index("year")
    # corrected background = 400 / 90,000 = 0.44%; 2004: 1% / 0.44% = 2.25 → flagged immediately
    assert df.loc[2004, "background_adj_pct"] == pytest.approx(100 * 400 / 90_000)
    assert df.loc[2004, "excluded_share_of_event_pct"] == pytest.approx(60.0)
    assert res.first_flag_year_adjusted == 2004
    assert res.first_flag_year_adjusted < res.first_flag_year_cumulative
    assert "brings detection forward by 2 years" in res.headline()
    d = res.as_dict()
    assert d["excluded_from_background"] == ["MASKER"]
    assert d["first_flag_year_masking_corrected"] == 2004


def test_no_signal_headline():
    class Flat(FakeYearClient):
        share = {2004: 0.01, 2005: 0.01, 2006: 0.01}

    res = signal_timeline("drug", "rx", client=Flat(), start_year=2004, end_year=2006, actions=[], detect_masking=False)
    assert res.first_flag_year_cumulative is None
    assert "never met" in res.headline()
    assert "top_contributor" not in res.table.columns


def test_regulatory_actions_file_loads_and_is_sorted():
    acts = load_regulatory_actions(SAMPLES / "regulatory_actions.yaml")
    assert "ROSIGLITAZONE" in acts and "ROFECOXIB" in acts
    ros = acts["ROSIGLITAZONE"]
    assert ros[0].date == date(2007, 5, 21)
    assert all(ros[i].date <= ros[i + 1].date for i in range(len(ros) - 1))


def test_start_year_is_clamped_to_openfda_window():
    res = signal_timeline("drug", "rx", client=FakeYearClient(), start_year=1999, end_year=2005, actions=[])
    assert res.start_year == 2004


def test_end_before_start_raises():
    with pytest.raises(ValueError):
        signal_timeline("drug", "rx", client=FakeYearClient(), start_year=2006, end_year=2005, actions=[])
