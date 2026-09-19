from pathlib import Path

import pytest
import yaml

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


# ------------------------------------------------------------------ remediation order tests


def test_remediation_order_topology(tmp_path):
    """a) topological ordering: 5.3.5.3 before 2.7 before 2.5 before 1.14; 4.2.3.5 before 1.14."""
    res = check_outline(load_outline(SAMPLES / "dossier_incomplete.yaml"))
    order = res.remediation_order
    assert order.index("5.3.5.3") < order.index("2.7")
    assert order.index("2.7") < order.index("2.5")
    assert order.index("2.5") < order.index("1.14")
    assert order.index("4.2.3.5") < order.index("1.14")


def test_remediation_order_blocks(tmp_path):
    """b) blocks field: 5.3.5.3 blocks 1.14, 2.5, 2.7 (sorted); 4.2.3.5 is in 1.14's ancestors."""
    res = check_outline(load_outline(SAMPLES / "dossier_incomplete.yaml"))
    gap_by_id = {g.section_id: g for g in res.gaps}
    assert gap_by_id["5.3.5.3"].blocks == sorted(["1.14", "2.5", "2.7"])
    assert "1.14" in gap_by_id["4.2.3.5"].blocks


def test_remediation_order_complete_coverage(tmp_path):
    """c) every gap appears exactly once; d) gaps list order is unchanged (first element critical)."""
    res = check_outline(load_outline(SAMPLES / "dossier_incomplete.yaml"))
    order = res.remediation_order
    # c) length matches
    assert len(order) == len(res.gaps)
    # c) every gap id present exactly once
    assert sorted(order) == sorted(g.section_id for g in res.gaps)
    assert len(set(order)) == len(order)


def test_gaps_order_unchanged():
    """d) result.gaps severity order is unchanged — first gap must be critical."""
    res = check_outline(load_outline(SAMPLES / "dossier_incomplete.yaml"))
    assert res.gaps[0].severity == "critical"


def test_complete_dossier_remediation_order_empty():
    """e) complete dossier has no gaps → remediation_order == []."""
    res = check_outline(load_outline(SAMPLES / "dossier_complete.yaml"))
    assert res.remediation_order == []


def test_cycle_raises_value_error(tmp_path):
    """f) two leaves that depend on each other must raise ValueError naming both ids."""
    spec = {
        "version": "test",
        "modules": [
            {
                "id": "2",
                "title": "Test module",
                "regional": False,
                "note": "",
                "sections": [
                    {
                        "id": "2.A",
                        "title": "Section A",
                        "required": True,
                        "weight": 3,
                        "note": "",
                        "depends_on": ["2.B"],
                    },
                    {
                        "id": "2.B",
                        "title": "Section B",
                        "required": True,
                        "weight": 3,
                        "note": "",
                        "depends_on": ["2.A"],
                    },
                ],
            }
        ],
    }
    spec_file = tmp_path / "cycle_spec.yaml"
    spec_file.write_text(yaml.safe_dump(spec), encoding="utf-8")
    with pytest.raises(ValueError) as exc_info:
        check_outline({"sections": []}, spec_path=spec_file)
    msg = str(exc_info.value)
    assert "2.A" in msg
    assert "2.B" in msg


def test_depends_on_non_gap_is_ignored():
    """g) a depends_on id that is present in the outline (not a gap) is silently ignored."""
    # 5.3.5.1 IS present in dossier_incomplete — it is not a gap.
    # 5.3.5.3 depends on 5.3.5.1 and 5.3.5.2; only 5.3.5.3 is missing.
    res = check_outline(load_outline(SAMPLES / "dossier_incomplete.yaml"))
    gap_by_id = {g.section_id: g for g in res.gaps}
    # 5.3.5.1 not a gap → not in depends_on_gaps of 5.3.5.3
    assert "5.3.5.1" not in gap_by_id["5.3.5.3"].depends_on_gaps
    # the result is still valid (no exception)
    assert "5.3.5.3" in res.remediation_order
