---
name: dossier-remediation
description: Turn an ICH M4 CTD completeness check into an ordered, owner-assigned remediation plan for a drug-approval dossier, using the pharos check_ctd_dossier and get_ctd_spec tools. Use when asked whether a dossier or submission is ready, what is missing, or what to fix first.
---

# Dossier remediation plan — Pharos SOP

1. **Check.** `check_ctd_dossier(outline_path=… | outline_json=…, region=US|EU)`. Never give a readiness opinion without it.
2. **Verdict first.** READY / NOT READY, overall %, number of critical gaps.
3. **Read the warnings.** A parent listed instead of its children ("4.2.3 Toxicology" as one block) means up to seven hidden gaps — explain that to the reader; it is the most common mistake.
4. **Order the work by dependency, then severity.** Summaries cannot be written before the reports they summarise:
   - 5.3.5.1 controlled studies → 5.3.5.3 integrated analyses (ISS/ISE) → 2.7 Clinical Summary → 2.5 Clinical Overview → 1.14 Labeling
   - 4.2.3.x toxicology reports → 2.6 nonclinical summaries → 2.4 Nonclinical Overview; 4.2.3.5 reproductive toxicity also feeds pregnancy labelling (1.14)
   - 3.2.S.4 / 3.2.P.5 specifications and 3.2.P.8 stability → 2.3 Quality Overall Summary
   - 5.3.5.1 → 5.2 tabular listing
5. **Assign an owner** to each gap: CMC/Quality (Module 3, 2.3) · Nonclinical (Module 4, 2.4, 2.6) · Clinical / Biostatistics (Module 5, 2.5, 2.7) · Regulatory operations (Module 1, tables of contents) · Medical writing (summaries) · Labelling (1.14).
6. **Say what each critical gap costs.** Use the `note` returned with the gap; distinguish *refuse-to-file* (weight 3) from *deficiency letter* (weight 2) from *administrative* (weight 1).
7. **Drafts count half.** List them separately as "finish, don't start".
8. **Output** a table — order · section · title · severity · status · owner · unblocks — then three sentences on the critical path and a realistic statement of what cannot be parallelised.

Scope honesty: the check is structural (is the section there, in what state) — it does not judge scientific adequacy. Module 1 is region-specific and simplified here; tell the reader to confirm against current agency guidance.
