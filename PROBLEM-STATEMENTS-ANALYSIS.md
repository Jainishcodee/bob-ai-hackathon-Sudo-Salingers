# IBM Bob Hackathon 2026 — Problem Statements, Decoded

**What this document is:** a plain-English breakdown of all 10 official problem statements. For each one: what they're actually asking you to build, what the jargon means, who the human at the other end is, and — in ordinary words — what problem it takes off that person's plate.

**Who it's for:** the team. Technical people, not domain experts in defense, semiconductors, pharma, power grids or shipping. Every acronym is expanded the first time it appears.

**A note on sourcing.** The problem descriptions, the money figures, and the "Your Challenge" asks all come from the official *Industry Problem Statements 2026* PDF. The **jargon decoding, end-user personas, plain-English translations, dataset suggestions, difficulty ratings and recommendations are our own analysis** — they are not from the organisers. Treat them as a starting point for discussion, not gospel.

---

## Table of Contents

1. [TL;DR — the 60-second version](#1-tldr--the-60-second-version)
2. [How to read each breakdown](#2-how-to-read-each-breakdown)
3. [All 10 at a glance](#3-all-10-at-a-glance)
4. [The breakdowns](#4-the-breakdowns)
   - [D1 — Mission Readiness & Predictive Maintenance Copilot](#d1--mission-readiness--predictive-maintenance-copilot)
   - [D2 — Threat Intelligence Correlation & Alert Prioritisation Assistant](#d2--threat-intelligence-correlation--alert-prioritisation-assistant)
   - [S1 — Wafer Yield Root Cause & Defect Pattern Analyser](#s1--wafer-yield-root-cause--defect-pattern-analyser)
   - [S2 — Fab Bottleneck & Supply Chain Risk Advisor](#s2--fab-bottleneck--supply-chain-risk-advisor)
   - [P1 — Clinical Trial Risk Monitor & Protocol Deviation Detector](#p1--clinical-trial-risk-monitor--protocol-deviation-detector)
   - [P2 — Drug Safety Signal Detector & Regulatory Submission Readiness Checker](#p2--drug-safety-signal-detector--regulatory-submission-readiness-checker)
   - [U1 — Power Outage Prediction & Grid Equipment Failure Advisor](#u1--power-outage-prediction--grid-equipment-failure-advisor)
   - [U2 — Grid Load Optimisation & Renewable Energy Performance Advisor](#u2--grid-load-optimisation--renewable-energy-performance-advisor)
   - [L1 — Container Congestion Predictor & Port Operations Optimiser](#l1--container-congestion-predictor--port-operations-optimiser)
   - [L2 — Supply Chain Disruption Assistant & Fleet Utilisation Optimizer](#l2--supply-chain-disruption-assistant--fleet-utilisation-optimizer)
5. [The pattern hiding in all ten](#5-the-pattern-hiding-in-all-ten)
6. [What "IBM Bob integration" actually means](#6-what-ibm-bob-integration-actually-means)
7. [Shortlist and recommendation](#7-shortlist-and-recommendation)
8. [Bringing your own problem statement](#8-bringing-your-own-problem-statement)

---

## 1. TL;DR — the 60-second version

- **All 10 problems are the same machine underneath.** Take messy data from several incompatible sources → find the things that matter → rank them by how bad they are → explain each one in words a human can act on → hand over a prioritised to-do list. The domain changes; the engineering barely does. **Pick the domain you find interesting, not the one you think is easiest — they're all about equally hard.**
- **The single biggest accelerator is whether real public data exists.** Three problems have genuinely excellent free public datasets: **P2** (FDA's adverse-event database), **D2** (the MITRE ATT&CK attacker catalogue), **S1** (811,000 real semiconductor wafer defect images). Two more have great free live APIs: **U1** and **U2** (weather and grid data). The rest need you to invent your data, which costs you a day and costs you credibility.
- **The scoring trap:** "Innovation & Differentiation" is worth 25 of 100 points. A generic "here's a ranked list of risky things" app is exactly what every team will build. Each breakdown below names the specific hook that makes that problem *not* generic.
- **The other scoring trap:** "IBM Bob Integration" is 10 points and the rubric explicitly says Bob must be *load-bearing, not name-dropped*. See [section 6](#6-what-ibm-bob-integration-actually-means) — this is the most commonly misunderstood requirement and the fix is straightforward.
- **Our shortlist:** **P2**, **D2**, **U1**. Reasoning in [section 7](#7-shortlist-and-recommendation).

---

## 2. How to read each breakdown

Every problem below is broken into the same seven parts:

| Field | What it tells you |
|---|---|
| **The ask, in one line** | The official challenge, compressed. |
| **Jargon decoded** | Every acronym and industry term in that problem, in plain words. |
| **What you'd actually build** | The challenge split into its separate features — because each one is a separate thing you have to demo. |
| **Who's actually using it** | The real human role sitting in front of the screen. |
| **In plain English** | What changes about that person's working day. No jargon, no numbers. **This is the heart of it.** |
| **Why it matters now** | The money and risk, quoted from the official PDF. |
| **Hackathon reality check** | What data you'd need, what the core algorithm is, where Bob genuinely earns its place, and how hard it really is. |

---

## 3. All 10 at a glance

| ID | Problem | Sector | The person it helps | Real public data? | Build difficulty | Demo impact |
|---|---|---|---|---|---|---|
| **D1** | Mission Readiness & Predictive Maintenance | Defense | Squadron maintenance officer | 🟢 Good — NASA engine degradation sets | 🟡 Medium | 🟢 High |
| **D2** | Threat Intel Correlation & Alert Prioritisation | Defense | Security operations analyst | 🟢 **Excellent** — MITRE ATT&CK is free | 🟡 Medium | 🟢 High |
| **S1** | Wafer Yield Root Cause & Defect Patterns | Semiconductor | Fab process/yield engineer | 🟢 **Excellent** — WM-811K wafer maps | 🟠 Med-High (ML) | 🟢 High — very visual |
| **S2** | Fab Bottleneck & Supply Chain Risk | Semiconductor | Ops planner + risk manager | 🔴 Poor — mostly invented | 🔴 High | 🟡 Medium |
| **P1** | Clinical Trial Risk & Protocol Deviations | Pharma | Clinical trial risk manager | 🟡 Synthetic (Synthea helps) | 🟢 Med-Low | 🟡 Medium |
| **P2** | Drug Safety Signals & Submission Readiness | Pharma | Drug safety scientist + regulatory lead | 🟢 **Excellent** — FDA FAERS, 20M reports | 🟡 Medium | 🟢 **Very high** |
| **U1** | Outage Prediction & Grid Equipment Failure | Utilities | Utility asset & storm-response manager | 🟢 **Excellent** — free weather + outage APIs | 🟡 Medium | 🟢 **Very high** — map |
| **U2** | Grid Load & Renewable Performance | Utilities | Grid control-room operator | 🟢 Excellent — EIA, NREL free APIs | 🟠 Med-High | 🟢 High |
| **L1** | Port Congestion & Operations Optimiser | Logistics | Port shift supervisor | 🟡 Fair — partial vessel data | 🟠 Med-High (optimisation) | 🟢 High — Gantt view |
| **L2** | Supply Chain Disruption & Fleet Utilisation | Logistics | Logistics control-tower coordinator | 🟡 Synthetic, but easy to fake well | 🟢 Med-Low | 🟢 High |

> **Reading the columns.** *Real public data* is the difference between spending Saturday building and spending Saturday inventing CSV files — and judges can tell. *Demo impact* is how convincing a 3-minute video will look, which matters because "Working Demo & Functionality" is worth 15 points and the guide explicitly says actual output beats mocked output.

---

## 4. The breakdowns

---

### D1 — Mission Readiness & Predictive Maintenance Copilot

> 🔴 **Critical Now** · Defense & Aerospace

**The ask, in one line**
Read sensor data and service records from military aircraft, vehicles and equipment; say which ones can't go on the next mission and why; predict which parts will break before the mission happens; and tell the crew what to fix first.

**Jargon decoded**

| Term | What it means |
|---|---|
| **HUMS** | Health & Usage Monitoring System — the sensor package bolted onto military aircraft and vehicles. It continuously records vibration, engine temperature, rotor torque, flight hours, stress loads. Think of a car's diagnostic port, but far richer — and, per the problem statement, mostly recorded and then never looked at. |
| **Mission-ready** | Can this aircraft actually fly the job tomorrow. The military grades it: Fully Mission Capable, Partially Mission Capable, Not Mission Capable. |
| **Mission window** | The time slot the operation has to happen in. This is the deadline everything is measured against. |
| **Calendar-based maintenance** | Servicing something every 6 months or every 100 flight hours regardless of what condition it's actually in. Throws away good parts early; misses bad parts that fail "in date". |
| **Platform** | Military-speak for the vehicle itself — the helicopter, the tank, the ship. |

**What you'd actually build** — four distinct features:
1. Ingest two very different data types: continuous sensor streams *and* free-text service/maintenance records.
2. Classify which assets are not mission-ready right now.
3. **Explain** each readiness issue — not a red flag, an actual reason a human can act on.
4. Predict which components will fail before the next mission window (a deadline-relative prediction, not a generic lifespan estimate).
5. Produce a prioritised maintenance plan — given you only have three mechanics and two spare gearboxes, what order do you do things in?

**Who's actually using it**
A squadron maintenance officer or fleet readiness manager. Indirectly, the commander who asks them "how many aircraft can I put in the air on Thursday?"

**In plain English**
A commander asks how many helicopters can fly on Thursday. Right now, answering that means someone spending hours on the phone and in spreadsheets, and the answer is still partly a guess. Parts are replaced on a fixed schedule — some are binned while they still had years left, others fail unexpectedly while still technically "in date". When something breaks without warning, the unit can't do its job and getting back to normal takes weeks.

This tool answers the Thursday question instantly. For every aircraft that can't fly, it says *why* in words, not codes. It warns which aircraft look fine today but won't make it to Thursday. And because the crew can only do a few jobs before then, it says which jobs to do, in what order, to get the most aircraft flying.

**Why it matters now**
The US military spends **$90 billion a year** on maintenance. Moving from fixed schedules to condition-based prediction saves billions. When platforms fail unexpectedly, readiness drops and recovery takes weeks.

**Hackathon reality check**

- **Data:** NASA's C-MAPSS turbofan engine degradation datasets are public and are a near-perfect stand-in — genuine run-to-failure sensor traces from jet engines. NASA's bearing and battery datasets work similarly. Service records you'd synthesize.
- **Core algorithm:** Remaining-useful-life estimation. You don't need deep learning — sensor drift against a healthy baseline, plus trend extrapolation to the mission date, is defensible and explainable. Prioritisation is constrained ranking (impact ÷ effort).
- **Where Bob genuinely earns its place:** Steps 3 and 5. "Explain each readiness issue" and "recommend a prioritised plan" are natural-language reasoning over structured evidence — exactly what an LLM agent is for. The prediction itself is ordinary maths.
- **The hook that stops it being generic:** Most predictive-maintenance demos predict failure in the abstract. This one predicts **against a specific deadline**. "Will this survive until Thursday 0600?" is a much better question than "how long will this last?", and it's what makes the output actionable.
- **Difficulty:** 🟡 Medium. The trap is teams overreaching on the ML and running out of time for the explanation and planning layers — which are the parts that actually score.

---

### D2 — Threat Intelligence Correlation & Alert Prioritisation Assistant

> 🔴 **Critical Now** · Defense & Aerospace

**The ask, in one line**
Take thousands of security alerts a day arriving in a dozen incompatible formats, work out which handful are a real attack, label what the attacker is doing using the industry's standard vocabulary, and write the commander a half-page brief that starts with the answer.

**Jargon decoded**

| Term | What it means |
|---|---|
| **SIEM** | Security Information and Event Management — the central console that collects security logs and raises alerts. Splunk, Microsoft Sentinel, and **IBM's own QRadar**. This is where the firehose comes from. |
| **BLUF** | Bottom Line Up Front — a military writing format. The conclusion and the recommendation go in the **first sentence**; the evidence comes after. The opposite of how a report is normally written. A commander should be able to read one line and decide. |
| **MITRE ATT&CK** | A free, public, industry-standard catalogue of roughly 200 things attackers do, each with an ID — T1566 is Phishing, T1078 is Valid Accounts — grouped into stages like Initial Access, Persistence, Exfiltration. It's the shared vocabulary that lets everyone describe an attack the same way. |
| **False positive** | An alert that looked like an attack and wasn't. The overwhelming majority of them. |
| **Correlation** | Realising that five separate, individually boring alerts are actually one attack in progress. |
| **Triage** | Deciding which alerts are worth a human's time. |

**What you'd actually build** — four distinct features:
1. Ingest feeds from multiple sources in different formats, and normalise them into one shape.
2. Correlate — group related alerts into single incidents, and separate genuine threats from false positives.
3. Map what's happening to MITRE ATT&CK technique IDs.
4. Generate prioritised BLUF summaries for commanders.

**Who's actually using it**
A security operations centre analyst, who starts their shift facing a queue they cannot possibly clear. And then the commander, who reads the output and decides what to do.

**In plain English**
An analyst arrives at work to four thousand alerts and has time to properly examine maybe forty. Almost all of them are noise. The genuine attack is usually not one alarming alert — it's five dull ones that are only frightening when you see them side by side: a failed login here, a new admin account there, an odd outbound connection at three in the morning. Nobody has time to see them side by side.

This tool does the seeing-them-side-by-side part. It throws out the noise, groups the related events into a single story, labels what the attacker is doing using the naming everyone in the industry already agrees on, and gives the commander half a page that opens with what's happening and what to do about it — rather than making them read to the bottom to find out.

**Why it matters now**
Missing one genuine threat is catastrophic. Chasing false positives burns analyst time that is already the scarcest resource in the building. Commanders need the picture in minutes, not hours.

**Hackathon reality check**

- **Data:** 🟢 **MITRE ATT&CK is completely free and machine-readable** — the full catalogue is published as STIX 2.1 JSON on GitHub, with a maintained Python library. That's your entire technique taxonomy, for free, in an afternoon. Alert feeds you'd synthesize, or draw from public security datasets and Sigma detection rules.
- **Core algorithm:** Normalise to a common event schema → build an entity graph (same host, same IP, same user account, within a time window) → cluster connected alerts into incidents → score by severity and confidence. ATT&CK mapping can be done by semantic similarity or a keyword-to-technique lookup.
- **Where Bob genuinely earns its place:** 🟢 **The best fit of all ten.** "Write a structured brief from a pile of evidence" is precisely what an LLM agent does well. The correlation reasoning — *why* these five alerts are one story — is also natural agent work.
- **The hook that stops it being generic:** The BLUF format and the ATT&CK mapping. Both are real, specific, checkable standards. A judge can verify you mapped T1566 correctly. That's much harder to hand-wave than "we ranked things by risk."
- **Difficulty:** 🟡 Medium — and the best ratio of *impressiveness per hour spent* on this list.

---

### S1 — Wafer Yield Root Cause & Defect Pattern Analyser

> 🔴 **Critical Now** · Semiconductor

**The ask, in one line**
When a chip factory starts producing more duds than it should, find out why — from the visual pattern of the failures and the machine data — rank the likely causes, say what to do, and warn about upcoming batches heading the same way.

**Jargon decoded**

| Term | What it means |
|---|---|
| **Wafer** | The shiny 300mm silicon disc that hundreds of individual chips are cut from. |
| **Die** | One individual chip on the wafer, before it's cut out. |
| **Yield** | The percentage of chips on a wafer that actually work. This is the number that decides whether a fab makes money. |
| **3nm / 5nm node** | The manufacturing generation. Smaller numbers mean denser, faster chips — and a far more fragile, less forgiving process. |
| **Lot / batch** | A group of roughly 25 wafers that travel through the factory together. |
| **Wafer map** | A picture of which chips on the disc failed. Crucially, **the shape of the failure pattern is a fingerprint**: a scratch means a handling problem, a ring means a spin-coating problem, edge failures mean something else again. |
| **Process parameters** | Temperature, pressure, gas flow, exposure time — the settings at each of the hundreds of manufacturing steps. |
| **Root cause** | Which specific machine, step, or setting caused the failure. |

**What you'd actually build** — four distinct features:
1. Analyse wafer lot data and defect reports to identify failure patterns.
2. Rank possible root causes by probability.
3. Recommend corrective actions for each.
4. **Look forward** — flag upcoming batches whose settings match ones that historically produced bad yield, before those batches run.

**Who's actually using it**
A process engineer or yield engineer in the fab, whose job is literally "find out why the numbers dropped."

**In plain English**
A chip factory quietly starts producing more failures than usual. Somewhere among thousands of sensors across hundreds of machines is the reason. Engineers currently hunt for it manually for weeks, and every week of hunting costs millions in lost product.

The useful thing is that failures leave a visual fingerprint on the silicon disc. A scratch pattern means one thing; a ring means another; failures clustered at the edge mean a third. An experienced engineer reads those shapes — but there are thousands of discs and only so many engineers.

This tool reads the fingerprints automatically, cross-references them against what the machines were doing, and gives a ranked shortlist of likely culprits with a confidence level and a suggested fix for each. Then it does the thing nobody currently does at all: it looks at the batches queued up to run tomorrow and says *"batch 4471 is set up almost identically to the batch that went wrong last month — stop it before you waste the silicon."*

**Why it matters now**
At the leading edge, a **1% yield drop costs tens of millions of dollars a month**. Every day spent finding the cause is revenue gone.

**Hackathon reality check**

- **Data:** 🟢 **WM-811K is a gift.** It's a real, free, public dataset of **811,457 actual wafer maps** from a real fab, with 8 labelled defect patterns (Center, Donut, Edge-Local, Edge-Ring, Local, Random, Scratch, Near-Full). Available on Kaggle. Process parameter data you'd synthesize alongside it.
- **Core algorithm:** Image classification on the wafer maps — a small CNN, or even classical shape features, gets respectable accuracy. Then association between parameter ranges and low yield for root-cause ranking, and a similarity score for the forward-looking batch flagging.
- **Where Bob genuinely earns its place:** The root-cause narrative and corrective-action recommendations. ⚠️ **Be careful here** — the headline feature (pattern classification) is machine learning, not LLM work. If you don't deliberately design Bob into the reasoning and advisory layer, you risk scoring poorly on the 10-point Bob Integration criterion.
- **The hook that stops it being generic:** The forward-looking part. Everyone builds the "what went wrong" analyser. Almost nobody builds the "this batch is about to go wrong, don't run it" part — and the problem statement explicitly asks for it ("before they run, not after they fail").
- **Difficulty:** 🟠 Medium-High because of the ML component — but the free real dataset buys back most of that.

---

### S2 — Fab Bottleneck & Supply Chain Risk Advisor

> 🔴 **Critical Now** · Semiconductor

**The ask, in one line**
Find the machine inside the chip factory that's causing the traffic jam and work out which customer orders will be late because of it — and separately, map which raw materials you'd be stuck without because only one supplier in one country makes them.

**Jargon decoded**

| Term | What it means |
|---|---|
| **Fab** | Fabrication plant — the chip factory itself. |
| **WIP** | Work In Progress — the queue of wafer lots waiting at each machine. The queue lengths tell you where the jam is. |
| **Lithography** | The step that prints the circuit pattern onto the wafer using light. The machines are the famously scarce ones — a single EUV lithography machine costs upwards of $150 million and only one company on earth makes them. |
| **Etch** | Chemically carving away material to leave the pattern behind. |
| **CVD** | Chemical Vapour Deposition — growing an ultra-thin film of material onto the wafer from a gas. |
| **Bottleneck tool** | The machine with the longest queue. It sets the pace of the entire factory — the whole fab can only go as fast as this one machine. |
| **Lead time** | Order to delivery. For chips, currently **26–52 weeks**. |
| **Single-source supplier** | Only one company or country makes it. If they stop, you stop. |
| **Photoresist** | The light-sensitive coating that makes lithography work. Highly specialised, very few suppliers. |
| **Geopolitical concentration risk** | Too much of a critical input coming from one country. China controls 80%+ of gallium and germanium — both now under export controls. |

**What you'd actually build** — four distinct features:
1. Identify bottleneck tools from the queue data.
2. Predict downstream delivery impact — which orders slip, and by how much.
3. Evaluate the supply chain for single-point-of-failure suppliers.
4. Score geopolitical concentration risk.

**Who's actually using it**
Two different people, really: a fab operations planner (features 1–2) and a supply chain risk manager (features 3–4).

**In plain English**
There are two quite separate ways a chip factory gets into trouble, and this tool watches both.

*Inside the factory:* one machine quietly becomes the traffic jam. Because everything has to flow through it, a two-day hold-up there turns into a six-week delay for a customer — but nobody connects those two facts until the customer phones up angry. This tool watches the queues, names the jam, and immediately says which specific orders are going to be late as a result.

*Outside the factory:* some of the exotic chemicals and metals you need come from exactly one supplier, in exactly one country. Most companies discover this is a problem in the same week that country stops exporting. This tool maps your suppliers and says, in advance, "these four materials have no plan B, and here's how exposed you are."

**Why it matters now**
Chip lead times are **26 to 52 weeks**. The 2021 chip shortage halted car factories for months. China's control of gallium and germanium is now an active export-control issue, not a hypothetical.

**Hackathon reality check**

- **Data:** 🔴 **The weakest data situation of the ten.** No public fab WIP data exists — it's among the most commercially sensitive data there is, so you'd simulate it entirely. The supply-chain half is better: the USGS Mineral Commodity Summaries publish real, free, citable country-by-country production shares for gallium, germanium and the rest.
- **Core algorithm:** Bottleneck detection from utilisation and queue length; discrete-event simulation to propagate delay downstream to order dates; and the **Herfindahl-Hirschman Index** for supplier concentration — a real, standard, defensible economics metric that makes the risk half look serious rather than hand-waved.
- **Where Bob genuinely earns its place:** The advisory narrative and "what if" scenarios — *what happens to delivery dates if this tool goes down for three days?*
- **The hook that stops it being generic:** Putting internal operational risk and external geopolitical risk in one view. That combination is genuinely unusual and is the reason the problem statement says "simultaneously."
- **Difficulty:** 🔴 **High — the broadest scope on the list.** This is honestly two products, and the simulation piece is the kind of thing that eats a whole day. Not recommended for a short hackathon unless someone on the team already knows operations research.

---

### P1 — Clinical Trial Risk Monitor & Protocol Deviation Detector

> 🔴 **Critical Now** · Pharma & Biotech

**The ask, in one line**
Check thousands of patient records against the trial's rulebook, flag every breach, grade how serious each one is by the official standard, work out which hospitals are heading for trouble, and draft the formal paperwork to fix it.

**Jargon decoded**

| Term | What it means |
|---|---|
| **Protocol** | The trial's rulebook. Who can join, exactly what dose, exactly when each visit happens, which other medicines are forbidden during the trial. Legally binding, and extremely precise. |
| **Protocol deviation** | Anything that didn't follow the rulebook. A visit happened three days late; a dose was wrong; a patient took a banned medication. |
| **Site** | A hospital or clinic taking part in the trial. A big trial has 200+ of them, all supposed to be doing the identical thing. |
| **ICH E6 GCP** | International Council for Harmonisation, Guideline E6, *Good Clinical Practice* — the global rulebook for running a trial properly. It's where the official severity grades come from: **major** (could affect patient safety or the validity of the data), **minor**, **administrative**. |
| **CAPA** | Corrective And Preventive Action — the formal document you must produce saying what went wrong, what you did about it, and how you'll stop it happening again. Regulators ask to see these. |
| **Leading indicator** | A warning sign that shows up *before* the failure — rising data queries, slow record entry, high staff turnover at a site — as opposed to a lagging indicator, which is the failed audit itself. |
| **Co-medication** | Another drug a patient is taking alongside the trial drug. Some are banned because they'd confound the results or endanger the patient. |

**What you'd actually build** — four distinct features:
1. Compare patient records against the protocol specification to detect deviations.
2. Classify each deviation by ICH E6 severity: major, minor, or administrative.
3. Score each site's risk using leading indicators, before problems escalate.
4. Generate CAPA-ready reports with recommended mitigations.

**Who's actually using it**
A clinical trial risk manager, or a Clinical Research Associate responsible for monitoring dozens of hospitals they can only physically visit occasionally.

**In plain English**
A drug trial runs across two hundred hospitals and five thousand patient visits, and every hospital is supposed to follow exactly the same rulebook. In reality someone gives a dose a day late, a patient is quietly taking a medication they shouldn't be, a check-up gets missed. Individually each of these looks trivial. Collectively they can invalidate the entire trial.

Today, nobody notices until a regulator turns up two years later, finds the pattern, and rejects the submission — which means six to twelve months of delay and a nine-figure cost, for problems that were visible in the data all along.

This tool reads the patient records against the rulebook continuously. It flags every breach as it happens, grades how serious each one is using the official scale, and ranks which hospitals are drifting towards trouble *before* they get there — based on early warning signs rather than waiting for the failure. Then it drafts the formal corrective paperwork, which is otherwise a slow manual job.

**Why it matters now**
One rejected submission delays approval by **6–12 months and costs $50–100 million**. Deviations currently go undetected until the FDA audit — the worst possible moment to find out.

**Hackathon reality check**

- **Data:** 🟡 Synthetic, but that's fine here. Synthea is a free, well-known synthetic patient record generator. The ICH E6 guideline text is publicly available.
- **Core algorithm:** 🟢 **This is the cleanest engineering on the list.** Encode the protocol as a machine-readable rule file (YAML or JSON), then run patient records through a rules engine. It's deterministic, testable, and reliable — no ML uncertainty. Site risk is weighted scoring over leading indicators.
- **Where Bob genuinely earns its place:** Drafting CAPA reports is real document generation. So is severity classification *with a written justification* — the judgement of whether a deviation is "major" often needs reasoning about context, not a lookup table.
- **The hook that stops it being generic:** **Treating the protocol as a machine-readable specification.** That single design decision — turning a legal prose document into something executable — is a genuinely good idea, easy to explain to a judge, and reusable across trials. It's the strongest innovation story of the pharma pair.
- **Difficulty:** 🟢 **Medium-Low — the most tractable problem on this list.** Rules engines are fast to build and hard to get visibly wrong.

---

### P2 — Drug Safety Signal Detector & Regulatory Submission Readiness Checker

> 🔴 **Critical Now** · Pharma & Biotech

**The ask, in one line**
Two tools in one: (1) sift twenty million side-effect reports to spot, early, that a drug is hurting people; and (2) check a hundred-thousand-page drug application against the required structure so it isn't rejected for a missing section.

**Jargon decoded**

| Term | What it means |
|---|---|
| **FAERS** | FDA Adverse Event Reporting System — the US regulator's public database of every side-effect report ever submitted. **20 million+ reports. Free to download.** |
| **Adverse event** | Any bad thing that happened to a patient who was taking a drug. Not necessarily caused by it — that's the whole problem. |
| **Signal** | Statistical evidence that a drug is associated with a side effect more than it should be. The first hint that something's wrong. |
| **PRR** | Proportional Reporting Ratio. The standard formula for detecting a signal: *how often this side effect appears among reports for this drug*, divided by *how often it appears among reports for every other drug*. A PRR of 2 or more (with at least 3 cases) is the classic threshold for "look into this." It is genuinely a few lines of arithmetic over a 2×2 table. |
| **Vioxx** | A painkiller withdrawn in 2004 after being linked to 27,000+ heart attacks. The textbook case of a signal sitting in the data while people kept being harmed. |
| **CTD / ICH M4** | Common Technical Document — the mandatory five-part structure every drug approval application must follow. Module 1 is regional admin, 2 is summaries, 3 is manufacturing quality, 4 is animal studies, 5 is human trials. The required structure is public. |
| **Dossier** | The application itself. 100,000+ pages. |
| **Pharmacovigilance** | The formal discipline of monitoring drug safety after approval. |

**What you'd actually build** — the challenge explicitly asks for **two modes**:

*Mode 1 — Signal Detection:* cluster adverse event reports, calculate PRR statistics, flag emerging safety signals.

*Mode 2 — Submission Readiness:* check a dossier outline against the ICH M4 CTD requirements, score completeness per module, generate a gap report.

**Who's actually using it**
Mode 1 is for a drug safety / pharmacovigilance scientist. Mode 2 is for a regulatory affairs manager. ⚠️ Be aware these are **two different people doing two different jobs** — the problem statement bolts them together on the reasoning that both suffer from "too much complex data for manual review."

**In plain English**

*Mode 1:* Every side effect anyone reports about any drug goes into one enormous government database — twenty million reports and growing. Buried in that pile, usually months or years before anyone acts on it, is the first evidence that a drug is harming people. With Vioxx, the evidence was in the data while twenty-seven thousand people had heart attacks. Nobody is doing the arithmetic fast enough. This tool does it continuously and says: *"heart problems are being reported four times more often for this drug than you'd expect by chance — someone needs to look at this."*

*Mode 2:* Separately, getting a drug approved means submitting an application of a hundred thousand pages in a rigidly prescribed five-part structure. Leave out one required section and the whole thing bounces — another six to twelve months and another nine-figure cost, for a filing error. This tool checks your table of contents against the official required structure and tells you exactly what's missing, before you send it.

**Why it matters now**
FAERS holds 20M+ reports. Vioxx caused 27,000+ heart attacks before its signal was acted on. A dossier rejection costs **6–12 months and $50–100 million**.

**Hackathon reality check**

- **Data:** 🟢 **The best data situation of all ten problems.** FAERS is real, free, and downloadable in quarterly files directly from the FDA — and there's an official open API too. The ICH M4 CTD structure is public. You would be working with genuine regulatory data from hour one.
- **Core algorithm:** PRR is a 2×2 contingency table and some division — genuinely simple, and *genuinely the industry-standard method*, which means it's defensible rather than invented. Add a chi-square test for significance. Mode 2 is structural comparison against a checklist. *(One caveat: MedDRA, the formal medical terminology, is licensed — but the FAERS files already contain the preferred terms, which is normally enough.)*
- **Where Bob genuinely earns its place:** Writing up the signal narrative; generating the gap report; and in Mode 2, reasoning about whether a section *actually satisfies* a requirement rather than just existing — which is judgement, not string matching.
- **The hook that stops it being generic:** 🟢 **A killer demo.** Run your detector over historical FAERS data and show it flagging a drug that was genuinely withdrawn years later — Vioxx being the obvious candidate. That is "real output, not mocked" in the most persuasive form available to any team in this hackathon. It is very hard for a judge to be unimpressed by a tool that catches a real disaster in real data.
- **The risk:** The split personality. Two modes is two products. A strong entry probably builds Mode 1 deeply, Mode 2 competently, and says so honestly — the guide explicitly notes that honest `known_limitations` are respected and overclaiming is penalised.
- **Difficulty:** 🟡 Medium.

---

### U1 — Power Outage Prediction & Grid Equipment Failure Advisor

> 🔴 **Critical Now** · Utilities

**The ask, in one line**
Combine the health readings from grid equipment with the weather forecast and the history of past failures, to predict where the lights will go out — then rank by how many people are affected and tell the utility where to send the repair crews tonight.

**Jargon decoded**

| Term | What it means |
|---|---|
| **Transformer** | The kit that steps voltage up or down — the big grey drum on the pole or the fridge-sized unit in a substation. Expensive, slow to replace, and when one fails the lights go out for everyone downstream. |
| **Substation** | A junction in the grid where voltage is changed and power is routed. |
| **Partial discharge** | Tiny electrical sparking inside the insulation — an early, measurable sign that the insulation is breaking down. One of the most reliable advance warnings of transformer failure. |
| **Oil quality / dissolved gas analysis** | The insulating oil inside a transformer picks up specific gases as it degrades. Testing it is effectively a blood test for the transformer. |
| **Grid impact severity** | Not all equipment matters equally. One transformer feeding a hospital and 40,000 homes outranks one feeding a car park. |
| **Crew pre-positioning** | Parking the repair trucks near where you *expect* the damage, *before* the storm arrives — instead of dispatching them across the county afterwards. |
| **Calendar-based maintenance** | Servicing on a fixed schedule regardless of the equipment's actual condition. Still the industry norm. |

**What you'd actually build** — four distinct features:
1. Combine three separate data sources: asset health sensors, weather forecasts, and historical incidents.
2. Predict outage-prone areas and at-risk equipment.
3. Rank assets by grid impact severity — who gets hurt if this one fails.
4. Generate a prioritised maintenance plan *and* a crew pre-positioning plan.

**Who's actually using it**
A utility asset manager in normal times; a storm response coordinator when weather is coming.

**In plain English**
The equipment that keeps the lights on tells you it's dying weeks in advance. It runs hot, it vibrates oddly, its oil goes bad, it sparks internally. The sensors measuring all of this already exist and are already recording. Nobody is listening — the equipment gets serviced on a calendar instead.

Then a storm arrives, the weakest equipment in its path fails, and a million people lose power at over a million pounds an hour. The two pieces of information that would have predicted exactly this — the equipment health readings and the weather forecast — sit in two different systems and are never put together in time to act on.

This tool puts them together. Here is the equipment that's already unwell. Here is where the storm is going. Here is the overlap. Here is which of those matter most, because of who they serve. And here is where to park the repair trucks tonight so you're already in the right place when it happens.

**Why it matters now**
Transformer and substation failures cause blackouts costing **over $1 million an hour** and affecting millions of people. Most utilities still run calendar-based maintenance while the predictive signals go unread.

**Hackathon reality check**

- **Data:** 🟢 **Excellent, and genuinely live.** Open-Meteo gives real weather forecasts with no API key at all; NOAA's National Weather Service API is free. The US Department of Energy's EAGLE-I programme publishes historical county-level outage data. Only the equipment sensor readings need simulating — and those are easy to simulate believably (a slow upward temperature drift, rising partial discharge counts).
- **Core algorithm:** Risk = f(asset health score, weather exposure at that location, historical failure rate) × criticality weighting. It's a geospatial overlay problem more than a machine learning one, which is good news for a weekend build.
- **Where Bob genuinely earns its place:** The operator briefing, the per-asset explanation of *why this one*, and the crew deployment plan — all of which are reasoning-and-writing tasks over structured risk data.
- **The hook that stops it being generic:** The **fusion**. Everyone builds an asset health monitor. Almost nobody joins it to a live weather forecast geographically and weights it by how many customers are downstream. The problem statement calls this out precisely: the data exists, it's just "never combined in time to act."
- **Demo value:** 🟢 **The best visual demo of the ten.** A map, a storm track sweeping across it, and at-risk assets lighting up underneath it, with a ranked action list beside it. That sells itself in a three-minute video without narration.
- **Difficulty:** 🟡 Medium.

---

### U2 — Grid Load Optimisation & Renewable Energy Performance Advisor

> 🔴 **Critical Now** · Utilities

**The ask, in one line**
Forecast when electricity demand will spike, suggest how to balance it without switching off clean energy, spot solar and wind farms that are underperforming, work out why each one is, and put it all in one brief for the control room.

**Jargon decoded**

| Term | What it means |
|---|---|
| **Curtailment** | Deliberately switching off a perfectly working solar or wind farm because the grid can't absorb the electricity right now. Free, clean power thrown away. The US threw away about **8 TWh** this way in 2023 — roughly the annual consumption of a small country. |
| **Load** | Total electricity demand on the grid at this moment. |
| **Load spike** | A sudden jump in demand. A heatwave hits, everyone turns on air conditioning at once. |
| **Grid instability** | Supply and demand have to match second by second. If they drift apart, the grid frequency moves, and equipment starts tripping offline to protect itself. |
| **Underperforming asset** | A solar farm producing less than the amount of sunshine says it should. Could be dust on the panels, shading, a dead inverter, or simple ageing. |
| **Performance ratio** | Actual output ÷ the output you'd theoretically expect given the weather. The industry's standard "is this solar farm healthy?" metric. Necessary because raw output naturally varies with the weather, which hides faults. |
| **Inverter** | The box that converts a solar panel's DC output to grid AC. A common failure point, and when one dies a whole section quietly produces nothing. |

**What you'd actually build** — five distinct features (note: the most sub-features of any problem here):
1. Forecast demand spikes.
2. Recommend load-balancing actions.
3. Detect anomalies in renewable energy performance.
4. Identify the root cause for each underperforming asset.
5. Generate an integrated operator brief with a curtailment minimisation plan.

**Who's actually using it**
A grid control-room operator, making decisions on a timescale of minutes.

**In plain English**
Two frustrations happening at once, and nobody is solving them together.

First: on a bright, windy day the grid sometimes can't absorb all the clean electricity being generated, so working solar and wind farms get switched off. Enough was wasted this way in the US in a single year to power a small country. Second: demand sometimes jumps unexpectedly and the grid wobbles. Both are forecasting problems, and the control room currently handles them with very little decision support.

On top of that, some solar farms are just quietly underperforming — dusty panels, a failed inverter — and it can go unnoticed for months, because output goes up and down with the weather anyway so nobody can tell the difference between a cloudy week and a broken farm.

This tool forecasts the demand spike before it lands, suggests what to shift or store rather than switching generation off, spots the farm producing less than the sunshine justifies, says *why* that farm specifically is down, and gives the control room one brief covering all of it.

**Why it matters now**
~8 TWh of clean energy curtailed in the US in 2023. Unexpected demand spikes destabilise the grid. Operators have very limited real-time decision support today.

**Hackathon reality check**

- **Data:** 🟢 Excellent and free. The US Energy Information Administration's EIA-930 dataset gives hourly demand and generation by region through a free API. NREL's PVWatts and NSRDB APIs give expected solar output for any location — which is exactly what you need as the denominator of a performance ratio. CAISO publishes real curtailment data. Open-Meteo for weather.
- **Core algorithm:** Time-series forecasting for demand (and be careful — a badly done forecast is obvious to anyone who knows the domain). Anomaly detection by comparing actual output to weather-adjusted expected output. A heuristic or linear-programming optimiser for the curtailment minimisation plan.
- **Where Bob genuinely earns its place:** The integrated operator brief, and the per-asset root cause narrative — "this farm's output dropped 12% while its neighbour three miles away didn't, and the drop is gradual not sudden, which points at soiling rather than a fault."
- **The hook that stops it being generic:** Curtailment minimisation. It reframes the whole thing from "monitor the grid" to "stop throwing away free clean electricity," which is a much sharper and more memorable pitch — and it's quantifiable in megawatt-hours saved.
- **Difficulty:** 🟠 Medium-High. **Five deliverables in one challenge statement is a lot** for a hackathon, and the forecasting component is the kind of thing that looks bad if rushed.

---

### L1 — Container Congestion Predictor & Port Operations Optimiser

> 🔴 **Critical Now** · Logistics & Ports

**The ask, in one line**
Look at which ships are arriving over the next three days against what the port can actually handle, predict where the jam will be, suggest rerouting, allocate the docks and cranes, and print the shift supervisor a plan.

**Jargon decoded**

| Term | What it means |
|---|---|
| **Berth** | A parking space for a ship at the quayside. There are a fixed number of them and that's the fundamental constraint the whole port runs into. |
| **Quay crane / gantry crane** | The enormous machines that lift containers off ships. Also finite, also assigned by hand. |
| **Yard** | The stacking area where containers sit after being unloaded and before being collected. |
| **Dwell time** | How long a container sits in the yard before it leaves. Long dwell times fill the yard and jam everything behind it. |
| **TEU** | Twenty-foot Equivalent Unit — the standard way of counting containers, since they come in 20ft and 40ft sizes. |
| **ETA** | Estimated time of arrival, as declared by the ship. Frequently wrong, which is a large part of the problem. |
| **Congestion hotspot** | A time and place where more ships want service than the port can give. |
| **Berth allocation problem** | The formal name for "which ship goes where and when." It's a known, genuinely hard scheduling problem in operations research. |

**What you'd actually build** — four distinct features:
1. Predict congestion hotspots from vessel schedules and berth capacity.
2. Recommend alternate routing strategies.
3. Optimise berth and crane assignments.
4. Generate a 72-hour port operations plan for shift supervisors.

**Who's actually using it**
A port shift supervisor or berth planner — who, per the problem statement, is currently doing all of this **manually in spreadsheets**.

**In plain English**
A port has a fixed number of places for ships to dock and a fixed number of cranes to unload them. Ships arrive late, arrive early, and arrive in bunches. Someone plans all of this by hand in a spreadsheet, and typically only notices there's a problem when ships are already queuing outside the harbour — by which point it is far too late to send anyone elsewhere. In 2021 the Los Angeles jam had over a hundred ships waiting for weeks and cost global supply chains more than ten billion dollars.

This tool looks at the next three days of arrivals against what the port can genuinely handle and says "Thursday afternoon you are two berths short." It suggests which specific ships to send elsewhere or which slots to shuffle. It works out which crane goes to which ship. And it prints the supervisor a plan for the next seventy-two hours instead of a blank spreadsheet.

**Why it matters now**
The 2021 LA/Long Beach backlog: 100+ ships waiting offshore for weeks, **$10 billion+** in supply chain cost. Hotspots are currently found reactively, and rerouting decisions come too late to help.

**Hackathon reality check**

- **Data:** 🟡 Mixed. AIS (the public ship-tracking transponder system) data is partially available on free tiers. UNCTAD publishes port statistics. Actual berth schedules would be synthesized.
- **Core algorithm:** This is real operations research — the berth allocation problem is formally NP-hard. The good news: a greedy heuristic, or Google's free OR-Tools solver, gets you a perfectly respectable answer. Congestion prediction is queueing simulation.
- **Where Bob genuinely earns its place:** ⚠️ **Watch this carefully.** This is the *least* LLM-shaped problem of the ten — the core is a solver, not a reasoner. Bob's genuine place is in explaining the trade-offs ("I delayed vessel X by four hours because it freed a berth for two vessels with tighter deadlines") and in the 72-hour plan narrative. If you pick this, design that in deliberately or you'll lose the 10 Bob Integration points.
- **The hook that stops it being generic:** Genuine scheduling optimisation, and the 72-hour forward window — moving the decision from reactive to planned is the entire point.
- **Demo value:** 🟢 High. A berth-occupancy Gantt chart, before and after optimisation, is immediately legible even to someone who knows nothing about ports.
- **Difficulty:** 🟠 Medium-High. Optimisation is very satisfying to build and reliably eats more time than you budgeted.

---

### L2 — Supply Chain Disruption Assistant & Fleet Utilisation Optimizer

> 🟠 **Ongoing Pain** *(the only problem not flagged "Critical Now")* · Logistics & Ports

**The ask, in one line**
When a disruption hits, instantly say which shipments are affected and what to do about them; find the trucks and containers sitting idle that could be redeployed; and watch the temperature loggers on refrigerated cargo so a breach is caught in transit rather than at delivery.

**Jargon decoded**

| Term | What it means |
|---|---|
| **Cold chain** | Cargo that must stay within a temperature range for its whole journey. Vaccines at 2–8°C, some at −70°C. Frozen food. Certain chemicals. |
| **Temperature excursion** | A period where the cargo went outside its allowed range. Depending on how far and how long, the entire shipment may become legally unusable — not damaged, just no longer certifiable, which amounts to the same thing. |
| **Leg** | One segment of a journey: factory to port, the sea crossing, port to warehouse. A breach on *any single leg* can ruin the whole shipment. |
| **IoT sensor log** | The temperature and humidity data logger travelling inside the container with the cargo. |
| **Fleet utilisation** | What proportion of your trucks, containers and vessels are actually earning money rather than sitting still somewhere. |
| **Carrier** | The shipping company actually moving the goods. Switching carrier is one of the levers you have when a route breaks. |
| **MKT** | Mean Kinetic Temperature — the pharma industry's standard way of scoring a temperature excursion. It weights hot periods more heavily than a simple average, because degradation accelerates with heat. This is how "how bad was it, really?" is answered formally. |
| **Regulatory severity** | Whether the excursion breached the product's approved stability limits. Determines whether it's a note in a file or a destroyed batch. |

**What you'd actually build** — four distinct features:
1. Given an active disruption, identify which shipments are affected.
2. Recommend re-routing or alternative carriers.
3. Identify idle fleet assets for redeployment.
4. Monitor cold chain IoT sensor logs, detect temperature excursions, and classify their regulatory severity **before delivery**.

**Who's actually using it**
A logistics control-tower coordinator for features 1–3; a quality or compliance officer for feature 4.

**In plain English**
A storm closes a port. Or a strike starts, or a border shuts. Hundreds of your shipments are somewhere in motion, and you have no quick way to know which ones just became a problem — people work it out one shipment at a time over the following days, while the situation keeps changing.

Meanwhile, half your trucks and containers are sitting empty in one place while another route is desperately overloaded, and nobody has the overall picture to match them up.

And the most expensive failure of the lot is completely silent: a shipment of vaccines worth half a million pounds gets too warm for three hours on one leg of its journey. The temperature logger dutifully records it. Nobody looks at that logger until the box is opened at the destination — at which point the cargo is a write-off and nothing can be done.

This tool answers "what does this disruption break?" in seconds instead of days, suggests other routes or other carriers, points out the idle equipment you could be using, and — most importantly — watches those temperature loggers *while the shipment is still moving*, so you hear about the breach at a point where the cargo can still be saved, diverted, or at minimum replaced before the customer is left short.

**Why it matters now**
Disruptions cascade across hundreds of shipments in ways nobody can track by hand. Fleet assets sit idle while other routes overload. **A single temperature excursion can spoil $500,000+ of cargo, and it's only discovered at delivery — too late.**

**Hackathon reality check**

- **Data:** 🟡 Synthetic — but this is one of the easiest to fake convincingly. Shipment records and temperature logger traces are simple to generate believably, and you can drive real disruptions off free NOAA weather data.
- **Core algorithm:** Impact propagation across a route graph (which shipments touch the affected node). Rule-based excursion detection with cumulative-time thresholds — and **use Mean Kinetic Temperature** rather than a naive min/max check; it's the real industry metric and it instantly makes the compliance logic look like it was built by someone who did their homework. Idle-asset matching is a straightforward assignment problem.
- **Where Bob genuinely earns its place:** The disruption impact narrative, the rerouting recommendation *with its trade-offs stated*, and the severity classification with written justification against the product's stability rules.
- **The hook that stops it being generic:** **The timing.** Every cold chain product on the market tells you about the breach afterwards. Catching it in transit, while intervention is still possible, is the entire value proposition — and the problem statement says so explicitly: "before delivery."
- **Difficulty:** 🟢 Medium-Low to Medium. Three sub-features, each individually tractable, which makes it a safe choice for a small team.
- **One note:** This is the only problem tagged **"Ongoing Pain"** rather than **"Critical Now."** That's a slightly softer urgency framing than the other nine, which may matter marginally for the 15-point "Problem Depth & Vision" criterion. You'd want to make the urgency case yourself rather than leaning on the label.

---

## 5. The pattern hiding in all ten

Read the ten "Your Challenge" paragraphs back to back and the same machine appears every time:

```
Ingest messy data          →  Detect / correlate      →  Score and rank
from several incompatible      the things that            by how bad it is
sources                        actually matter

                           →  Explain each one        →  Emit a prioritised
                              in plain language          action plan
```

- **D1:** ingest sensors + records → identify non-ready → explain → predict → prioritised maintenance plan
- **D2:** ingest feeds → correlate → map to ATT&CK → prioritised BLUF summaries
- **S1:** analyse lots → identify patterns → rank causes → recommend actions → flag upcoming batches
- **S2:** identify bottleneck → predict impact → evaluate supplier risk → advise
- **P1:** compare to protocol → classify severity → score sites → generate CAPA reports
- **P2:** cluster events → calculate PRR → flag signals / check structure → gap report
- **U1:** combine sensors + weather + history → predict → rank by impact → maintenance + crew plan
- **U2:** forecast → recommend → detect anomalies → root cause → operator brief
- **L1:** predict hotspots → recommend rerouting → optimise assignments → 72-hour plan *(the partial exception — its core is genuine optimisation, not correlation)*
- **L2:** identify affected → recommend reroute → identify idle assets → monitor and classify

**What this means for you, practically:**

1. **Pick on interest, not on perceived difficulty.** The engineering effort is broadly comparable. Pick the domain someone on the team can talk about with conviction for fifteen minutes — that conviction is what the 15-point "Problem Depth & Vision" criterion is actually measuring.

2. **This is also the trap.** "Innovation & Differentiation" is worth **25 points** — the joint-largest criterion — and the guide says it's *"anchored in the code."* If you build the generic version of this pipeline, you have built what every other team built. Each breakdown above names the one specific thing that makes that problem *not* the generic version. Build that thing first, not last.

3. **The "explain" step is where the points are.** Four of the six scoring criteria reward things that come out of the explanation and recommendation layer, and it's also where IBM Bob is genuinely load-bearing rather than decorative. Teams naturally spend their time on the detection algorithm and bolt on explanation at the end. That's backwards for this rubric.

---

## 6. What "IBM Bob integration" actually means

Worth 10 points, and the rubric wording is pointed: *"Is IBM Bob load-bearing in the solution, not just name-dropped?"* This is the most commonly misread requirement, so it's worth being precise.

IBM Bob is an **AI coding agent that lives in your IDE** — it explains codebases, plans and writes features, reviews changes, runs terminal commands, spawns subagents for research, and connects to outside systems via **MCP (Model Context Protocol)**. It is a development partner, not a runtime API you call from your app.

That gives you two ways to make it load-bearing, and they're not equally strong:

| Approach | What it looks like | How strong |
|---|---|---|
| **Built *with* Bob** | You used Bob to build the project and can evidence it — custom Rules/Modes/Skills configured for your project, `/review` in your workflow, subagents for research, Bob Shell for ops. Documented in your repo. | 🟡 Legitimate, but every team can claim it. On its own it reads as "we used the tool." |
| **Bob is *in* the product** | You build an **MCP server** exposing your solution's capabilities as tools, so Bob itself becomes the conversational front end. The analyst literally talks to Bob, and Bob calls your correlation engine, your PRR calculator, your risk scorer. | 🟢 **Much stronger.** Bob is now architecturally load-bearing — remove it and the product loses its interface. |

**The submission template guide's own example architecture diagram shows exactly the second pattern:**

```
User  --Chat prompt-->  IBM Bob CLI
                            |
                        MCP call
                            v
                      Your MCP Server
                        /         \
                    API            Query
                     v               v
                watsonx.ai      PostgreSQL
```

That diagram is effectively a hint about what a well-integrated submission looks like. **Do both** — build it with Bob *and* expose it to Bob over MCP — and document each clearly.

> This interpretation is our reading of the rubric wording and the template's example diagram, not an explicit instruction from the organisers. If you can ask them directly, do.

---

## 7. Shortlist and recommendation

Scored against the actual rubric from the submission guide:

| # | Criterion | Points |
|---|---|---|
| 1 | Technical Implementation Quality | 25 |
| 2 | Innovation & Differentiation | 25 |
| 3 | Problem Depth & Vision | 15 |
| 4 | Working Demo & Functionality | 15 |
| 5 | IBM Bob Integration | 10 |
| 6 | Documentation & Reproducibility | 10 |

Half the available points (criteria 1 and 2) depend on **code that actually does something non-obvious**. Criterion 4 depends on it **running**. So the deciding question for choosing a problem is: *which of these can we get genuinely working, with real data, in the time we have?*

### 🥇 First choice — P2, Drug Safety Signal Detector

**Why:** Real public data (FAERS, 20M+ reports, free), a real standard method (PRR — simple arithmetic, but it's what the industry actually uses, so it's defensible rather than invented), and **the single best demo available to any team here**: run it over historical data and watch it flag a drug that was genuinely withdrawn years later. "Actual output being produced, not mocked" — which the guide explicitly asks for in the demo video — doesn't get more convincing than catching a real disaster in real data.

**Watch out for:** It's two products. Build Mode 1 (signal detection) properly, Mode 2 (submission readiness) competently, and be honest about the balance in `known_limitations` — the guide says honest limitations are respected and overclaiming is penalised.

### 🥈 Second choice — D2, Threat Intelligence Correlation

**Why:** MITRE ATT&CK is free, real, and already machine-readable, so your taxonomy is solved in an afternoon. The output format (BLUF) is text generation over evidence, which is the most natural fit for an LLM agent of all ten problems — meaning the Bob Integration points come naturally rather than being retrofitted. Correlation logic is genuinely interesting code. Best impressiveness-per-hour on the list.

**Watch out for:** Alert data is synthetic, so invest in making it realistic — a good synthetic attack scenario with a real kill chain buried in noise is worth the time and makes the demo.

### 🥉 Third choice — U1, Power Outage Prediction

**Why:** Free live weather APIs with no key required, free public outage history, and **the best-looking demo of the ten** — a map with a storm track and at-risk assets lighting up beneath it. The core insight is a genuine one and it's stated in the problem itself: the two datasets that would predict the outage exist but are never combined in time. Moderate difficulty, high visual payoff.

**Watch out for:** Asset sensor data is simulated, so ground it in real physics (partial discharge trends, oil degradation curves) rather than random numbers.

### Also worth a look

- **P1 (Clinical Trial Risk)** — 🟢 **the easiest to actually finish.** A rules engine is fast, deterministic, and hard to get visibly wrong. The "protocol as a machine-readable spec" idea is a genuinely good innovation hook. Pick this if the team is small, time is short, or you'd rather ship something complete than something ambitious and half-working. The guide is explicit that *"partial functionality that runs scores better than complete scaffolding that doesn't."*
- **S1 (Wafer Yield)** — pick this **only if someone on the team is comfortable with image models.** The WM-811K dataset is a real gift, but the ML is a genuine time sink and the Bob integration needs designing in deliberately.
- **L2 (Supply Chain / Cold Chain)** — safe, tractable, good demo. The cold chain half is the strong part; consider leading with it.

### Probably avoid for a hackathon

- **S2 (Fab Bottleneck)** — 🔴 two products, no public data for the fab half, and simulation work that will eat a day.
- **U2 (Grid Load)** — five deliverables in one challenge statement, and forecasting done in a hurry looks bad to anyone who knows the domain.
- **L1 (Port Optimiser)** — the optimisation is fun and will consume more time than you plan, and it's the weakest natural fit for Bob.

---

## 8. Bringing your own problem statement

The problem statements PDF says this plainly, and it's easy to miss:

> *"The problem statements below are provided as inspiration and serve as a starting point — they are not a definitive or exhaustive list. You are encouraged to bring your own problem statements, whether drawn from your industry experience or beyond the domains listed here."*

If someone on the team has a real problem from their own working life, that's a legitimate and often *stronger* option — because "Problem Depth & Vision" (15 points) asks whether you understand the problem rather than just the spec, and lived experience beats research every time.

To score well, a self-proposed problem should clear the same bars the official ten do:

- [ ] **A named human** whose day gets measurably better, not an abstract "the business."
- [ ] **A quantified pain** — hours lost, error rate, money. The official ten all have a number; yours should too.
- [ ] **Why existing tools don't already solve it.** The `docs/problem-statement.md` file asks for exactly this.
- [ ] **Data you can actually get** in the time available.
- [ ] **A non-obvious mechanism** — the 25 innovation points need something more than "we put an LLM in front of it."
- [ ] **A genuine role for Bob**, per [section 6](#6-what-ibm-bob-integration-actually-means).

---

*Analysis compiled from the three official hackathon PDFs: the IBM Bob Getting Started Guide, Industry Problem Statements 2026, and the Bobathon Submission Template Guide. Problem descriptions and figures are the organisers'; decoding, personas, dataset suggestions, difficulty ratings and recommendations are our own and open to argument.*
