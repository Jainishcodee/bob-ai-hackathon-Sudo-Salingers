"""Detector tests run fully offline against a fake client — no network, deterministic."""

import pandas as pd

from pharos.signals.cluster import assign_soc, cluster_signals
from pharos.signals.detector import ADMINISTRATIVE_TERMS, scan_drug


class FakeClient:
    """Mimics OpenFDAClient with a tiny hand-built FAERS universe."""

    last_source = "fake"

    def total_reports(self):
        return 1_000_000

    def drug_report_count(self, names):
        return 2_000

    def drug_reaction_counts(self, names, limit=1000):
        return [
            {"term": "DRUG INEFFECTIVE", "count": 300},   # administrative — never a clinical signal
            {"term": "MYOCARDIAL INFARCTION", "count": 120},
            {"term": "NAUSEA", "count": 100},
            {"term": "HEPATIC FAILURE", "count": 15},
            {"term": "ALOPECIA", "count": 2},              # below min cases
            {"term": "RARE TERM NOT IN BACKGROUND", "count": 5},
        ]

    def background_reaction_counts(self, limit=1000):
        return {
            "DRUG INEFFECTIVE": 60_000,       # 6% background; drug 15% → PRR 2.5 but administrative
            "MYOCARDIAL INFARCTION": 8_000,   # 0.8% background; drug 6% → PRR ≈ 7.6
            "NAUSEA": 50_000,                 # 5% background; drug 5% → PRR ≈ 1
            "HEPATIC FAILURE": 1_500,         # 0.15% background; drug 0.75% → PRR ≈ 5
            "ALOPECIA": 5_000,
        }

    def reaction_report_count(self, reaction):
        return 40_000  # rare-term fallback: 4% background vs drug 0.25% → PRR ≈ 0.06, not a signal


def test_scan_ranks_clinical_signals_first_and_flags_correctly():
    res = scan_drug(["testdrug"], client=FakeClient(), top_n=10)
    df = res.table
    assert list(df["reaction"][:2]) == ["MYOCARDIAL INFARCTION", "HEPATIC FAILURE"]
    mi = df.set_index("reaction").loc["MYOCARDIAL INFARCTION"]
    assert mi["is_signal"] and not mi["is_administrative"]
    assert mi["prr"] > 5
    nausea = df.set_index("reaction").loc["NAUSEA"]
    assert not nausea["is_signal"]
    alo = df.set_index("reaction").loc["ALOPECIA"]
    assert not alo["is_signal"]  # only 2 cases


def test_administrative_terms_are_computed_but_excluded_from_clinical_signals():
    res = scan_drug("testdrug", client=FakeClient())
    admin = res.table.set_index("reaction").loc["DRUG INEFFECTIVE"]
    assert admin["is_administrative"]
    assert admin["is_signal"]  # statistically yes…
    assert "DRUG INEFFECTIVE" not in set(res.signals()["reaction"])  # …but not a clinical signal
    assert "DRUG INEFFECTIVE" in ADMINISTRATIVE_TERMS


def test_rare_reaction_falls_back_to_single_lookup():
    res = scan_drug("testdrug", client=FakeClient())
    rare = res.table.set_index("reaction").loc["RARE TERM NOT IN BACKGROUND"]
    assert rare["event_total"] == 40_000
    assert not rare["is_signal"]


def test_as_dict_is_json_friendly():
    d = scan_drug("testdrug", client=FakeClient()).as_dict(top=3)
    assert d["drug"] == "TESTDRUG"
    assert d["reports_mentioning_drug"] == 2_000
    assert len(d["rows"]) == 3
    assert d["n_clinical_signals"] == 2


def test_soc_assignment_curated_and_heuristic():
    assert assign_soc("MYOCARDIAL INFARCTION") == ("Cardiac disorders", "curated")
    assert assign_soc("SOME NEW HEPATIC THING")[0] == "Hepatobiliary disorders"
    assert assign_soc("SOME NEW HEPATIC THING")[1] == "heuristic"
    assert assign_soc("XYZZY")[0] == "Unclassified"


def test_cluster_signals_groups_by_soc():
    res = scan_drug("testdrug", client=FakeClient())
    cl = cluster_signals(res.table)
    assert set(cl["soc"]) == {"Cardiac disorders", "Hepatobiliary disorders"}
    cardiac = cl.set_index("soc").loc["Cardiac disorders"]
    assert cardiac["strongest_reaction"] == "MYOCARDIAL INFARCTION"
    assert cardiac["n_cases"] == 120


def test_cluster_of_empty_table_is_empty_frame():
    empty = pd.DataFrame(columns=["reaction", "is_signal", "is_administrative", "prr", "n_cases"])
    assert cluster_signals(empty).empty
