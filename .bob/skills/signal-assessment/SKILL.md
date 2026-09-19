---
name: signal-assessment
description: Standard operating procedure for a full pharmacovigilance signal assessment of one drug using the pharos MCP tools — scan, label triage, exact verification, case review, masking check, emergence timeline, and a one-page BLUF memo. Use when asked to assess, review, investigate or write up a drug's safety signals.
---

# Signal assessment — Pharos SOP

You are producing a memo a safety review board could act on. Follow the steps in order. Every number must come from a tool call made in this conversation.

## 0. Pin down the product

Ask for (or infer and state) the generic name **and** brand names. Older FAERS reports use brands: "rofecoxib" alone finds 1,569 reports; adding "vioxx" finds 45,770. Pass brands as `aliases`.

## 1. Scan

`scan_signals(drug, aliases)`. Note: reports mentioning the drug, clinical signals found, and the `fda_label` block.

## 2. Triage by label — new before known

From the rows' `label_status`:
- **Not found on the label** → these lead the memo.
- **Labelled** → expected; mention the boxed-warning ones in one line.
- **No current label** (withdrawn product) → say so; do not guess what the label said.

Remember the match is textual. If an "unlabelled" term is a near-synonym of a labelled one (e.g. *acute kidney injury* vs "renal impairment"), say that rather than calling it new.

## 3. Verify

For the top 3 signals you intend to write about, call `compute_prr(drug, reaction, aliases)`. Use these exact figures in the memo. If the exact query disagrees materially with the scan, report both and say why (the scan uses term counts).

## 4. Read real cases

`search_reports(drug, reaction, aliases, limit=3)` for each. Look for: co-suspect drugs, indication that explains the event (confounding by indication), implausible timing, duplicate-looking reports, litigation markers (lawyer reporters, clusters of identical narratives).

## 5. Check for masking — always

`find_hidden_signals(drug, aliases, as_of_year=…)`. Masking is time-local, so choose the year that matters to the question (default: current). Report `unmasked` rows as findings and `strengthened` rows as "understated by the standard screen". If a serious event has standard PRR < 1, treat that as a red flag for masking, not as reassurance.

## 6. Date the lead signal

`signal_emergence_timeline(drug, reaction, aliases, exclude_drugs="auto")`. Report: first-flag year (standard), first-flag year (rule-based correction), the exclusion schedule, and the regulatory milestones returned. State lead/lag in whole years. Never hand-pick a masker to improve the date.

## 7. Organ-system picture

`cluster_signals_by_organ_system` — one sentence: which system dominates.

## 8. Write the memo

Use `memo-template.md` in this skill folder. One page. No causal language. End with exactly one recommendation: *no action · continue monitoring · formal causality assessment · label review · urgent escalation*.

## Self-check before you send

- [ ] Every number traceable to a tool call above
- [ ] n, PRR [95% CI], χ² given for each signal discussed
- [ ] Unlabelled signals lead
- [ ] Masking checked and reported (even if nothing found)
- [ ] Biases named specifically, not generically
- [ ] No "causes", "proves", "safe"
- [ ] Data window stated (openFDA FAERS from 2004)
