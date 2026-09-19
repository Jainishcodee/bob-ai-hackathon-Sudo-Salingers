---
name: add-signal-metric
description: How to add a new disproportionality statistic or signal metric to Pharos the house way — hand-computed reference test first, implementation beside (never instead of) the Evans rule, wiring into the scan table, MCP output, CLI and dashboard, and docs. Use when asked to add, implement or change a statistic such as IC, IC025, EBGM, BCPNN, ROR variants, or a new signal criterion.
---

# Adding a signal metric to Pharos

Statistics are the part of this project a regulator would audit. Order of work is fixed.

## 1. Write the hand calculation first

In `src/tests/test_stats.py`, add a test whose expected value is derived **by hand in a comment**, using the reference table already in that file:

```
a=10, b=90, c=100, d=9,800   (drug total 100 · event total 110 · N 10,000)
PRR = 9.9 · ROR = 10.888… · χ²(Yates) = 65.51
```

Show the arithmetic step by step. Add an edge case: a zero cell (Haldane correction applies) and a null association (expected ≈ no signal). Run the test and watch it fail.

## 2. Implement beside, not instead

In `src/pharos/signals/stats.py`:
- a pure function `metric(t: ContingencyTable) -> float` with a docstring citing the source paper;
- new fields on `DisproportionalityResult`, populated in `evaluate()`;
- **do not** change how `is_signal` is computed. A second opinion gets its own flag (e.g. `is_signal_ic`). Disagreement between methods is information — expose it, don't resolve it silently.

## 3. Wire it through

- `src/pharos/signals/detector.py` — add columns to `COLUMNS` and to the row dict in `scan_drug`; include in `compute_pair` output.
- `src/mcp_server/server.py` — mention the new fields in the `scan_signals` / `compute_prr` docstrings so the agent knows they exist and what they mean.
- `src/pharos/cli.py` — a column in the `scan` table only if it fits an 100-column terminal; otherwise show it in `prr`.
- `src/app/streamlit_app.py` — add to the table; a "methods disagree" count is more useful than another number.

## 4. Prove nothing else moved

`python -m pytest tests -q` from `src/` — all green, including `test_detector.py` (fake client) and `test_app_smoke.py` (headless dashboard from the committed cache). The Avandia reference numbers must not change: standard first flag 2008, corrected 2006.

## 5. Document

One line in `README.md` key features, the formula and citation in `docs/solution-overview.md`, an entry in `docs/round2/PROGRESS-LOG.md`.

## Reference formulas

- **IC (WHO-UMC, BCPNN point estimate):** `E = (a+b)(a+c)/N`; `IC = log2((a+0.5)/(E+0.5))`; `IC025 ≈ IC − 3.3·(a+0.5)^−½ − 2·(a+0.5)^−3/2`; signal if `IC025 > 0` (Norén et al. 2013). Reference table: E = 1.1, IC = log2(10.5/1.6) = 2.714.
- **ROR lower bound criterion (EMA):** signal if the lower 95% bound of ROR > 1 and n ≥ 3 (or 5).
