# Solution Overview

Pharos is a two-mode drug-safety evidence engine with IBM Bob as the reasoning layer on top. The name is the lighthouse of Alexandria: an early-warning beacon (Mode 1) that also guides ships safely into port (Mode 2).

## The core mechanism

### Mode 1 — Signal Detection

Every signal-detection question reduces to a **2×2 contingency table**:

|  | reaction Y | all other reactions |
|---|---|---|
| **drug X** | a | b |
| **all other drugs** | c | d |

openFDA's `count` endpoint returns the four marginal totals directly (total reports, reports for drug X, reports for reaction Y, and reports for X-and-Y), so the whole table costs three or four small HTTP requests — **no multi-gigabyte FAERS download**, live data at demo time.

From the table Pharos computes the standard pharmacovigilance screen:

- **PRR** — Proportional Reporting Ratio (Evans, Waller & Davis 2001): the share of drug-X reports that mention Y, divided by the same share among all other drugs.
- **ROR** — Reporting Odds Ratio with 95% CI (the EMA/Eudravigilance companion metric).
- **χ²** — Yates-corrected chi-square.
- **Signal flag** — Evans criteria: PRR ≥ 2, χ² ≥ 4, ≥ 3 cases. Thresholds are user-adjustable.
- **Haldane–Anscombe correction** when any cell is zero, so ratios stay finite.

A **scan** does this for every reaction reported with a drug (up to 500 keyless) using one background request for the top-500 reaction totals across all of FAERS, ranks clinical signals first by PRR, and **clusters** them by MedDRA System Organ Class so the analyst sees "this is a cardiac problem" rather than 30 separate terms.

Two pieces of domain judgement are built in rather than left to the user:

1. **Administrative-term filtering.** FAERS is dominated by terms like *DRUG INEFFECTIVE*, *OFF LABEL USE*, *PRODUCT USED FOR UNKNOWN INDICATION*. They are statistically "signals" and clinically meaningless. Pharos computes them, shows them, and excludes them from the clinical signal count.
2. **Alias matching.** Older reports name the brand, not the molecule. Searching "rofecoxib" alone finds 1,569 reports; adding the alias "Vioxx" finds 45,770. Pharos ORs every name across the verbatim and FDA-harmonised name fields.

### The emergence timeline — *when*, and *what hid it*

A static scan answers "is there a signal now?" A safety scientist's real question is "**when** could we have known?" — and, if the answer is "late", **why**.

`signal_timeline()` rebuilds the 2×2 table for every calendar year using the FDA **receive date**, so the cumulative series for year *Y* uses only reports the agency had by 31 December *Y*. The first year the cumulative table meets the criteria is the *first-flag year*; set against the drug's real regulatory milestones (`data/samples/regulatory_actions.yaml`) it yields a lead time. This is the "first seen" field of an error-monitoring tool, or a control chart in manufacturing — a detection history instead of a snapshot.

It also runs a **masking check** each year: which drugs dominate the reaction's reports? Disproportionality compares a drug against *all other drugs*; if one drug's reporting wave makes up most of a reaction's reports, the background inflates and the same reaction is hidden for everyone else. This is a documented failure mode (Maignen et al. 2014; Wang et al. 2010), and Pharos both detects it (`top_contributor`, `masking_alert`) and corrects it (`--exclude` removes the named drug from the comparator).

**The real result that shaped this feature.** We expected Avandia's MI signal to be obvious in 2005. It wasn't: FAERS's background MI rate was 4.5–5.5% in 2005–06 because **Vioxx litigation reports were 69–73% of all MI reports** — Pharos's masking column showed `VIOXX (73%) ⚠`. Under the standard screen, Avandia × MI first meets the criteria in **2008**, a year after the Nissen meta-analysis and after FDA's boxed warning. Exclude Vioxx from the comparator and it meets them in **2006** — a year *before* Nissen. Detection moves forward two years, on real data, by a literature-standard correction. The tool told us we were wrong and then told us why; that is exactly the behaviour a pharmacovigilance tool should have.

Where no masking is present the same timeline gives clean prospective results: Meridia (sibutramine) × cerebrovascular accident meets the criteria in **2004** (n=16, PRR 5.0, χ² 48), five years before FDA's SCOUT-trial communication; Darvon (propoxyphene) × cardiac arrest in **2005** (PRR 3.0, χ² 100), four years before EMA's withdrawal recommendation. These say the *screen* would have flagged the pair early — not that regulators were unaware of class risks.

**From one finding to a screen: the hidden-signal finder.** A result that depends on an analyst spotting Vioxx is an anecdote. `find_hidden_signals()` (`signals/masking.py`) makes it a method: for one drug and one receive-date window it runs the standard screen, asks openFDA which products dominate each reaction's reports, removes any single product holding ≥ 25% (with its brand/generic aliases) from the comparator, and recomputes. Run as of end-2006 it finds Avandia's hidden heart-attack signal by itself (PRR 0.77 → 2.18) and shows congestive heart failure — Avandia's actual boxed warning — understated by a third. For Meridia it finds stroke (1.67 → 4.40) and heart attack (1.06 → 2.95) hidden behind the same Vioxx wave, four years before Meridia's withdrawal for cardiovascular events. On the timeline the same rule runs as `exclude="auto"`, applied **prospectively**: a product is excluded only from the first year it crossed the threshold. Our first implementation excluded Celebrex in 2005 because Celebrex crossed 25% in 2007 — and reported detection in 2005. That is look-ahead bias; we caught it, fixed it, and locked it with a test. The honest answer is 2006.

### Known or new? — the FDA label check

The first question a safety scientist asks about a statistical signal is *is it labelled?* A hit for a reaction already in the boxed warning is expected; one that appears nowhere on the label is the one worth a human's time. `signals/label.py` pulls the current FDA-approved label from openFDA's `/drug/label` endpoint (preferring single-ingredient prescribing information, so a combination product's other ingredient cannot make a reaction look labelled), normalises British MedDRA spelling to American label spelling, applies a synonym table (*pyrexia* → fever, *cerebrovascular accident* → stroke), and falls back to requiring every significant word of the term within one sentence. Each signal is tagged by the most prominent section where it appears — boxed warning › warnings & precautions › contraindications › adverse reactions — or **not found on the label**. Metformin: 15 clinical signals → 12 labelled, lactic acidosis correctly located in the boxed warning → 3 not found. It is a text match and reported as such: "not on the label" means *go and read it*, not a regulatory determination.

### Mode 2 — Submission Readiness

ICH M4's CTD structure is encoded once as a **machine-readable checklist** — [`src/pharos/ctd/data/ich_m4_ctd.yaml`](../src/pharos/ctd/data/ich_m4_ctd.yaml) — with 69 leaf sections across Modules 1–5, each carrying:

- `required` — true for every NDA/MAA, or false where applicability depends on the product (e.g. 3.2.A.2 Adventitious Agents, needed only for biologics);
- `weight` — 3 critical (refuse-to-file grade), 2 major (deficiency letter), 1 minor (administrative);
- `note` — one line of *why it matters*, written for the gap report.

A dossier outline (YAML/JSON: section id, title, status) is matched against the checklist by normalised id, falling back to fuzzy title matching. Each module's score is the weighted share of required sections present (drafts count half). The result is a ranked gap list, warnings for common mistakes — a parent listed instead of its children, duplicates, unrecognised entries — and a ready-to-submit verdict. Module 1 is regional, so the checklist ships US and EU variants.

## What makes it different from the naive version

| Naive approach | Pharos |
|---|---|
| Ask an LLM "is there a signal for drug X?" | Deterministic statistics from live FDA data; the LLM only *reads* them. |
| Download quarterly FAERS files and run a notebook | Three HTTP requests per pair; results in seconds; cached to disk; offline mode. |
| Invent a "risk score" | The exact metrics and thresholds regulators use, with citations, unit-tested against hand-computed values. |
| Show the top reaction terms | Filter administrative noise, cluster by organ system, rank by evidence strength. |
| Treat all 35 signals as equally urgent | Split them by the actual FDA label: already known (and how prominently) vs **not on the label**. |
| Trust the standard screen's silence | Check every reaction for a dominant product and show what the screen is hiding — by rule, not by analyst. |
| Report a signal exists today | Show the year it first became detectable, against real regulatory dates — and detect and correct the masking that delayed it. |
| Checklist in a spreadsheet | Checklist as data; weighted scoring; detects structural mistakes; generates blank outlines. |

## Where IBM Bob is load-bearing

Pharos deliberately stops at the numbers. The MCP server ([`src/mcp_server/server.py`](../src/mcp_server/server.py)) exposes nine tools and two prompt templates; **Bob is the analyst**:

1. **Scan** → Bob calls `scan_signals` and sees the ranked table.
2. **Verify** → for the top signals Bob calls `compute_prr` (an exact `AND` query rather than the count approximation) and `search_reports` to read real case narratives.
3. **Contextualise** → `cluster_signals_by_organ_system` gives the organ-system picture.
4. **Triage** → the `fda_label` block splits signals into already-labelled and not-on-label; `find_hidden_signals` checks whether masking is hiding anything.
5. **Date it** → `signal_emergence_timeline` (with `exclude_drugs="auto"`) establishes when the lead signal first met the criteria, whether another drug's reporting masked it, and the lead time versus regulatory action.
6. **Write** → Bob produces a BLUF-style memo: verdict, evidence table, emergence year, biases, next step.

The server's `instructions` constrain that behaviour — always state n, PRR with CI and χ²; never claim causation; name reporting biases such as litigation-driven or notoriety-driven reporting. The same pattern runs for Mode 2: `check_ctd_dossier` returns structured gaps; Bob writes the remediation plan with dependency ordering and owning teams.

Remove Bob and Pharos still computes — but it no longer explains, prioritises, or converses. Remove Pharos and Bob would be guessing. That is the sense in which the integration is load-bearing rather than decorative.

## Key design decisions

- **openFDA over raw files** — speed and liveness beat completeness for a triage tool; the raw-file loader is the obvious next step for production.
- **Standard metrics only** — no invented scores. Credibility in a regulated domain comes from using the literature's methods exactly.
- **Evidence/reasoning split** — the deterministic layer is testable; the LLM layer is replaceable. Neither has to pretend to be the other.
- **Cache + offline mode** — a demo should not depend on Wi-Fi. `pharos build-cache` snapshots the demo drugs; `PHAROS_OFFLINE=1` forces cache-only.
- **Mode 1 deep, Mode 2 competent** — the prompt asks for both; we invested where the demo value is and say so in `known_limitations`.

## What the user experience looks like

**In Bob** — the primary interface. *"Run a signal assessment for rosiglitazone (alias Avandia)."* Bob calls the tools and returns a memo with the numbers, the cases, and a recommendation.

**Dashboard** — `streamlit run app/streamlit_app.py`. Tab 1: pick a demo drug or type one, adjust criteria, scan; PRR bar chart with confidence intervals, organ-system chart, full table, 2×2 drill-down, and the Bob prompt to copy. Tab 2: choose or upload an outline; module completeness bars, ranked gaps, warnings, downloadable Markdown report, and the Bob prompt.

**CLI** — `python -m pharos scan …`, `prr …`, `ctd-check …`, `ctd-template`, `build-cache`. Rich tables, JSON output for pipelines.

## Honest scope

- Retrospective validation, not prospective detection (openFDA starts in 2004).
- Reporting disproportionality ≠ incidence or causation; Pharos is triage.
- Heuristic organ-system mapping because MedDRA is licensed.
- Mode 2 checks structure, not scientific content.

See [architecture.md](architecture.md) for components and data flow, and [bob-integration.md](bob-integration.md) for connecting Bob.
