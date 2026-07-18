# Handoff — Sokoban port implementation (2026-07-17)

**To:** the implementing agent (NOT CJ). **From:** grill session that finalized the port spec.
**Authoritative spec:** [`docs/specs/sokoban-port-plan.md`](docs/specs/sokoban-port-plan.md) —
implement into `MSALGCM-sokobot-analysis/src/sokoban/`. Everything below is orientation; the spec
governs on conflict. Locked decisions and their rationale: [`docs/DECISIONS.md`](docs/DECISIONS.md),
algorithm choice detail: [ADR 0001](docs/adr/0001-sokoban-search-algorithm.md).

## What you are building

A Python Sokoban solver for a **comparative search study** (Sokoban vs HP protein folding). The
solver's job is to emit a paradigm-neutral **effort metric** per run to a shared CSV, not to be a
production game AI. `CSINTSY-sokobot2024/` (Java) is a **reference, not source of truth** — its
solver is greedy best-first (non-optimal); do NOT faithfully port its algorithm.

## Build order (wk1 = #1 schedule risk)

1. `board.py` + `loader.py` (parse single `maps/<name>.txt`: `#.$@*+` + space) + `deadlock.py`.
2. `state.py` (push successors, normalization, canonical key).
3. `heuristic.py` (Manhattan) + `solver.py` (WA\* + closed-list TT, `g>stored`).
4. `metrics.py` + `emit.py` (CSV, D6 schema).
5. `validator.py` (replay + UCS optimality oracle) + `tests/` → validate every solve.
6. `cli.py` flags. THEN Phase-2: Hungarian `h` (scalar-ratio arm) + weight sweep (Pareto arm).

## Do NOT

- Import/copy `CSINTSY-sokobot2024/main.py` or its hardcoded Discord token into `src/sokoban/`.
- Chase Java node-count parity (different algorithm by design).
- Substitute best-found-so-far as pseudo-optimal on `w=1`-censored maps (corrupts ratios).

## Blocked on others (do not let these block the port)

- **CSV schema D6** — DRAFT, needs Enzo (harness) sign-off. Join key **resolved**: `nodes_expanded`
  (Roan confirmed B&B, [ADR 0002](docs/adr/0002-hp-engine-bnb.md)). Log both counters so no re-run
  is needed.
- **Map suite** (CJ) — done. 155 maps in `src/sokoban/maps/`, sourced from
  `CSINTSY-sokobot2024/maps/` (originals + a 1-in-10 sample of `sokoban-info/`'s 2716 XSokoban
  maps) and filtered by `scripts/build_map_suite.py` (w=1 Manhattan proves optimal, D2
  baseline-anchor rule). 152 excluded, logged in `src/sokoban/maps/EXCLUDED.md`.

## Phase-2 experiments — data collected, analysis next

Both headline arms ran full scale: `scripts/run_experiments.py` over all 155 suite maps x 7
configs (Arm A: manhattan vs hungarian @ w=1; Arm B: manhattan @ weight grid), 1085 rows in
`results/results.csv` (gitignored — regenerate via `uv run python scripts/run_experiments.py`).
1084 solved, 1 eval-budget cutoff. Eval budget, weight grid, and arm design:
[`docs/DECISIONS.md`](docs/DECISIONS.md) #9. Next: analysis notebook (Phase 3) — efficiency
ratios for Arm A, Pareto curves for Arm B.
