---
name: preflight
description: 'Demo-day preflight — tests green, every demo command works OFFLINE, repo clean'
metadata:
  user-invocable: true
  disable-model-invocation: true
  argument-hint: (no arguments)
---

Run the Pharos demo-day preflight from the `src/` directory and report a pass/fail table. Do not fix anything unless I ask — just report.

1. `python -m pytest tests -q` → expect all passed.
2. With the environment variable `PHAROS_OFFLINE=1` set (PowerShell: `$env:PHAROS_OFFLINE = "1"`), each of these must exit 0 without touching the network:
   - `python -m pharos scan rofecoxib --alias vioxx --no-clusters`
   - `python -m pharos hidden rosiglitazone --alias avandia --as-of 2006`
   - `python -m pharos hidden sibutramine --alias meridia --alias reductil --as-of 2006`
   - `python -m pharos timeline rosiglitazone "myocardial infarction" --alias avandia -x auto --to 2013`
   - `python -m pharos scan metformin --alias glucophage --no-clusters`
   - `python -m pharos prr rofecoxib "myocardial infarction" --alias vioxx`
   - `python -m pharos ctd-check data/samples/dossier_complete.yaml`
   - `python -m pharos ctd-check data/samples/dossier_incomplete.yaml` → this one must exit **1** (NOT READY) — that is the pass condition.
   Unset `PHAROS_OFFLINE` afterwards.
3. In the timeline output confirm the headline contains "2008" (standard) and "2006" (corrected). In the hidden-signals output confirm MYOCARDIAL INFARCTION is reported as hidden.
4. `git status --short` → report anything uncommitted; confirm `src/.env` is NOT tracked (`git ls-files src/.env` prints nothing).
5. Summarise: ✅/❌ per line, then one sentence — are we safe to demo with Wi-Fi off?

If a command reports a cache miss, say which one and that the fix is `python -m pharos build-cache` while online.
