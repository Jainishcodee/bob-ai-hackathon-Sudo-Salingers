"""Headless smoke test of the Streamlit dashboard using Streamlit's AppTest harness.

Runs the real script, clicks the real Scan button, and asserts nothing raised. Served from
the committed openFDA cache (conftest sets PHAROS_OFFLINE=1), so no network is needed.
"""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parent.parent / "app" / "streamlit_app.py"
CACHE = Path(__file__).resolve().parent.parent / "pharos" / "faers" / "cache"


def _app() -> AppTest:
    return AppTest.from_file(str(APP), default_timeout=120)


def test_dashboard_renders_without_exception():
    at = _app().run()
    assert not at.exception, [e.value for e in at.exception]
    assert at.title[0].value.endswith("Pharos")
    assert len(at.tabs) == 2


@pytest.mark.skipif(not any(CACHE.glob("*.json")), reason="openFDA cache not built — run `python -m pharos build-cache`")
def test_vioxx_scan_from_cache_renders_signals():
    at = _app().run()
    # Demo dropdown defaults to ROFECOXIB · Vioxx, so the drug inputs are pre-filled.
    assert at.text_input[0].value == "ROFECOXIB"
    at.button[0].click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert not at.error, [e.value for e in at.error]  # surfaces OpenFDAError / cache-miss messages
    labels = [m.label for m in at.metric]
    assert "Clinical signals" in labels
    clinical = next(m for m in at.metric if m.label == "Clinical signals")
    assert int(clinical.value) > 5
    # the strongest-signal metric should name a cardiovascular term for Vioxx
    strongest = next(m for m in at.metric if m.label == "Strongest signal")
    assert strongest.value  # non-empty


def test_ctd_tab_shows_not_ready_for_incomplete_sample():
    at = _app().run()
    assert not at.exception
    labels = {m.label: m.value for m in at.metric}
    assert labels.get("Verdict") == "NOT READY"
    assert int(labels.get("Critical gaps", 0)) >= 3
