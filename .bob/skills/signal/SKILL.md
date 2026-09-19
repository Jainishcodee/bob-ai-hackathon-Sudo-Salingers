---
name: signal
description: >-
  Full drug-safety signal assessment (scan → label triage → verify → cases →
  masking → timeline → memo)
metadata:
  user-invocable: true
  disable-model-invocation: true
  argument-hint: '<drug> [brand names, comma-separated]'
---

Run a complete pharmacovigilance signal assessment for **$1** (aliases: $2) using the pharos MCP tools and the `signal-assessment` skill.

Follow the skill's procedure exactly: scan_signals → split signals into NOT on the FDA label vs labelled → confirm the top 3 with compute_prr → read 2–3 real cases each with search_reports → find_hidden_signals → signal_emergence_timeline with exclude_drugs="auto" for the lead signal → cluster_signals_by_organ_system → one-page BLUF memo using the skill's memo template.

If no aliases were given, tell me which brand names you think apply and ask before scanning — brand names change the counts dramatically for older drugs.
