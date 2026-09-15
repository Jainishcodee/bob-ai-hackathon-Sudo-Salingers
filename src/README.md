# `src/` — Pharos source layout

```
src/
├── pharos/                     Python package — the evidence engine
│   ├── faers/client.py         openFDA (FAERS) client: count queries, disk cache, offline mode, retry/backoff
│   ├── faers/cache/            cached openFDA responses for the demo drugs (built by `pharos build-cache`)
│   ├── signals/stats.py        2×2 table → PRR, ROR (+95% CI), chi-square (Yates); Evans 2001 criteria
│   ├── signals/detector.py     scan one drug across all its reported reactions; administrative-term filter
│   ├── signals/cluster.py      group signals by MedDRA System Organ Class (curated map + heuristics)
│   ├── signals/timeline.py     year-by-year + cumulative PRR by FDA receive date; masking detection & correction; lead time vs regulatory actions
│   ├── ctd/data/ich_m4_ctd.yaml  ICH M4 CTD Modules 1–5 as a machine-readable checklist (69 leaf sections)
│   ├── ctd/checker.py          outline → matched sections → per-module weighted score → ranked gaps
│   ├── ctd/report.py           Markdown gap report
│   └── cli.py                  `python -m pharos` — scan · prr · timeline · ctd-check · ctd-template · build-cache
├── mcp_server/server.py        MCP server exposing 7 tools + 2 prompt templates to IBM Bob
├── app/streamlit_app.py        two-tab dashboard (Signal Detection incl. emergence timeline · Submission Readiness)
├── data/samples/               demo_drugs.txt · regulatory_actions.yaml · dossier_complete.yaml · dossier_incomplete.yaml
├── scripts/build_cache.py      wrapper to warm the offline cache (scans + headline timelines)
├── tests/                      pytest — 50 tests, all offline (fake clients), hand-computed reference values
├── requirements.txt · pyproject.toml · .env.example
```

Quick start (from this directory):

```bash
pip install -r requirements.txt
pip install -e . --no-build-isolation
python -m pharos scan rofecoxib --alias vioxx
python -m pharos timeline rosiglitazone "myocardial infarction" --alias avandia -x rofecoxib -x vioxx --to 2013
python -m pharos ctd-check data/samples/dossier_incomplete.yaml
streamlit run app/streamlit_app.py
python -m mcp_server.server        # for IBM Bob (stdio)
python -m pytest tests -q
```

Full instructions: [`../docs/setup-guide.md`](../docs/setup-guide.md).
