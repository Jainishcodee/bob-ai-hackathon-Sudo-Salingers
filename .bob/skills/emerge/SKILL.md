---
name: emerge
description: >-
  When could this signal first have been seen — and what masked it? Year-by-year
  replay against real regulatory dates
metadata:
  user-invocable: true
  disable-model-invocation: true
  argument-hint: '<drug> "<reaction>" [brand names, comma-separated]'
---

Using the pharos `signal_emergence_timeline` tool, replay **$1** (aliases: $3) × **$2** year by year from 2004.

1. Run it with no exclusion. State the first year the standard cumulative screen met the criteria, and read the `top_contributor` column: did any product hold ≥ 25% of this reaction's reports in any year?
2. Run it again with exclude_drugs="auto". State the corrected first-flag year and the `exclusion_schedule` (which product was excluded from which year — the rule is prospective, no look-ahead).
3. Put both years next to the regulatory milestones the tool returns. Lead or lag, in whole years.
4. Give me a small table: year · cases / drug reports · background % · top product (share) · cumulative PRR standard · cumulative PRR corrected.
5. One paragraph: what this implies about how the screen should be run. No causal language; do not convert years to months.
