# Setup Guide

Written for someone who has never seen this repo. Every command is copy-pasteable. Tested on Windows 11 with Python 3.11.6; the commands are the same on macOS/Linux except where noted.

## 1. Prerequisites

| Requirement | Version | Check | Notes |
|---|---|---|---|
| Python | 3.10 or newer | `python --version` | 3.11 recommended. Windows: [python.org](https://www.python.org/downloads/) — tick *Add to PATH*. |
| pip | any recent | `pip --version` | Ships with Python. |
| git | any | `git --version` | Only to clone. |
| Internet | — | — | For the first run and for drugs outside the demo set. The demo drugs work **offline** from the committed cache. |
| IBM Bob | current | — | Only for the MCP integration ([bob-integration.md](bob-integration.md)). Everything else runs without Bob. |

No accounts, no API keys, no database. An optional free openFDA key raises rate limits (see §4).

## 2. Install

```bash
# 1. Clone and enter the source directory
git clone https://github.com/Jainishcodee/bob-ai-hackathon-Sudo-Salingers.git
cd bob-ai-hackathon-Sudo-Salingers/src

# 2. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate                # Windows PowerShell / cmd
# source .venv/bin/activate           # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install Pharos itself (editable, so `python -m pharos` and `pharos` both work)
pip install -e . --no-build-isolation
```

`--no-build-isolation` avoids pip re-downloading setuptools just to build the tiny package; drop the flag if you prefer.

## 3. Environment variables

All optional. Copy the template if you want to set any:

```bash
copy .env.example .env               # Windows
# cp .env.example .env               # macOS / Linux
```

| Variable | Default | Purpose |
|---|---|---|
| `OPENFDA_API_KEY` | *(empty)* | Free key from <https://open.fda.gov/apis/authentication/>. Lifts daily limit from 1,000 to 120,000 requests and count queries from 500 to 1,000 terms. Not needed for the demo. |
| `PHAROS_OFFLINE` | `0` | Set to `1` to never touch the network — serve only from the on-disk cache. |
| `PHAROS_CACHE_DIR` | `src/pharos/faers/cache/` | Where cached openFDA responses live. The repo ships with the demo drugs pre-cached. |

## 4. Run

All commands from `src/` with the virtual environment active.

### Mode 1 — signal detection (CLI)

```bash
# The headline demo: Vioxx. Live query against openFDA, ~5–15 s.
python -m pharos scan rofecoxib --alias vioxx

# Any other drug; aliases are optional but brand names matter for older drugs
python -m pharos scan rosiglitazone --alias avandia
python -m pharos scan cerivastatin --alias baycol --alias lipobay

# One exact drug–reaction pair with the full 2×2 table
python -m pharos prr rofecoxib "myocardial infarction" --alias vioxx

# Show everything (non-signals and administrative terms too), export JSON
python -m pharos scan ibuprofen --alias advil --all --json ibuprofen.json

# WHEN did the signal emerge, and what masked it? (4–7 requests per year; ~30 s live, instant from cache)
python -m pharos timeline rosiglitazone "myocardial infarction" --alias avandia --to 2013
python -m pharos timeline rosiglitazone "myocardial infarction" --alias avandia -x rofecoxib -x vioxx --to 2013
```

The second form excludes Vioxx from the comparator background. Compare the two headlines: standard screen flags 2008; masking-corrected flags 2006.

### Mode 2 — submission readiness (CLI)

```bash
python -m pharos ctd-check data/samples/dossier_incomplete.yaml            # exits 1: NOT READY, gaps listed
python -m pharos ctd-check data/samples/dossier_complete.yaml              # exits 0: READY, 100%
python -m pharos ctd-check data/samples/dossier_incomplete.yaml --report gap_report.md --json check.json
python -m pharos ctd-template --region EU --out my_dossier.yaml            # blank outline to fill in
```

### Dashboard

```bash
streamlit run app/streamlit_app.py
```

Opens <http://localhost:8501>. Tab 1: pick *ROFECOXIB · Vioxx* from the dropdown → **Scan for signals**. Tab 2: *Sample — incomplete dossier* is pre-selected.

### MCP server for IBM Bob

```bash
python -m mcp_server.server
```

Runs on stdio and waits for an MCP client — you don't interact with it directly. Register it in Bob per [bob-integration.md](bob-integration.md).

### Offline demo

```bash
python -m pharos build-cache          # once, while online — ~1 minute, 8 demo drugs
set PHAROS_OFFLINE=1                  # Windows      (macOS/Linux: export PHAROS_OFFLINE=1)
python -m pharos scan rofecoxib --alias vioxx   # now served entirely from disk
```

The repository already ships with this cache populated, so the demo drugs work offline out of the box.

## 5. Verify it's working

```bash
python -m pytest tests -q
```

Expected: `50 passed`. The tests are fully offline (fake FAERS client, hand-computed reference values, headless Streamlit).

Then:

| Check | Command | You should see |
|---|---|---|
| Statistics | `python -m pharos prr rofecoxib "myocardial infarction" --alias vioxx` | A 2×2 table with `a ≈ 19,886`, PRR ≈ 49, **SIGNAL · strong** |
| Scan | `python -m pharos scan rofecoxib --alias vioxx` | ~30 clinical signals; MYOCARDIAL INFARCTION, CORONARY ARTERY DISEASE, CEREBROVASCULAR ACCIDENT near the top; a *Cardiac disorders* cluster |
| Timeline | `python -m pharos timeline rosiglitazone "myocardial infarction" --alias avandia -x rofecoxib -x vioxx --to 2013` | Headline: standard first flag **2008** (1 yr after Nissen); `VIOXX (72%) ⚠` in the 2006 masking column; Vioxx-excluded first flag **2006** (1 yr before Nissen); "brings detection forward by 2 years" |
| CTD (bad) | `python -m pharos ctd-check data/samples/dossier_incomplete.yaml` | NOT READY, 75.4%, 12 gaps (10 critical) incl. 1.14, 3.2.P.8, 5.3.5.3 and all 4.2.3.x; a warning that "4.2.3" was listed as a single section; exit code 1 |
| CTD (good) | `python -m pharos ctd-check data/samples/dossier_complete.yaml` | READY TO SUBMIT, 100% |
| UI | `streamlit run app/streamlit_app.py` | Browser opens; sidebar shows "Reports in FAERS: 20,6xx,xxx" |

Exact counts drift slightly as FDA adds reports.

## 6. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `openFDA returned HTTP 403 … API_KEY_MISSING` | A `count` query asked for more than 500 terms without a key. | Pharos caps at 500 automatically; if you changed the cap, set `OPENFDA_API_KEY` or lower `--top`. |
| `HTTP 429` / very slow | Rate-limited (240/min, 1,000/day keyless). | Wait a minute; set `OPENFDA_API_KEY`; or use the cache (`PHAROS_OFFLINE=1`). |
| `OfflineCacheMiss: PHAROS_OFFLINE is set and this query is not cached` | Offline mode with a drug that was never fetched. | Unset `PHAROS_OFFLINE`, or run `python -m pharos build-cache` while online. |
| `Network error calling openFDA` / DNS errors | No internet or a proxy. | Use `PHAROS_OFFLINE=1` for the demo drugs; check proxy settings for others. |
| `pip install` times out | Flaky connection to PyPI. | `pip install --timeout 90 --retries 8 -r requirements.txt` |
| `pip install -e .` fails fetching setuptools | Build isolation needs network. | Add `--no-build-isolation` (setuptools is already installed). |
| `pharos: command not found` | Editable install skipped or venv not active. | Use `python -m pharos …` — identical. |
| `ModuleNotFoundError: No module named 'pharos'` | Running from the wrong directory. | `cd src` first, or `pip install -e . --no-build-isolation`. |
| Streamlit: `Port 8501 is already in use` | Another Streamlit running. | `streamlit run app/streamlit_app.py --server.port 8502` |
| Streamlit shows no chart for a drug | Zero clinical signals under the criteria, or the drug name isn't how FAERS spells it. | Toggle *Include non-signals*; add a brand-name alias; try the generic in CAPITALS as FAERS lists it. |
| Bob doesn't list the Pharos tools | MCP server not registered or wrong Python path. | See [bob-integration.md](bob-integration.md); make sure the `command` points at the venv's `python`. |
| Vioxx numbers look "too big" | They are — litigation-driven reporting inflated Vioxx's FAERS counts. | This is real and expected; it's a known reporting bias, and Bob is instructed to mention it. |

## 7. Uninstall / clean

```bash
deactivate
rmdir /s /q .venv          # Windows      (macOS/Linux: rm -rf .venv)
```

Nothing is installed outside the virtual environment and the repo directory.
