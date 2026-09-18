"""Hidden-signal finder tests — offline, against a hand-built universe where the answers are known.

Universe (one window): N = 1,000,000 reports; our drug DRUGX has 10,000; a litigation-wave product
MASKER has 50,000.

  HEART ATTACK   DRUGX 200 (2.0%) · background 30,000 of which MASKER 24,000 (80%)
                 standard PRR = 0.02 / (29,800/990,000) = 0.66           -> no signal
                 corrected    = 0.02 / ( 5,800/940,000) = 3.24           -> UNMASKED
  LIVER INJURY   DRUGX 300 (3.0%) · background 5,000 of which MASKER 2,000 (40%)
                 standard PRR = 6.3 (signal) · corrected = 10.4 (+65%)    -> STRENGTHENED
  NAUSEA         DRUGX 500 (5.0%) · background 50,000, top product ASPIRIN 8%  -> no masking
  DRUG INEFFECTIVE  administrative                                        -> never checked
"""

import pytest

from pharos.signals.masking import alias_group, find_hidden_signals

N, N_DRUG, N_MASKER = 1_000_000, 10_000, 50_000
DRUG_RX = {"DRUG INEFFECTIVE": 900, "NAUSEA": 500, "LIVER INJURY": 300, "HEART ATTACK": 200}
EVENT_TOTAL = {"DRUG INEFFECTIVE": 60_000, "NAUSEA": 50_000, "LIVER INJURY": 5_000, "HEART ATTACK": 30_000}
MASKER_EVENT = {"HEART ATTACK": 24_000, "LIVER INJURY": 2_000, "NAUSEA": 1_000}
CONTRIBUTORS = {
    "HEART ATTACK": [("MASKER", 24_000), ("ASPIRIN", 900), ("DRUGX", 200)],
    "LIVER INJURY": [("MASKER", 2_000), ("DRUGX", 300), ("ASPIRIN", 100)],
    "NAUSEA": [("ASPIRIN", 4_000), ("MASKER", 1_000), ("DRUGX", 500)],
}


class FakeWindowClient:
    last_source = "fake"

    def __init__(self):
        self.contributor_calls: list[str] = []

    @staticmethod
    def window_expression(start, end):
        return "W"

    @staticmethod
    def drug_expression(names):
        names = [names] if isinstance(names, str) else list(names)
        return "D:" + "|".join(sorted(n.upper() for n in names))

    @staticmethod
    def reaction_expression(reaction):
        return "R:" + reaction.upper()

    @staticmethod
    def and_(*exprs):
        return "&".join(exprs)

    @staticmethod
    def _parts(expr):
        parts = expr.split("&")
        drug = next((p[2:] for p in parts if p.startswith("D:")), None)
        rx = next((p[2:] for p in parts if p.startswith("R:")), None)
        return drug, rx

    def report_count(self, expr=None):
        drug, rx = self._parts(expr)
        if drug is None and rx is None:
            return N
        if drug == "DRUGX":
            return DRUG_RX[rx] if rx else N_DRUG
        if drug == "MASKER":
            return MASKER_EVENT.get(rx, 0) if rx else N_MASKER
        return EVENT_TOTAL[rx]

    def reaction_counts(self, expr=None, limit=500):
        drug, _ = self._parts(expr)
        src = DRUG_RX if drug == "DRUGX" else EVENT_TOTAL
        return [{"term": t, "count": c} for t, c in sorted(src.items(), key=lambda kv: -kv[1])]

    def drug_contributors(self, expr, limit=8):
        _, rx = self._parts(expr)
        self.contributor_calls.append(rx)
        return [{"term": t, "count": c} for t, c in CONTRIBUTORS.get(rx, [])]


@pytest.fixture
def result():
    return find_hidden_signals("drugx", client=FakeWindowClient(), as_of_year=2006)


def test_hidden_signal_is_unmasked(result):
    row = result.table.set_index("reaction").loc["HEART ATTACK"]
    assert not row["signal_std"]
    assert row["prr_std"] == pytest.approx(0.02 / (29_800 / 990_000), rel=1e-6)
    assert row["maskers"] == "MASKER"
    assert row["excluded_share_pct"] == pytest.approx(80.0)
    assert row["prr_adj"] == pytest.approx(0.02 / (5_800 / 940_000), rel=1e-6)
    assert row["signal_adj"] and row["status"] == "unmasked"
    assert list(result.unmasked["reaction"]) == ["HEART ATTACK"]


def test_existing_signal_is_flagged_as_understated(result):
    row = result.table.set_index("reaction").loc["LIVER INJURY"]
    assert row["signal_std"] and row["signal_adj"]
    assert row["prr_adj"] / row["prr_std"] > 1.25
    assert row["status"] == "strengthened"


def test_no_dominant_product_means_no_correction(result):
    row = result.table.set_index("reaction").loc["NAUSEA"]
    assert row["status"] == "no masking"
    assert row["top_contributor"] == "ASPIRIN"          # the drug's own name is never its own masker
    assert row["top_contributor_share_pct"] == pytest.approx(8.0)
    assert row["prr_adj"] is None or row["prr_adj"] != row["prr_adj"]  # None / NaN


def test_administrative_terms_are_never_checked():
    client = FakeWindowClient()
    res = find_hidden_signals("drugx", client=client, as_of_year=2006)
    row = res.table.set_index("reaction").loc["DRUG INEFFECTIVE"]
    assert row["is_administrative"] and not row["checked"] and row["status"] == "not checked"
    assert "DRUG INEFFECTIVE" not in client.contributor_calls


def test_unmasked_rows_sort_first_and_headline_names_them(result):
    assert result.table.iloc[0]["reaction"] == "HEART ATTACK"
    h = result.headline()
    assert "found 1 MORE" in h and "HEART ATTACK" in h and "MASKER" in h
    assert "1 existing signal is understated" in h


def test_threshold_controls_what_counts_as_a_masker():
    strict = find_hidden_signals("drugx", client=FakeWindowClient(), as_of_year=2006, min_share_pct=50.0)
    rows = strict.table.set_index("reaction")
    assert rows.loc["HEART ATTACK", "status"] == "unmasked"       # 80% >= 50%
    assert rows.loc["LIVER INJURY", "status"] == "no masking"     # 40% <  50%


def test_max_checks_bounds_the_request_budget():
    client = FakeWindowClient()
    find_hidden_signals("drugx", client=client, as_of_year=2006, max_checks=1)
    assert len(client.contributor_calls) == 1


def test_as_dict_is_json_friendly(result):
    d = result.as_dict()
    assert d["n_unmasked"] == 1 and d["n_strengthened"] == 1
    assert d["window"] == {"start_year": 2004, "end_year": 2006}
    assert "fixed share rule" in " ".join(d["notes"])


def test_alias_groups_expand_brand_and_generic():
    assert alias_group("vioxx") == {"VIOXX", "ROFECOXIB"}
    assert alias_group("Rofecoxib") == {"VIOXX", "ROFECOXIB"}
    assert {"AVANDIA", "ROSIGLITAZONE"} <= alias_group("avandia")
    assert alias_group("some-unknown-drug") == {"SOME-UNKNOWN-DRUG"}


def test_bad_window_raises():
    with pytest.raises(ValueError):
        find_hidden_signals("drugx", client=FakeWindowClient(), as_of_year=2003, start_year=2004)
