# Handoff — Sokoban port implementation (2026-07-17)

**To:** the implementing agent (NOT CJ). **From:** grill session that finalized the port spec.
**Authoritative spec:** [`sokoban-port-plan.md`](./sokoban-port-plan.md) — implement into
`MSALGCM-sokobot-analysis/src/sokoban/`. Everything below is orientation; the spec governs on conflict.

## What you are building
A Python Sokoban solver for a **comparative search study** (Sokoban vs HP protein folding). The
solver's job is to emit a paradigm-neutral **effort metric** per run to a shared CSV, not to be a
production game AI. `CSINTSY-sokobot2024/` (Java) is a **reference, not source of truth** — its
solver is greedy best-first (non-optimal); do NOT faithfully port its algorithm.

## Locked, do not re-litigate (grilled + advisor-checked)
- **Algorithm:** Weighted A* + closed list, `f=g+w·h`, closed-list skip predicate is strict
  **`g > stored`** (NOT `≥` — `≥` drops equal-cost optimal paths). NOT IDA*.
- **State:** crate-push macro moves; state = sorted crate tuple + **normalized** player cell
  (flood-fill region → canonical min-index cell). Successors = legal pushes only. `g` = push count.
- **Heuristic:** greedy Manhattan sum (admissible) behind a swappable `heuristic()` seam. **Hungarian
  min-cost matching is a committed Phase-2 build** — it is the strong-`h` half of the second arm.
- **Deadlock:** static dead-squares (reverse-pull BFS from goals), constant in both arms.
- **Metrics:** log BOTH `nodes_expanded` and `candidates_scored` (every successor you call
  `heuristic()` on, incl. closed/deadlock-pruned). Do NOT collapse them.
- **Stopping:** primary = eval budget `N` (shared constant); wall-clock = hang-safety only; record
  `cutoff_reason ∈ {NA, budget, clock}`. `solved ∈ {1, 0=proven-unsolvable, cutoff}`.
- **Validation:** pure-Python `validator.py` — (a) replay push seq, assert crates==goals; (b)
  **small-map UCS optimality oracle**, assert `w=1` result == BFS optimal `Q*`. This is mandatory:
  `w=1` optimality is load-bearing (anchors both experimental arms) and is NOT proven by
  admissibility alone — a `g≥stored` bug yields valid-but-suboptimal results the validity check
  passes blind. **Java oracle is removed from wk1** (optional/deferred).

## Build order (wk1 = #1 schedule risk)
1. `board.py` + `loader.py` (parse single `maps/<name>.txt`: `#.$@*+` + space) + `deadlock.py`.
2. `state.py` (push successors, normalization, canonical key).
3. `heuristic.py` (Manhattan) + `solver.py` (WA* + closed-list TT, `g>stored`).
4. `metrics.py` + `emit.py` (CSV, D6 schema).
5. `validator.py` (replay + UCS optimality oracle) + `tests/` → validate every solve.
6. `cli.py` flags. THEN Phase-2: Hungarian `h` (scalar-ratio arm) + weight sweep (Pareto arm).

## Do NOT
- Import/copy `CSINTSY-sokobot2024/main.py` or its hardcoded Discord token into `src/sokoban/`.
- Chase Java node-count parity (different algorithm by design).
- Substitute best-found-so-far as pseudo-optimal on `w=1`-censored maps (corrupts ratios).

## Blocked on others (do not let these block the port)
- **CSV schema D6** — DRAFT, needs Enzo (harness) + Roan (HP) sign-off. Which counter is the join
  key is **PROVISIONAL** pending Roan's HP engine choice. Log both counters so no re-run is needed.
- **Map suite** (CJ + Enzo) — sized to Manhattan's reach so `w=1` solves under both `h` on every map.
- **`project-proposal.md` research question** still names "symmetry pruning" (now dropped) — CJ to
  reconcile the thesis statement; does not block coding.
