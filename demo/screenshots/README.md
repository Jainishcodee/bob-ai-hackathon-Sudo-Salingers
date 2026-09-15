# Screenshots

At least three screenshots of the **running** application, named sequentially. Take them at 1920×1080 if you can; PNG.

| File | What to capture | How to get there |
|---|---|---|
| `01-signal-scan-vioxx.png` | Dashboard Tab 1 after scanning **ROFECOXIB · Vioxx**: metric row (45,770 reports, ~30 clinical signals), PRR bar chart with confidence intervals, organ-system chart. | `streamlit run app/streamlit_app.py` → Tab 1 → dropdown already on Vioxx → **Scan for signals** |
| `02-avandia-timeline-masking.png` | **The money shot.** Tab 1 with **ROSIGLITAZONE · Avandia** scanned → *When did this signal emerge?* built with `ROFECOXIB, VIOXX` excluded: the four metrics (standard 2008 / corrected 2006 / Nissen 2007 / lead time +1), the 🎭 masking warning, and the chart with the red standard line, green corrected line and blue milestone markers. | Dropdown → Avandia → **Scan** → in the timeline expander leave the default exclude → **Build timeline** |
| `03-ctd-readiness.png` | Tab 2 with the **incomplete dossier**: NOT READY, module completeness bars, the ranked gap table with critical rows, the "4.2.3 listed as a single section" warning. | Tab 2 → *Sample — incomplete dossier* |
| `04-prr-drilldown.png` *(optional)* | The 2×2 drill-down for *Myocardial Infarction*: the a/b/c/d table and the PRR / ROR / χ² / SIGNAL metrics. | Tab 1 → expand **Drill into one drug–reaction pair** → MYOCARDIAL INFARCTION → **Compute exact 2×2** |
| `06-cli-timeline.png` *(optional)* | Terminal output of the Avandia timeline command with `-x rofecoxib -x vioxx` — the headline panel and the `VIOXX (72%) ⚠` column. | Terminal, wide window |
| `05-bob-memo.png` *(strongly recommended)* | IBM Bob with the Pharos MCP tools listed, and Bob's signal-assessment memo after calling `scan_signals` / `compute_prr` / `search_reports`. | Bob, per `docs/bob-integration.md` |

Delete this table's optional rows or keep them — only the first three are required.
