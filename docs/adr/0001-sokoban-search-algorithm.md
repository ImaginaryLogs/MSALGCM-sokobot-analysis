# ADR 0001 — Sokoban search algorithm: Weighted A* + closed list

**Date:** 2026-07-17
**Status:** Accepted

## Decision

Weighted A* with a closed list, `f = g + w·h`, closed-list skip predicate is strict `g > stored`
(NOT `≥` — `≥` drops equal-cost optimal paths). **NOT IDA\*** — Sokoban transposition (many move
orders reach the same crate configuration) makes a closed list mandatory; IDA*'s no-closed-list
design would re-explore transposed states unboundedly.

State = sorted crate tuple + normalized player cell (flood-fill region → canonical min-index
cell). Successors = legal crate pushes only. `g` = push count. Base heuristic = greedy Manhattan
sum (admissible), behind a swappable `heuristic()` seam — Hungarian min-cost matching is a
committed Phase-2 build (see [DECISIONS.md](../DECISIONS.md)). Deadlock pruning = static
dead-squares (reverse-pull BFS from goals), constant across both heuristic arms.

## Why

- Sokoban's state space has heavy transposition — different push orders reach identical crate
  layouts — so revisits must be caught by a closed list, not just avoided by IDA*'s path-only
  memory.
- `g > stored` (strict) rather than `g ≥ stored`: the `≥` variant discards a re-discovered path
  tied with the stored cost, which can be the only path continuing to the optimal solution —
  silently drops optimal solutions in graphs with many equal-cost paths.
- `w = 1` optimality is load-bearing (anchors both experimental arms — see
  [DECISIONS.md](../DECISIONS.md)) and is verified by a small-map UCS optimality oracle in
  `validator.py`, not assumed from admissibility alone.

## Consequences

- Module layout fixed: `board.py`/`loader.py`/`deadlock.py` → `state.py` → `heuristic.py` +
  `solver.py` (closed-list TT) → `metrics.py`/`emit.py` → `validator.py` → `cli.py`. Full build
  order in [`docs/specs/sokoban-port-plan.md`](../specs/sokoban-port-plan.md).
- Do not chase Java (`CSINTSY-sokobot2024`) node-count parity — it runs greedy best-first, a
  different algorithm by design.
