# 🔦 Pharos — Drug Safety Signal Detector & Regulatory Submission Readiness Checker

> *A lighthouse for drug safety.* Standard pharmacovigilance statistics over **20.7 million real FDA adverse-event reports**, an **ICH M4 CTD** dossier audit, and **IBM Bob** as the analyst who reads the evidence and writes the memo.

**Problem statement:** P2 — *Drug Safety Signal Detector & Regulatory Submission Readiness Checker* (Pharma & Biotech, Industry Problem Statements 2026).

---

## 👥 Team

| Field | Value |
|---|---|
| **Team Name** | Sudo Salingers |
| **Track** | AI |
| **Team Lead** | Jainish — d24ce180@charusat.edu.in  |
| **Members** | Bhavya Radiya — d24ce168@charusat.edu.in · Vandan Shah — 24BCA229@charusat.edu.in · Jinam Shah — D26DCE140@charusat.edu.in |

---

## 🎯 Problem Statement

FDA's FAERS database holds **20M+ adverse-event reports** and grows by over a million a year. No pharmacovigilance team can read them, so the first statistical evidence that a drug is hurting people sits undetected — Vioxx's cardiovascular signal was in the data while **27,000+ heart attacks** occurred. Separately, regulatory affairs teams assemble **100,000-page approval dossiers** by hand against the rigid five-module ICH M4 CTD structure, where one missing section means a refuse-to-file costing **6–12 months and $50–100M**. Both are the same problem: far too much structured data for manual review. → [docs/problem-statement.md](docs/problem-statement.md)

---

## 💡 Solution

Pharos is a two-mode evidence engine with IBM Bob as its reasoning layer.

**Mode 1 — Signal Detection.** For any drug, Pharos queries openFDA live, builds the 2×2 contingency table for every reaction reported with it, and computes the statistics regulators actually use — **PRR, ROR with 95% CI, Yates chi-square, Evans (2001) criteria** — then ranks clinical signals, filters administrative noise, and clusters them by organ system. Run it on Vioxx and myocardial infarction comes back at **n = 17,981, PRR 52**.

**Mode 2 — Submission Readiness.** Pharos encodes ICH M4 CTD Modules 1–5 as a **69-section machine-readable checklist** with required flags and criticality weights, matches a dossier outline against it, scores each module, and emits a ranked gap report (critical / major / minor, each with *why it matters*).

**IBM Bob** connects through the **Pharos MCP server** (7 tools, 2 prompt templates). Bob calls the tools, verifies each signal with an exact query, pulls real case reports, and writes the signal-assessment memo or the dossier remediation plan. Pharos supplies numbers; Bob supplies judgement. → [docs/solution-overview.md](docs/solution-overview.md)

---

## ✨ Key Features

- **Live disproportionality analysis on real data:** PRR, ROR (95% CI), chi-square (Yates), Evans 2001 signal criteria, Haldane zero-cell correction — unit-tested against hand-computed reference values. `src/pharos/signals/stats.py`
- **Signal emergence timeline with masking detection and correction** — the part we'd defend hardest. Rebuilds the 2×2 table year by year (FDA receive date) to show *when* a signal first met the criteria versus the real regulatory milestones. It also lists which drug dominated the reaction's reports each year — and that exposes **masking**: Vioxx litigation reports were **68–72% of all myocardial-infarction reports in FAERS in 2005–06**, inflating the background every other drug was compared against. Standard PRR flags Avandia × MI in **2008**, a year *after* the Nissen meta-analysis; exclude Vioxx from the comparator and Pharos flags it in **2006, a year *before*** — detection brought forward two years, on real data, by a literature-standard correction (Maignen et al.). Same method, unmasked: Meridia × stroke flagged 2004 (regulators acted 2009–10), Darvon × cardiac arrest flagged 2005 (acted 2009–10). `src/pharos/signals/timeline.py`
- **Retrospective validation on real withdrawals:** the demo set (Vioxx, Bextra, Avandia, Baycol, Meridia, Darvon + two controls) reproduces each drug's known safety signal from FAERS. `src/data/samples/demo_drugs.txt`
- **ICH M4 CTD readiness checker:** weighted per-module completeness, ranked gaps with regulatory rationale, detection of collapsed parent sections ("4.2.3 Toxicology" listed instead of its seven sub-sections) and non-CTD entries; blank-outline generator for regulatory teams. `src/pharos/ctd/`
- **IBM Bob MCP server (7 tools):** `scan_signals`, `compute_prr`, `cluster_signals_by_organ_system`, `search_reports`, `signal_emergence_timeline`, `check_ctd_dossier`, `get_ctd_spec`, plus `signal_assessment` and `dossier_gap_memo` prompt templates. Bob can now say *"novel cardiac signal, first detectable in 2006, masked until 2008 by Vioxx reporting."* `src/mcp_server/server.py`
- **Two front ends + resilience:** Streamlit dashboard and Typer CLI; administrative-term filter; curated MedDRA SOC clustering; on-disk openFDA cache with `PHAROS_OFFLINE=1` so the demo survives a dead network.

---

## 🛠️ Tech Stack

| Category | Technologies |
|---|---|
| **Languages** | Python 3.10+ |
| **Frameworks** | Streamlit, Typer + Rich, Plotly, pandas, httpx, pytest |
| **IBM Technologies** | IBM Bob — development (Plan / Agent modes, `/review`) **and** runtime (Bob ↔ Pharos over MCP) |
| **Databases** | openFDA FAERS API (FDA Adverse Event Reporting System, 20.7M reports); JSON disk cache |
| **Other** | Model Context Protocol (FastMCP), ICH M4 CTD checklist in YAML, GitHub Actions validator |

---

## 📁 Repository Structure

```
├── src/                          # All source code  → src/README.md for the layout
│   ├── pharos/                   #   engine: faers/ · signals/ · ctd/ · cli.py
│   ├── mcp_server/server.py      #   IBM Bob MCP server
│   ├── app/streamlit_app.py      #   dashboard
│   ├── data/samples/             #   demo drugs, sample dossier outlines
│   └── tests/                    #   50 offline unit tests
├── docs/
│   ├── problem-statement.md
│   ├── solution-overview.md
│   ├── architecture.md
│   ├── setup-guide.md
│   └── bob-integration.md        # registering the MCP server in Bob + example prompts
├── demo/                         # video link, screenshots
├── presentation/                 # slide deck
├── PROBLEM-STATEMENTS-ANALYSIS.md  # our decode of all 10 problem statements and why we chose P2
└── submission.yaml
```

---

## ⚡ How to Run

> Full guide with troubleshooting: [`docs/setup-guide.md`](docs/setup-guide.md). Requires Python 3.10+ and internet (or the bundled cache).

```bash
# 1. Clone the repo
git clone https://github.com/Jainishcodee/bob-ai-hackathon-Sudo-Salingers.git
cd bob-ai-hackathon-Sudo-Salingers/src

# 2. Install dependencies
python -m venv .venv
.venv\Scripts\activate            # Windows      (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
pip install -e . --no-build-isolation

# 3. Configure environment (optional — runs with no config)
copy .env.example .env            # macOS/Linux: cp .env.example .env

# 4. Run the project
python -m pharos scan rofecoxib --alias vioxx                     # Mode 1: the Vioxx signal, live
python -m pharos timeline rosiglitazone "myocardial infarction" --alias avandia -x rofecoxib -x vioxx --to 2013
                                                                  #         when Avandia's signal emerged, and what masked it
python -m pharos ctd-check data/samples/dossier_incomplete.yaml   # Mode 2: gap report
streamlit run app/streamlit_app.py                                # dashboard → http://localhost:8501
python -m mcp_server.server                                       # MCP server for IBM Bob (stdio)
python -m pytest tests -q                                         # 50 tests, offline
```

---

## 🖥️ Demo

| Artifact | Link |
|---|---|
| 📹 Demo Video | [See demo/demo-video-link.txt](demo/demo-video-link.txt) |
| 🌐 Live Demo | [See demo/live-demo-url.txt](demo/live-demo-url.txt) |
| 🖼️ Screenshots | [See demo/screenshots/](demo/screenshots/) |
| 📊 Presentation | [See presentation/](presentation/) |

---

## ⚠️ Known Limitations

- **Vioxx is retrospective; Avandia is the honest prospective claim.** openFDA data begins in 2004 and Vioxx was withdrawn that September, so the Vioxx scan shows the method works on real data — nothing more. The Avandia timeline is different: it uses only reports the FDA had received by 31 December of each year, so "flagged in 2006" is a genuine statement about what was knowable then. Two caveats we make ourselves: the masking drug (Vioxx) was chosen by inspection of Pharos's own masking report, not by an automated rule; and the *standard* screen flagged Avandia only in 2008 — Pharos's contribution is making the masking visible and correctable, not a claim that naive PRR beats regulators.
- **Reporting biases are real.** Vioxx's FAERS counts are inflated by litigation-driven reporting (notoriety bias) — the same wave that masked Avandia. Bob is instructed to name such biases in every memo.
- **Association, not causation.** PRR/ROR measure disproportionality of *reporting*. Pharos is a triage tool; the MCP server instructions forbid causal language.
- **MedDRA is licensed.** Organ-system clustering uses a curated ~300-term map plus keyword heuristics, labelled `heuristic` in every output.
- **Mode 2 is structural.** It checks that required CTD sections exist and their status, not the scientific adequacy of their contents. Module 1 (regional) is simplified to the main US and EU items.
- **Keyless openFDA limits.** 500-term cap on count queries and 1,000 requests/day per IP; a free API key lifts both. The committed cache makes the demo drugs work regardless.
- **Bob output varies by model.** The narrative is Bob's; the numbers are ours and deterministic.

---

## 🏅 What We're Most Proud Of

**The Avandia timeline** ([`src/pharos/signals/timeline.py`](src/pharos/signals/timeline.py)). Run
`python -m pharos timeline rosiglitazone "myocardial infarction" --alias avandia -x rofecoxib -x vioxx --to 2013` and Pharos rebuilds the 2×2 table for every year from real FDA data, shows the standard screen flagging Avandia's heart-attack signal only in **2008** — after the FDA had already acted — then shows *why*: Vioxx litigation reports were 68–72% of every MI report in FAERS in 2005–06. Remove them and the signal is there in **2006**, a year before the Nissen meta-analysis. We did not expect this result when we started; the data corrected our first assumption, and the tool now makes that correction visible for any drug. That is what a pharmacovigilance tool should do.

**The evidence/judgement split** ([`src/mcp_server/server.py`](src/mcp_server/server.py)). Pharos computes; IBM Bob interprets. Tool descriptions and server instructions make Bob behave like a careful safety scientist — confirm each signal with an exact query, read real cases, establish when it emerged, state the numbers, name the biases, never claim causation. Every statistic is the one in the pharmacovigilance literature and each is unit-tested against a hand-computed table ([`src/tests/test_stats.py`](src/tests/test_stats.py)).

---

*Built for the IBM Bob AI Innovation Hackathon 2026 · Round 1 · 15 September 2026.*
