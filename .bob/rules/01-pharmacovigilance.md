# Pharos — domain rules (apply in every mode)

Pharos is a pharmacovigilance tool. People may act on what you say about a medicine, so precision is not optional.

## Language

- A disproportionality statistic is **never** evidence of causation. Say "signal", "reporting association", "disproportionately reported". Never "causes", "proves", "is responsible for".
- Never say a drug "is safe" because a PRR is low. A PRR **below 1** for a serious event is a reason to check for masking, not reassurance.
- Never say Pharos would have "saved lives" or "beaten the FDA". Say what the screen shows and when.
- "Not on the label" means *not found by text match in the current US label*. It is a prompt to read the label, not a regulatory finding. Say it that way.

## Numbers

- Any FAERS number you state must come from a `pharos` MCP tool call in this conversation. Do not compute PRR, ROR or chi-square yourself and do not recall figures from memory.
- When you describe a signal, always give: case count (n), PRR with its 95% CI, chi-square, and whether it meets the Evans 2001 criteria (n ≥ 3, PRR ≥ 2, χ² ≥ 4).
- Before writing about a signal from `scan_signals`, confirm it with `compute_prr` (exact query).
- State the data window. openFDA FAERS begins in 2004; anything about earlier years is out of scope.

## Method

- Lead with signals **not on the FDA label**; labelled signals are expected.
- For any serious event with PRR < 2, or any drug studied in 2004–2007, run `find_hidden_signals` — Vioxx litigation reports were 69–73% of all myocardial-infarction reports in 2005–06 and masked other drugs.
- When dating a signal use `signal_emergence_timeline` with `exclude_drugs="auto"`. The automatic rule is prospective (no look-ahead); do not hand-pick a masker to get an earlier year.
- Always name plausible reporting biases: stimulated reporting (litigation, media), notoriety bias, confounding by indication, channelling, the Weber effect for new drugs.
