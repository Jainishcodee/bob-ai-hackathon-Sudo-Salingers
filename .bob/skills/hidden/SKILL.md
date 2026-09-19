---
name: hidden
description: >-
  What is the standard screen HIDING for this drug? Automatic masking detection
  and correction
metadata:
  user-invocable: true
  disable-model-invocation: true
  argument-hint: '<drug> <as-of year> [brand names, comma-separated]'
---

Using the pharos `find_hidden_signals` tool, check **$1** (aliases: $3) as of the end of **$2**.

Report, in this order:
1. how many clinical signals the standard screen shows;
2. every **unmasked** reaction — standard PRR → corrected PRR, the masking product, and its share of that reaction's reports;
3. every **understated** signal (corrected PRR ≥ 25% higher);
4. whether the masking product's dominance is explained by a known event (withdrawal, litigation, safety communication) — say what you know and what you are unsure of;
5. one sentence on what a safety scientist relying on the standard screen in $2 would have missed.

Then re-run with min_share_pct 20 and 50 and tell me whether the hidden signals are the same. No causal language.
