---
description: Known or new? Split a drug's signals by the current FDA label
argument-hint: <drug> [brand names, comma-separated]
---
Run pharos `scan_signals` for **$1** (aliases: $2) and use the `fda_label` block and each row's `label_status`.

Give me:
1. which label was checked (product names, how many labels, most recent effective date) — or that there is no current label and what that probably means;
2. a table of clinical signals **not found on the label**, strongest first: reaction · n · PRR [CI];
3. for each of those, call `check_fda_label` with the two or three closest synonyms you can think of, and tell me whether it is genuinely absent or just worded differently on the label;
4. one line on the labelled signals, naming any in the boxed warning;
5. which of the genuinely-absent ones look like confounding by indication (the disease being treated showing up as a "reaction") rather than a candidate safety signal.

Remember the match is textual: say "not found on the label", never "unlabelled" as a regulatory fact.
