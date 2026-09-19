# Signal assessment — {DRUG} ({BRANDS})

**Date:** {today} · **Data:** openFDA FAERS, reports received 2004–{year} · **Reports mentioning the product:** {n_drug} · **Prepared with:** Pharos + IBM Bob

## BLUF

{One sentence: what was found, how strong, what you recommend.}

## Evidence

| Reaction | n | PRR [95% CI] | χ² | Evans met? | On FDA label? |
|---|---|---|---|---|---|
| | | | | | |

*Figures from exact 2×2 queries (`compute_prr`). Evans 2001: n ≥ 3, PRR ≥ 2, χ² ≥ 4.*

## New vs known

- **Not found on the current label:** …
- **Already labelled:** … (boxed warning: …)

## Masking

{What `find_hidden_signals` found as of {year}: hidden reaction, standard → corrected PRR, masking product and its share of the reaction's reports. Or: "No product held ≥ 25% of any checked reaction's reports."}

## When did it emerge?

| | Year |
|---|---|
| Standard screen first flags | |
| Rule-based masking correction first flags | |
| First regulatory / scientific milestone | |

{Lead or lag in whole years. Exclusion schedule as returned by the tool.}

## Cases reviewed

1. {age/sex · seriousness · co-suspect drugs · what stands out}
2. …

## Reporting biases that apply here

{Specific: stimulated reporting from litigation/media, notoriety, confounding by indication, channelling, Weber effect.}

## Recommendation

**{no action · continue monitoring · formal causality assessment · label review · urgent escalation}** — {one sentence why}.

---
*Disproportionality in spontaneous reports shows a reporting association, not causation or incidence. "Not on the label" reflects a text match against the current US label.*
