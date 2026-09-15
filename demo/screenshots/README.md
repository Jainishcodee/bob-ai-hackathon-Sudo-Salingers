# Screenshots

At least three screenshots of the **running** application, named sequentially. Take them at 1920×1080 if you can; PNG.

| File | What to capture | How to get there |
|---|---|---|
| `01-signal-scan-vioxx.png` | Dashboard Tab 1 after scanning **ROFECOXIB · Vioxx**: metric row (45,770 reports, ~30 clinical signals), PRR bar chart with confidence intervals, organ-system chart. | `streamlit run app/streamlit_app.py` → Tab 1 → dropdown already on Vioxx → **Scan for signals** |
| `02-avandia-timeline-masking.png` | **The money shot.** Tab 1 with **ROSIGLITAZONE · Avandia** scanned → *When did this signal emerge?* built with `ROFECOXIB, VIOXX` excluded: the four metrics (standard 2008 / corrected 2006 / Nissen 2007 / lead time +1), the 🎭 masking warning, and the chart with the red standard line, green corrected line and blue milestone markers. | Dropdown → Avandia → **Scan** → in the timeline expander leave the default exclude → **Build timeline** |
| `03-ctd-readiness.png` | Tab 2 with the **incomplete dossier**: NOT READY, module completeness bars, the ranked gap table with critical rows, the "4.2.3 listed as a single section" warning. | Tab 2 → *Sample — incomplete dossier* |
| `04-prr-drilldown.png` *(optional)* | The 2×2 drill-down for *Myocardial Infarction*: the a/b/c/d table and the PRR / ROR / χ² / SIGNAL metrics. | Tab 1 → expand **Drill into one drug–reaction pair** → MYOCARDIAL INFARCTION → **Compute exact 2×2** |
| `06-cli-timeline.png` *(optional)* | Terminal output of the Avandia timeline command with `-x rofecoxib -x vioxx` — the headline panel and the `VIOXX (72%) ⚠` column. | Terminal, wide window |
| `05a-bob-timeline-toolcalls.png` **(required — the Bob proof)** | Top of the Bob chat: the Avandia prompt, the two **Ran Signal Emergence Timeline (pharos)** tool-call cards, and Bob's line "Vioxx dominated the MI background at up to 72%… now running the masking-corrected screen". Shows Bob deciding to re-run with `exclude_drugs` by itself. | Bob → Agent mode → Avandia prompt from `docs/bob-integration.md` §3 |
| `05b-bob-standard-vs-corrected.png` | Bob's section 2 table: standard cumulative PRR vs Vioxx-excluded PRR by year, with **FIRST FLAG** at 2008 (standard) and 2006 (corrected). | Scroll down in the same answer |
| `05c-bob-key-dates.png` | Bob's section 3: corrected screen end-2006 → Nissen May 2007 → FDA Nov 2007 → standard screen end-2008, with lead times. | Same answer |
| `06-bob-vioxx-assessment.png` | Bob orchestrating 8 Pharos tool calls for rofecoxib — `scan_signals`, `cluster_signals_by_organ_system`, then 3× `compute_prr` + 3× `search_reports` in parallel. Bob wrote the resulting memo as an HTML report: see `../transcripts/vioxx-signal-memo-by-bob.html`. | Prompt in `docs/bob-integration.md` §3 "Signal assessment" |
| `07-bob-mcp-connected.png` | Bob Settings → MCP showing `pharos · Connected`. | Bob Settings → MCP |
| `08-bob-ask-mode.png` | Ask mode: Bob explaining `src/pharos/signals/stats.py` and checking the PRR / χ² formulas — "built with Bob" evidence. | Bob → Ask mode |
| `09-bob-ctd-memo.png` *(optional)* | Bob's remediation memo after `check_ctd_dossier` on the incomplete sample. | Prompt in `docs/bob-integration.md` §3 "Dossier remediation plan" |

Delete this table's optional rows or keep them — only the first three are required.
