# Pharos — engineering rules (apply in every mode)

## Layout

All code lives in `src/`. Engine: `src/pharos/` (`faers/` client · `signals/` statistics · `ctd/` dossier checker · `cli.py`). Bob's tools: `src/mcp_server/server.py`. Dashboard: `src/app/streamlit_app.py`. Tests: `src/tests/`. Run everything from `src/`.

## Non-negotiables

- **Tests stay green.** Run `python -m pytest tests -q` from `src/` before calling any change done. Tests are offline by design — never add a test that touches the network; use a fake client like the ones in `tests/test_masking.py`.
- **Statistics need a hand calculation.** Any change to `src/pharos/signals/stats.py` ships with a test whose expected value is derived by hand in a comment (see `tests/test_stats.py`). Do not change how `is_signal` (the Evans rule) is computed — add new metrics beside it.
- **Evidence and reasoning stay separate.** Code under `src/pharos/` returns numbers and structured data only — no prose opinions, no LLM calls. Interpretation belongs to the agent calling the MCP tools.
- **Reactions are matched exactly.** Use `client.reaction_expression()` (the `.exact` field). A phrase match over-counts up to 6× and disagrees with the `count` endpoint.
- **No look-ahead.** Anything that claims "detectable in year Y" may only use reports received by 31 Dec Y and only maskers that had crossed the threshold by year Y. `test_auto_exclusion_is_prospective_with_no_look_ahead` guards this — never weaken it.
- **The ICH M4 checklist is data, not code**: `src/pharos/ctd/data/ich_m4_ctd.yaml`. Every section needs `required`, `weight` (3 critical · 2 major · 1 minor) and a one-line `note` saying why it matters.

## Hands off

- Never read, print or edit `src/.env` (it holds a real API key). `.env.example` is the template and must never contain a real value.
- Never delete or hand-edit `src/pharos/faers/cache/` — it is the committed offline demo. Regenerate with `python -m pharos build-cache`.
- Do not modify `.github/workflows/validate.yml` or delete `CONTRIBUTING.md` (hackathon template rules).

## Style

Match the surrounding code: type hints, dataclasses for results with an `as_dict()`, a module docstring that explains *why*, comments only where the reason is not obvious. New MCP tools need a docstring written for an agent: what it returns, when to use it, and an example.
