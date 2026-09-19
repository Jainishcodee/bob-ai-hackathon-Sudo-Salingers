---
name: masking-audit
description: Audit whether masking (one product flooding a reaction's reports) is hiding or understating safety signals for a drug or across a drug class, year by year, using the pharos find_hidden_signals and signal_emergence_timeline tools. Use when asked about masking, hidden signals, why a signal appeared late, competition bias, or the effect of litigation-driven reporting.
---

# Masking audit — Pharos SOP

**What masking is.** PRR compares a drug with *all other drugs*. If one product's reporting wave (lawsuits, media, a recall) makes up a large share of a reaction's reports, the background rate inflates and that reaction is hidden for everyone else. It is time-local: Vioxx is ~10% of myocardial-infarction reports across all of FAERS but was 69–73% in 2005–06.

## Procedure

1. **Choose the years.** Masking only shows inside the window where the wave happened. For a historical question, audit each year-end separately: call `find_hidden_signals(drug, aliases, as_of_year=Y)` for Y across the period of interest (e.g. 2004 → 2008).
2. **Tabulate by year**: standard signals · unmasked · understated · the masking product(s) and their share.
3. **Follow the most serious unmasked reaction** with `signal_emergence_timeline(drug, reaction, aliases, exclude_drugs="auto")`. Report first-flag year standard vs corrected and the `exclusion_schedule`.
4. **Sanity-check the masker.** Is its dominance explained by a known event (withdrawal, litigation, a Dear-Doctor letter)? Say what you know and flag what you don't. A co-prescribed drug (e.g. Byetta with other diabetes drugs) dominating a *pharmacological* term like "blood glucose decreased" is closer to confounding by co-medication than to a reporting wave — distinguish the two.
5. **Robustness.** Re-run step 1 for the key year with `min_share_pct` 20 and 50. If the hidden signal appears at both, say the result does not depend on the threshold.
6. **For a class question**, repeat for each member and compare: which drugs were masked, by what, in which years.

## Reporting rules

- The masker is chosen by the fixed share rule. Never substitute your own choice to get a better year.
- The timeline rule is prospective: a product is excluded only from the first year it crossed the threshold. If asked "could it have been seen in year Y?", only maskers known by Y count.
- "Unmasked" = meets the same Evans criteria once the comparator is corrected. It is still a reporting association.
- Exclusion changes the comparator only; the drug's own reports are untouched.
- Cite: Maignen et al. 2014 (*Pharmacoepidemiol Drug Saf*) and Wang et al. 2010 for the phenomenon. The method is not novel; applying it routinely, by rule, per year, is what Pharos adds.

## Known reference result (use to sanity-check your run)

Rosiglitazone (Avandia) × MYOCARDIAL INFARCTION: standard cumulative PRR first meets the criteria in **2008**; rule-based correction (Vioxx excluded from 2004; Celebrex/Bextra from 2007) → **2006**; Nissen meta-analysis May 2007, FDA boxed warning Nov 2007. As of end-2006 the standard PRR is 0.77 and the corrected PRR 2.18. If your numbers differ wildly, check the aliases you passed.
