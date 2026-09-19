# Problem Statement

**Official prompt (P2, Pharma & Biotech):** *Build a Bob solution with two modes: (1) Signal Detection — cluster adverse event reports and calculate PRR statistics to flag emerging safety signals. (2) Submission Readiness — check a dossier outline against ICH M4 CTD requirements, score completeness per module, and generate a gap report.*

## Who has this problem

Two people, in two different departments of every pharmaceutical company and every regulator:

**The pharmacovigilance scientist.** Their job is to notice, as early as possible, that an approved drug is hurting people. Their raw material is spontaneous adverse-event reports — from doctors, patients, lawyers, and the companies themselves — collected into databases like FDA's FAERS (FDA Adverse Event Reporting System). FAERS holds **over 20 million reports** and receives **more than a million new ones a year**. A single busy drug can have tens of thousands of reports across hundreds of different reaction terms.

**The regulatory affairs manager.** Their job is to get a new drug approved. The application — the *dossier* — is assembled in the ICH Common Technical Document (CTD) format: five modules, dozens of mandated sections, **often 100,000+ pages**, built over years by quality, non-clinical and clinical teams who each own a slice. A refuse-to-file for a structural omission is a filing error that costs the same as a scientific failure.

## Why it hurts

**Signal detection.** The Vioxx (rofecoxib) case is the reference disaster: the drug was on the market from 1999 to September 2004, and its cardiovascular risk is estimated to have caused **27,000+ heart attacks and sudden cardiac deaths** before withdrawal. The pattern was present in spontaneous reports and trial data well before action was taken. The failure was not a lack of data. It was that the data volume exceeded what humans could review, and the statistical screen that would have surfaced it was not being run systematically. Twenty years later the database is ten times bigger.

**Submission readiness.** One rejected or refused-to-file submission delays approval by **6–12 months** and costs **$50–100 million** in lost exclusivity and rework. The CTD structure is public and rigid, yet completeness is still tracked in spreadsheets by hand across dozens of contributors, and gaps are found by the agency rather than the applicant.

Both share a root cause the official problem statement names precisely: *too much complex data for manual review.*

## Why existing approaches fall short

| Approach | Where it falls down |
|---|---|
| Manual case review | Cannot scale past a few hundred reports; misses patterns that are only visible in aggregate. |
| Commercial PV platforms (Oracle Argus, ArisGlobal) | Powerful but expensive, closed, and built for case *processing*; signal detection is a paid add-on run periodically, not conversationally. Small companies, academics and regulators in low-resource settings have no access. |
| Ad-hoc statistics scripts | Every team re-implements PRR slightly differently, with no tests and no shared vocabulary. Results are not reproducible or explainable to a non-statistician. |
| Dossier checklists in Excel | No machine-readable link between the checklist and the ICH structure; no weighting by criticality; no detection of common mistakes like listing a parent section instead of its required children. |
| Generic LLM chat | Fluent, but it will confidently invent a PRR. Without a deterministic evidence layer underneath, an LLM is a liability in a regulated domain. |

The gap is not "we need an AI." It is: **a deterministic, tested statistical engine over real data, with an AI on top that reads the evidence and explains it** — and that can be driven conversationally by the person who actually has the question.

## Why now

- **The data is finally open.** openFDA exposes FAERS through a free public API, so the whole 20M-report database is queryable in seconds without a multi-gigabyte download.
- **The methods are settled.** PRR (Evans, Waller & Davis 2001), ROR, and chi-square screening have twenty years of regulatory precedent; there is no methodological debate to resolve, only an engineering job to do.
- **Agents can now call tools.** The Model Context Protocol lets an AI coding agent like IBM Bob invoke a real statistical engine rather than hallucinate one. That combination — grounded numbers, fluent explanation — did not exist as a practical pattern two years ago.

## What success looks like

A pharmacovigilance scientist asks Bob *"is there a cardiac signal for drug X?"* and gets back, in under a minute: the case counts, the PRR with its confidence interval, the chi-square, two real case narratives, the organ-system picture, the likely reporting biases, and a recommended next step — every number traceable to a query against the live FDA database.

A regulatory affairs lead drops in a dossier outline and gets back: overall readiness, each module's completeness, the critical gaps first with *why each one would trigger a refuse-to-file*, and a remediation order that respects dependencies between sections.

That is what Pharos does. See [solution-overview.md](solution-overview.md).
