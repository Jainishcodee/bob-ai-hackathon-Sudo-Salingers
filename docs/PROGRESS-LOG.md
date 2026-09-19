# Progress log — IBM Bob Hackathon, Team Sudo Salingers

A running record of what changed and why. Newest first. On 19 Sept this file stays open on screen — add a line every time something ships or a mentor gives feedback.

---

## 19 Sept 2026 — on-site round  *(fill in live)*

| Time | What happened | Who / with Bob? | Commit |
|---|---|---|---|
| 08:30 | Arrived · `git pull` · tests green · dashboard + Bob up | | |
| | | | |
| | | | |

**Mentor feedback received today**

| Time | Mentor | Feedback / request | What we did about it |
|---|---|---|---|
| | | | |

---

## Between rounds — signal quality upgrades

### Task 1 — WHO-UMC Information Component (IC) beside PRR

- **New:** `ic()` and `ic025()` pure functions in `signals/stats.py` (Norén et al. 2013 shrinkage form). `DisproportionalityResult` gains four fields: `ic`, `ic025`, `is_signal_ic` (WHO rule: IC025 > 0 and n ≥ 3), `methods_agree`.
- **Why it matters:** FDA world uses PRR; WHO uses IC. When the two methods *disagree* (Evans fires but IC025 ≤ 0, or vice versa), it almost always means a small case count where the point estimate is unreliable. Showing both lets a reviewer see that immediately.
- **Where it surfaces:** scan table has four new columns; `prr` CLI panel shows `IC = … IC025 = … → WHO rule: SIGNAL / no signal`; scan CLI prints how many reactions where the two methods disagree; dashboard "All evaluated reactions" table adds an **IC025** column and a caption count of disagreeing rows; MCP `scan_signals` and `compute_prr` docstrings updated.
- **Tests added:** 11 new tests in `test_stats.py` and `test_detector.py` — every expected value hand-derived in a comment. Regression test locks the existing PRR/chi² values unchanged.
- **No existing behaviour changed.** `is_signal` (Evans rule) and `tier` are untouched; all IC fields default so existing call-sites need no update.

### Task 2 — Publicity-stimulated reporting flag on the timeline

- **New:** every timeline row carries `stimulated_reporting` (bool) and `share_vs_baseline` (ratio). A year is flagged when it is on/after the first regulatory action **and** the reaction's share of the drug's own reports is ≥ 2× the pre-action mean. Convention (not a published standard) — stated as such in every docstring.
- **Why it matters:** our Avandia table shows MI reports jumping from ~5% of Avandia's reports (2007) to 22% (2008) and 51% (2010), *after* the FDA acted — driven by news coverage, not new risk. Without this flag a reviewer seeing that PRR climb might think risk is worsening. Now the chart shades those years and the headline explicitly calls it out.
- **Where it surfaces:** `TimelineResult.stimulated_years` property; `headline()` appends a caution sentence when non-empty; `as_dict()` adds `stimulated_reporting_years` and an explanatory note; CLI `timeline` adds 📣 to the Flag cell for stimulated years plus a footnote; dashboard timeline chart adds a shaded grey `vrect` labelled "publicity-stimulated reporting" plus a `st.caption` explaining it; year-by-year table adds the two new columns; MCP `signal_emergence_timeline` docstring updated.
- **Zero extra API calls.** All data (`share_of_drug_reports_pct`) is already fetched in phase 1 of the timeline loop.
- **Tests added:** 5 new tests in `test_timeline.py` covering: flag fires correctly, no actions → empty, action before data → empty, flat share → empty, `as_dict` structure. All 22 existing timeline tests pass unchanged.
- **Total test count: 103** (was 80 before these two tasks; now 98 + 5 new timeline = 103).

---

## 17–18 Sept 2026 — between rounds

- **New: hidden-signal finder** (`signals/masking.py`, CLI `pharos hidden`, MCP `find_hidden_signals`, dashboard section). For any drug and any as-of year it checks each reaction for a dominant product (≥ 25% of the reaction's reports), removes it and its brand/generic aliases from the comparator, and recomputes. **Result on real data:** Avandia as of end-2006 → the standard screen shows 19 signals; Pharos finds **1 more that was hidden** — myocardial infarction, PRR 0.77 → 2.18 with Vioxx (66% of MI reports) excluded — and **5 understated**, including congestive heart failure (Avandia's actual boxed warning) 5.47 → 8.56. It also surfaced a masker we didn't know about: **Byetta** flooding the blood-glucose terms. **Second confirmation:** Meridia (sibutramine) as of 2006 → stroke (1.67 → 4.40) and heart attack (1.06 → 2.95) both hidden behind Vioxx — Meridia was withdrawn in 2010 for cardiovascular events and stroke.
- **New: rule-based, prospective masker selection** (`-x auto` on the timeline). Removes the caveat from Round 1 that *"the masking drug was chosen by an analyst"*. **We caught our own look-ahead bug here:** the first version excluded Celebrex in 2005 because Celebrex crossed 25% in *2007* — and reported first detection in 2005. That is using the future to explain the past. Fixed so a product is excluded only from the first year it crossed the threshold; first detection is **2006**, identical to the manual result. A test (`test_auto_exclusion_is_prospective_with_no_look_ahead`) locks it in.
- **New: FDA label check — known or new?** (`signals/label.py`, MCP `check_fda_label`, column in every scan). Uses openFDA's drug-label endpoint; prefers single-ingredient prescribing information so a combination product can't make a reaction look labelled. **Result:** metformin → 15 clinical signals → 12 already on the label (lactic acidosis correctly located in the **boxed warning**) → 3 not found. Withdrawn drugs correctly report "no current label".
- **Bug found and fixed: reaction matching was too loose.** We searched reactions with a phrase match, so "OEDEMA" also matched *oedema peripheral*, *pulmonary oedema*… (6× over-count) and disagreed with the FDA's own exact-term counts. Switched to exact preferred-term matching everywhere. Consequence: the pair query for Vioxx × MI now returns **n = 17,981, PRR 52.15 — identical to the scan** (it previously said 19,886). **Every headline number was re-verified:** Avandia standard first flag 2008, corrected 2006 — unchanged.
- Tests: 50 → **80**, all offline — including a headless run of the whole demo path (Avandia → hidden signals → rule-based timeline). Threshold check: the hidden Avandia MI signal is identical at every masker threshold from 20% to 60%. Cache rebuilt for scans, timelines (standard / named / auto), hidden-signal demos and labels.
- Docs: plain-English explainer with flow diagrams (`docs/THE-BIG-PICTURE.md`), 3-minute pitch, Q&A prep, on-site roadmap.

## 15 Sept 2026 — Round 1 (online)

- Built Pharos end to end: openFDA client with disk cache and offline mode; PRR / ROR / chi-square with Evans 2001 criteria; organ-system clustering; ICH M4 CTD checker (69 sections); Typer CLI; Streamlit dashboard; MCP server for IBM Bob.
- **The finding that shaped the project:** we expected Avandia's heart-attack signal to be obvious in 2005. It wasn't — the standard screen flags it in **2008**, after the FDA had acted. The year-by-year "who is filing these reports?" column showed why: **Vioxx litigation reports were ~70% of all MI reports in 2005–06**. Excluding them moves first detection to **2006**, a year before the Nissen meta-analysis.
- Bob, given one question, called the timeline tool, **identified Vioxx as the dominant product itself** (the prompt never named it), and ran the corrected analysis. Transcript and screenshots in `demo/`.
- Submitted; Validate Submission green; shortlisted for Round 2.
