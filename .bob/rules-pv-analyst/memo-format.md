# PV Analyst — how to write the memo

Audience: a safety review board. They read the first sentence and the table; everything else is reference.

1. **BLUF** — one sentence: what was found, how strong, what you recommend.
2. **Evidence table** — one row per signal: reaction · n · PRR [95% CI] · χ² · Evans met? · on FDA label? (section, or "not found").
3. **New vs known** — which signals are not on the label. If the product has no current label (withdrawn), say so and do not guess.
4. **Masking** — what `find_hidden_signals` found: the hidden reaction, standard → corrected PRR, the masking product and its share. If nothing, say "no product held ≥ 25% of any checked reaction".
5. **When** — for the lead signal: first-flag year under the standard screen, under the rule-based correction, and the real regulatory milestones. State lead or lag in years. Do not convert to months unless you compute from exact dates.
6. **Cases** — two or three real reports in one line each (age, sex, seriousness, co-suspect drugs). Note confounders you can see.
7. **Biases** — which apply here and why.
8. **Recommendation** — one of: no action · continue monitoring · formal causality assessment · label review · urgent escalation. One sentence of justification.

Keep it to one page. No causal language. Every number from a tool call.
