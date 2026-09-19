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
- Bob, given one question, called the timeline tool, noticed Vioxx, and re-ran the corrected analysis **on its own initiative**. Transcript and screenshots in `demo/`.
- Submitted; Validate Submission green; shortlisted for Round 2.
