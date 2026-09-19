---
name: progress
description: Add an entry to the hackathon progress log from what just changed
metadata:
  user-invocable: true
  disable-model-invocation: true
---

Update `docs/round2/PROGRESS-LOG.md`.

Look at @git-changes and the last few commits. Under today's date heading, add one row to the "What happened" table for each meaningful change since the last logged entry: time (now, 24-hour), what happened in one plain sentence a mentor can read at a glance, who / with Bob, and the short commit hash if committed.

Mentor context, if given: $1 — if this is non-empty, also add or update a row in the "Mentor feedback received today" table with what was asked and what we did about it.

Rules: newest first; facts only, no adjectives; if a number changed (tests, tools, a PRR) state old → new; do not rewrite earlier entries. Show me the diff before saving.
