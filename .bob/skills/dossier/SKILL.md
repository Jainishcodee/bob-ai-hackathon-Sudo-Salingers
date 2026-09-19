---
name: dossier
description: >-
  Audit a dossier outline against ICH M4 CTD and produce an ordered remediation
  plan
metadata:
  user-invocable: true
  disable-model-invocation: true
  argument-hint: '<path to outline .yaml/.json> [US|EU]'
---

Using the pharos `check_ctd_dossier` tool and the `dossier-remediation` skill, audit the dossier outline at **$1** (region: $2 — default to the outline's own region if blank).

Produce: the readiness verdict; module-by-module status; critical gaps first with why each would cause a refuse-to-file or a deficiency letter; an order of work that respects section dependencies; the owning function for each gap; and what cannot be parallelised. Call out any parent section listed instead of its required sub-sections.

If no path was given, use `src/data/samples/dossier_incomplete.yaml`.
