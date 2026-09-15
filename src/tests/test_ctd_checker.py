from pathlib import Path

import pytest

from pharos.ctd.checker import (
    check_outline,
    load_outline,
    load_spec,
    normalize_id,
    outline_template,
)
from pharos.ctd.report import gap_report_markdown

SAMPLES = Path(__file__).resolve().parent.parent / "data" / "samples"


def test_spec_loads_five_modules_for_both_regions():
    for region in ("US", "EU"):
        mods = load_spec(region)
        assert [m.id for m in mods] == ["1", "2", "3", "4", "5"]
        assert all(any(True for _ in m.leaves()) for m in mods)


def test_unknown_region_raises():
    with pytest.raises(ValueError):
        load_spec("MARS")


@pytest.mark.parametrize(
    "raw,expected",
    [("Module 3.2.P.8", "3.2.P.8"), ("m 2.5", "2.5"), (" 4.2.3.1. ", "4.2.3.1"), ("3.2.s.4", "3.2.S.4")],
)
def test_normalize_id(raw, expected):
    assert normalize_id(raw) == expected


def test_complete_template_scores_100_and_is_ready():
    tpl = outline_template("US", status="complete")
    res = check_outline(tpl)
    assert res.overall_score == pytest.approx(1.0)
    assert res.ready_to_submit
    assert not res.gaps
    assert all(m.score == pytest.approx(1.0) for m in res.modules)


def test_blank_template_scores_zero():
    tpl = outline_template("US", status="missing")
    res = check_outline(tpl)
    assert res.overall_score == pytest.approx(0.0)
    assert not res.ready_to_submit


def test_removing_critical_sections_creates_critical_gaps():
    tpl = outline_template("US", status="complete")
    tpl["sections"] = [s for s in tpl["sections"] if s["id"] not in {"4.2.3.4", "3.2.P.8", "1.14"}]
    res = check_outline(tpl)
    ids = {g.section_id for g in res.gaps}
    assert ids == {"4.2.3.4", "3.2.P.8", "1.14"}
    assert all(g.severity == "critical" and g.status == "missing" for g in res.gaps)
    assert 0.85 < res.overall_score < 1.0


def test_draft_counts_half():
    tpl = outline_template("US", status="complete")
    for s in tpl["sections"]:
        if s["id"] == "2.5":
            s["status"] = "draft"
    res = check_outline(tpl)
    gap = next(g for g in res.gaps if g.section_id == "2.5")
    assert gap.status == "draft"
    m2 = next(m for m in res.modules if m.module_id == "2")
    assert 0.5 < m2.score < 1.0


def test_parent_listed_instead_of_children_becomes_warning_not_credit():
    tpl = outline_template("US", status="complete")
    tpl["sections"] = [s for s in tpl["sections"] if not s["id"].startswith("4.2.3.")]
    tpl["sections"].append({"id": "4.2.3", "title": "Toxicology", "status": "complete"})
    res = check_outline(tpl)
    assert any("4.2.3" in w and "sub-sections" in w for w in res.warnings)
    assert any(g.section_id == "4.2.3.2" for g in res.gaps)  # repeat-dose tox now a gap


def test_title_only_entries_match_by_title():
    res = check_outline({"region": "US", "sections": [{"title": "Clinical Overview"}, {"title": "Quality Overall Summary (QOS)"}]})
    matched = {g.section_id for g in res.gaps}
    assert "2.5" not in matched and "2.3" not in matched
    assert res.matched_sections == 2


def test_bare_string_entries_are_accepted():
    res = check_outline(["2.5 Clinical Overview", "3.2.P.8"])
    assert res.matched_sections == 2


def test_unrecognised_entries_are_reported():
    res = check_outline({"sections": [{"id": "9.1", "title": "Marketing launch plan"}]})
    assert res.unmatched_entries == ["9.1 Marketing launch plan"]


def test_sample_incomplete_dossier_has_expected_gaps():
    res = check_outline(load_outline(SAMPLES / "dossier_incomplete.yaml"))
    missing = {g.section_id for g in res.gaps if g.status == "missing"}
    drafts = {g.section_id for g in res.gaps if g.status == "draft"}
    assert {"1.14", "3.2.P.8", "5.3.5.3"} <= missing
    assert {"2.5", "2.7", "1.3", "5.3.7"} <= drafts
    assert any("4.2.3" in w for w in res.warnings)
    assert "9.1 Marketing launch plan" in res.unmatched_entries
    assert not res.ready_to_submit


def test_sample_complete_dossier_is_ready():
    res = check_outline(load_outline(SAMPLES / "dossier_complete.yaml"))
    assert res.ready_to_submit
    assert res.overall_score == pytest.approx(1.0)


def test_markdown_report_renders_key_sections():
    res = check_outline(load_outline(SAMPLES / "dossier_incomplete.yaml"))
    md = gap_report_markdown(res)
    assert "# CTD Submission Readiness" in md
    assert "NOT READY" in md
    assert "3.2.P.8" in md
    assert "Warnings" in md
