# Pharos — slide deck outline

Render to `presentation/slides.pdf` (preferred) or `slides.pptx`. Order follows the submission guide: Problem → Solution → Demo/architecture → IBM technology → Impact. Ten slides, ~5 minutes. Speaker notes in *italics*.

---

## 1 · Title

**Pharos** — *a lighthouse for drug safety*
Drug Safety Signal Detector & Regulatory Submission Readiness Checker
Team Sudo Salingers · IBM Bob AI Innovation Hackathon 2026 · Problem P2 (Pharma & Biotech)

*The Pharos was the lighthouse of Alexandria — a beacon that warns of danger and guides ships safely into port. Two jobs, one light. That's the product.*

---

## 2 · The problem — who, what, why it hurts

- **20,000,000+** adverse-event reports in FDA's FAERS. +1M a year.
- **Vioxx:** cardiovascular signal sat in the data; **27,000+ heart attacks** before withdrawal (2004).
- **100,000-page** drug dossiers assembled by hand in the 5-module ICH CTD structure.
- One missing section → refuse-to-file → **6–12 months, $50–100M.**
- Same root cause: *too much structured data for manual review.*

*Two people: the pharmacovigilance scientist who can't read the pile, and the regulatory lead who can't see the hole in the dossier until the agency does.*

---

## 3 · Why nothing fixes it today

| | |
|---|---|
| Manual review | doesn't scale past hundreds of reports |
| Commercial PV platforms | expensive, closed, periodic — not conversational |
| Notebook scripts | untested, irreproducible, unexplainable |
| Excel checklists | no link to the ICH structure, no weighting |
| Plain LLM chat | will confidently invent a PRR |

**Missing piece:** a deterministic, tested evidence engine over *real* data, with an AI on top that *reads* the evidence.

---

## 4 · The solution — two modes, one engine

**Mode 1 · Signal Detection** — live openFDA → 2×2 table → **PRR · ROR (95% CI) · χ² · Evans 2001** → rank → filter admin noise → cluster by organ system.

**Mode 2 · Submission Readiness** — ICH M4 CTD as a **69-section machine-readable checklist** (required · weight · why-it-matters) → match outline → per-module score → ranked gaps.

**IBM Bob** = the analyst. Calls the tools over MCP, verifies, reads cases, writes the memo.

*Pharos supplies numbers. Bob supplies judgement. Neither pretends to be the other.*

---

## 5 · It finds real disasters in real data

`python -m pharos scan rofecoxib --alias vioxx` — **live** against 20.7M reports:

| Reaction | n | PRR [95% CI] | χ² |
|---|---|---|---|
| Coronary artery disease | 4,156 | 72.2 [70.0–74.5] | 251,805 |
| **Myocardial infarction** | **17,981** | **52.2 [51.5–52.8]** | 815,462 |
| Cerebrovascular accident | 13,370 | 39.1 [38.5–39.7] | 459,992 |

Cardiac SOC cluster: **8 signals, 35,521 cases.** Same result for Avandia, Baycol, Bextra, Meridia, Darvon.

*Honest framing: openFDA starts 2004, Vioxx withdrew Sept 2004, and litigation inflated these counts. This proves the method works on real data — nothing more. The next slide is the real claim.*

---

## 5b · The Avandia timeline — when could we have known, and what hid it?

`pharos timeline rosiglitazone "myocardial infarction" --alias avandia -x rofecoxib -x vioxx --to 2013`

| Year | Avandia MI share | FAERS MI background | **Vioxx share of ALL MI reports** | Standard PRR | Vioxx-excluded PRR |
|---|---|---|---|---|---|
| 2005 | 3.3% | 4.5% | **68%** | 0.73 | **2.13** |
| 2006 | 3.8% | 5.5% | **72%** ⚠ | 0.68 | **2.27** ● |
| 2007 | 5.7% | 2.5% | 15% | 2.26 | 2.66 |

- **Standard screen first flags: 2008** — *after* the Nissen meta-analysis (May 2007) and FDA's boxed warning (Nov 2007).
- **Pharos masking check:** Vioxx litigation reports were ~70% of every MI report in FAERS — the background Avandia was compared against was inflated 5×.
- **Vioxx-excluded screen first flags: 2006** — one year *before* Nissen. **Detection moved forward two years.**

Also from the timeline, same method, real receive dates: **Meridia × stroke flagged 2004** (n=16, PRR 5.0) — regulators acted 2009–10. **Darvon × cardiac arrest flagged 2005** (PRR 3.0) — EMA acted 2009, FDA 2010.

*We expected Avandia to be obvious in 2005. It wasn't — and the tool told us why. Masking is in the literature (Maignen 2014); nobody puts it in the workflow. Pharos detects it every year and corrects it on request. That's the innovation: not a better number, a better question — "what hid this?"*

---

## 6 · Demo — dashboard & CLI

Screenshots: Tab 1 (PRR chart with CIs + organ-system chart) · 2×2 drill-down · Tab 2 (module bars, ranked gaps, "4.2.3 collapsed parent" warning).

- 36 unit tests, hand-computed reference values, all offline.
- On-disk cache + `PHAROS_OFFLINE=1` → demo survives no Wi-Fi.

---

## 7 · Architecture

```
User ──chat──▶ IBM Bob ──MCP/stdio──▶ Pharos MCP server (6 tools, 2 prompts)
User ──browser──▶ Streamlit ─────────▶ pharos engine ──▶ signals/ (PRR·ROR·χ²·SOC)
User ──terminal──▶ CLI ──────────────▶               ──▶ ctd/ (ICH M4 checker)
                                        signals/ ──▶ openFDA client (cache·offline) ──▶ FAERS 20.7M
                                        ctd/ ──────▶ ich_m4_ctd.yaml (69 sections)
```

*This is the template's own reference architecture — user → Bob → MCP → your server → data.*

---

## 8 · IBM Bob — where and how (load-bearing)

**Built with Bob:** Plan mode for the evidence/reasoning split · Agent mode to implement · `/review` on stats before tests · subagent for openFDA research.

**Runs with Bob:** `scan_signals` → `compute_prr` (verify) → `search_reports` (ground) → `cluster_by_organ_system` → `signal_emergence_timeline` (date it; spot masking; re-run corrected) → **memo**.

Server instructions: *always state n, PRR+CI, χ²; name reporting biases; never claim causation.*

> Remove Bob → no explanation, no conversation. Remove Pharos → Bob is guessing.

---

## 9 · Impact — what this becomes

- **Today:** a triage tool a safety scientist can talk to; a dossier auditor a regulatory team can run daily.
- **Next:** raw quarterly FAERS + EudraVigilance loaders · Bayesian shrinkage (EBGM/BCPNN) beside PRR · licensed MedDRA hierarchy · time-sliced signals ("when did this emerge?") · CTD content checks, not just structure.
- **Who it serves:** small pharma, academic PV groups, regulators in low-resource settings — everyone priced out of commercial platforms.

*Every drug safety disaster of the last 30 years was visible in the data first. The bottleneck was never data. It was attention. Pharos gives attention back.*

---

## 10 · Close

**Pharos** — *a lighthouse for drug safety*
github.com/Jainishcodee/bob-ai-hackathon-Sudo-Salingers
Team Sudo Salingers · thank you

---

### Production notes

- One idea per slide; slide 5b is the money shot — make "2008 → 2006" and "72%" huge. Use the dashboard's timeline chart (red standard line, green corrected line, blue milestone markers) as the visual.
- Use the dashboard screenshots from `demo/screenshots/` on slides 6 and 8.
- Export: PowerPoint/Keynote/Google Slides → PDF → `presentation/slides.pdf`.
