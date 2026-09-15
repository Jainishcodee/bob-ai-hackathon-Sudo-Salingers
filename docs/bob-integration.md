# IBM Bob Integration

Pharos uses IBM Bob in two ways, and the distinction matters for how the project should be read.

| | How | Where to see it |
|---|---|---|
| **Bob built it** | Plan mode to design the module layout and the evidence/reasoning split; Agent mode to implement; `/review` on the statistics module before writing tests; a subagent to research openFDA query syntax and rate limits. | This repo's history and structure. |
| **Bob runs it** | Bob connects to the **Pharos MCP server** and becomes the conversational analyst: it calls the tools, verifies signals, reads real cases, and writes the memo. | `src/mcp_server/server.py`; this document. |

The second is the load-bearing one. Remove Bob and Pharos still computes but no longer explains or converses; remove Pharos and Bob would be guessing at statistics.

## 1. Register the MCP server in Bob

The Pharos server speaks MCP over **stdio** — the standard transport Bob (and every other MCP client) expects. You register it with a command, arguments, and optional environment variables.

**Step 1 — install Pharos** per [setup-guide.md](setup-guide.md) and note the absolute path to the venv's Python and to `src/`.

**Step 2 — open Bob's MCP settings.** In Bob, open the MCP Servers panel (see *MCP integrations* under bob.ibm.com/docs/ide) and edit the configuration. The configuration shape is the common MCP one:

```json
{
  "mcpServers": {
    "pharos": {
      "command": "G:\\path\\to\\bob-ai-hackathon-Sudo-Salingers\\src\\.venv\\Scripts\\python.exe",
      "args": ["-m", "mcp_server.server"],
      "cwd": "G:\\path\\to\\bob-ai-hackathon-Sudo-Salingers\\src",
      "env": {
        "PHAROS_OFFLINE": "0",
        "OPENFDA_API_KEY": ""
      }
    }
  }
}
```

macOS / Linux: `"command": "/path/to/src/.venv/bin/python"` and forward slashes in `cwd`.

If Bob's settings UI asks for fields rather than JSON: *command* = the python path, *arguments* = `-m mcp_server.server`, *working directory* = `src/`.

**Step 3 — confirm.** Bob should list seven tools under `pharos`:

`scan_signals` · `compute_prr` · `cluster_signals_by_organ_system` · `search_reports` · `signal_emergence_timeline` · `check_ctd_dossier` · `get_ctd_spec`

plus two prompt templates (`signal_assessment`, `dossier_gap_memo`) and a resource (`pharos://about`).

Without Bob to hand, you can sanity-check the server with any MCP client, or simply start it — `python -m mcp_server.server` — and confirm it stays running waiting on stdin.

## 2. What each tool gives Bob

| Tool | Returns | Bob uses it to |
|---|---|---|
| `scan_signals(drug, aliases, top_n, min_cases, prr_threshold, chi2_threshold)` | Ranked reactions with n, PRR + CI, ROR + CI, χ², signal flag, tier, administrative flag; interpretation notes | Get the overall picture for a drug |
| `compute_prr(drug, reaction, aliases)` | Exact 2×2 table + all statistics for one pair (uses an `AND` query, not the count approximation) | Verify the top signals before writing about them |
| `cluster_signals_by_organ_system(drug, aliases)` | One row per MedDRA SOC with signal count, cases, max PRR, strongest reaction, curated share | Answer "is this cardiac or hepatic?" |
| `search_reports(drug, reaction, aliases, limit)` | Trimmed real FAERS cases: id, date, seriousness, age/sex, reactions, co-drugs | Ground the statistics in narratives; spot confounders |
| `signal_emergence_timeline(drug, reaction, aliases, exclude_drugs, start_year, end_year, detect_masking)` | Per-year and cumulative PRR by FDA receive date; first-flag year; top contributing drugs per year with `masking_alert`; masking-corrected series when `exclude_drugs` is set; real regulatory milestones and lead time; a dated `headline` sentence | Answer "when could we have known, and what hid it?" — then re-run with the masking drug excluded |
| `check_ctd_dossier(outline_path | outline_json, region)` | Per-module scores, ranked gaps with severity and *why it matters*, warnings, verdict, Markdown report | Audit a dossier and write the remediation plan |
| `get_ctd_spec(region, as_blank_outline)` | The ICH M4 checklist, or a blank fillable outline | Explain what's required; generate a template for a team |

The server's `instructions` tell Bob to always state case count, PRR with CI and χ² when describing a signal, to name reporting biases, and never to claim causation. That is deliberate: Bob's fluency is the value, and the guard-rails keep it honest in a regulated domain.

## 3. Prompts that work

Paste into Bob once the server is registered.

**Signal assessment — the headline demo**

```
Using the pharos tools, run a signal assessment for rofecoxib (aliases: vioxx).
Confirm the top 3 clinical signals with compute_prr, pull 2 real cases each with
search_reports, group by organ system, and write a BLUF-style memo: one-line verdict,
evidence table (n, PRR [CI], chi²), organ-system picture, likely reporting biases,
recommended next step. Do not claim causation.
```

Expected shape of Bob's answer: a verdict sentence ("Strong, consistent cardiovascular disproportionality signal…"), a table led by myocardial infarction (n ≈ 18k, PRR ≈ 52), coronary artery disease, cerebrovascular accident; a note that the cardiac SOC dominates; a paragraph on litigation-driven reporting inflating Vioxx counts; a recommendation such as formal causality assessment / label review — with the explicit caveat that this is a retrospective look at a drug already withdrawn.

**When did it emerge, and what masked it? — the Avandia story**

```
Using pharos, run signal_emergence_timeline for rosiglitazone (aliases: avandia) ×
MYOCARDIAL INFARCTION from 2004 to 2013. Read the masking column: if one drug dominates
the MI reports in any year, run it again with that drug in exclude_drugs. Then tell me,
with years and numbers: when did the standard screen first flag it, when did the
masking-corrected screen flag it, how does each compare with the Nissen meta-analysis
(May 2007) and the FDA boxed warning (Nov 2007), and what does this imply for how
signal detection should be run?
```

Expected: Bob reports the standard first-flag year 2008 (after both milestones), notices `VIOXX` at 68–72% of MI reports in 2005–06, re-runs with `exclude_drugs="rofecoxib, vioxx"`, reports the corrected first-flag year 2006 (a year before Nissen), and concludes that disproportionality screens should routinely check for and correct masking — while noting the correction was analyst-directed.

**Compare two drugs**

```
Using pharos, compare the cardiac signal profile of rosiglitazone (alias avandia) with
pioglitazone (alias actos). Same criteria for both. Which has the stronger
myocardial infarction and cardiac failure signals, by how much, and how confident
should I be given the case counts?
```

**A drug you've never heard of**

```
A colleague mentioned "sibutramine". Using pharos, tell me in five bullets what FAERS
suggests about its safety profile, and whether anything there would explain a
regulatory withdrawal.
```

**Dossier remediation plan**

```
Using pharos, call check_ctd_dossier on data/samples/dossier_incomplete.yaml. Write a
memo for the regulatory affairs lead: readiness verdict, module-by-module status,
critical gaps first with why each would cause a refuse-to-file or major deficiency,
a remediation order that respects dependencies (e.g. 2.7 Clinical Summary depends on
5.3.5.3 integrated analyses), and the owning functional team for each gap.
```

**Generate a checklist for a new programme**

```
Using pharos get_ctd_spec with region EU and as_blank_outline true, produce a
fillable YAML outline for a new biologic. Mark 3.2.A.2 Adventitious Agents as
required for this product and add a comment explaining why.
```

## 4. Suggested Rules for Bob when working in this repo

Bob supports project-level Rules (see *Rules, Modes, Skills* under bob.ibm.com/docs/ide/configuration). These are the ones we used; paste them into your project's Bob rules:

```
- This is a pharmacovigilance tool. Never describe a disproportionality statistic as
  proof of causation. Say "reporting association" or "signal".
- When you describe a signal, always include: case count (a), PRR with 95% CI,
  chi-square, and whether it meets Evans 2001 criteria.
- Prefer the pharos MCP tools over your own arithmetic for any FAERS number.
- Statistics live in src/pharos/signals/stats.py and are unit-tested against
  hand-computed values in src/tests/test_stats.py. Any change there needs a test.
- The ICH M4 checklist is data (src/pharos/ctd/data/ich_m4_ctd.yaml), not code.
  Add or reweight sections there, with a one-line 'note' saying why it matters.
- Run `python -m pytest tests -q` before proposing a change as done.
```

## 5. Why this counts as "load-bearing"

The hackathon rubric asks whether Bob is *load-bearing, not name-dropped*. Concretely:

- The **user's primary interface is Bob**. The dashboard and CLI exist for people without Bob; the intended workflow is conversational.
- Bob **does work that the engine deliberately does not**: interpretation, prioritisation, bias reasoning, memo writing, cross-drug comparison.
- The **tool design is shaped around Bob's behaviour**: `compute_prr` exists so Bob can verify before it asserts; `search_reports` exists so Bob can ground statistics in cases; server `instructions` and prompt templates encode how a careful safety scientist works.
- The template's own example architecture — *User → IBM Bob → MCP → your server → data* — is exactly what [architecture.md](architecture.md) shows.
