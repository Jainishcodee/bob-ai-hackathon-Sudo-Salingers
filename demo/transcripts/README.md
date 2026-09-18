# Bob transcripts and generated artifacts

Outputs written by **IBM Bob** after calling the Pharos MCP tools — the "reasoning layer" in action. Nothing here was hand-edited.

| File | What it is | Tools Bob called to produce it |
|---|---|---|
| `vioxx-signal-memo-by-bob.html` | BLUF pharmacovigilance signal memo for rofecoxib (Vioxx) — verdict, evidence table (n, PRR [95% CI], χ²), organ-system picture, reporting biases, next step. Bob chose to emit it as a standalone HTML report. | `scan_signals` → `cluster_signals_by_organ_system` → 3× `compute_prr` + 3× `search_reports` (8 calls; see `../screenshots/06-bob-vioxx-assessment.png`) |
| `avandia-masking-analysis.md` *(add if saved)* | Bob's year-by-year analysis of rosiglitazone × myocardial infarction: standard screen flags 2008, Bob detects Vioxx at 72% of MI reports, re-runs with `exclude_drugs` on its own, corrected screen flags 2006. | `signal_emergence_timeline` ×2 (see `../screenshots/05a–05c`) |

**Note on numbers:** the 15 Sept transcripts predate a fix to reaction matching (phrase → exact MedDRA preferred term). Bob's figures there — e.g. Vioxx × MI n = 19,886, PRR 49; Vioxx share 68–72% — are what the tools returned that day. Current values: n = 17,981, PRR 52; share 69–73%. The conclusions (standard 2008 → corrected 2006) are unchanged. See `docs/round2/PROGRESS-LOG.md`.

Open the `.html` in any browser. Numbers in these files come from live openFDA queries at the time Bob ran them and may drift slightly as FDA adds reports.
