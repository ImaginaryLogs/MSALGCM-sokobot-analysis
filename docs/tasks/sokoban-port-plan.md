# Sokoban Port Plan — grilled decisions (2026-07-17)

Owner: **CJ**. Produced via `/grill-with-docs`. This is the spec the **next agent** implements
into `MSALGCM-sokobot-analysis/src/sokoban/`. The Java project `CSINTSY-sokobot2024/` is a
**reference, not source of truth** — align to the project plan, do not faithfully copy its
algorithm.

## Factual correction (supersedes HANDOFF)
- `project-specs.md` does **NOT** cite IDA* or Korf — it is the generic course rubric.
  The IDA* requirement traces only to `tasks.md` (self-imposed) + CJ's Korf lit-review paper.
  It was revisable, and we revised it (see D1).
- The Java solver is **greedy best-first**, NOT A*: `SokoStateComparator` sorts purely by
  `SokoState.getCost` = product of 3 weighted **non-admissible** heuristics (`moveCount` folded
  in multiplicatively). No `f = g + h`. Satisficing, not optimal. Do not port this as-is.

## Locked decisions

### D1 — Search architecture: **Weighted A\* with closed list (`f = g + w·h`)**
Chosen over faithful GBFS port, pure admissible IDA*, and TT-backed IDA*. **NOT literal IDA***:
Sokoban has massive transposition (many push orders → same crate config), so pure O(depth) IDA*
is intractable and a closed list is mandatory — a persistent closed list + iterative deepening is
just weighted A* with IDA* cosmetics, so we name it honestly. Keeps a tunable `w` (preserves
weight-tuning as the flagship transferable technique), is a complete systematic search (matches
CONTEXT.md glossary, pairs cleanly vs Roan's B&B). `w=1` = admissible optimal baseline; `w>1` =
bounded-suboptimal tuned runs. tasks.md's "IDA*" was self-imposed; the Korf citation still backs
the weighted-search / bounded-suboptimal story. `algorithm` CSV value = `wastar` (was `widastar`).

### D2 — Base heuristic `h`: **greedy Manhattan sum**, behind a swappable `heuristic()` seam
Each crate to nearest goal, summed; ignores walls + collisions; admissible. ~10 lines, ships
week 1. **Hungarian min-cost matching** is a noted later upgrade — same signature, becomes an
extra ablation row if ahead. (Java's multiplicative product is non-admissible — do NOT reuse it
as `h`.)

### D3 — Move granularity: **crate-push (macro) level**
State = crate config + player's **reachable region, normalized** (flood-fill; player collapsed to
canonical min-index cell of its region). Successors = **legal pushes only**. `g` = push count.
NOT player-step (Java's model). Makes the primary metric defensible, pairs with B&B, and `h`
(crate-goal distance) is naturally a push lower bound matching `g` units.

### D4 — Deadlock pruning: **static dead-squares in baseline, held constant**
Precompute cells from which no crate can ever reach a goal (reverse-pull BFS from goals); prune
any push into them. It is **soundness infrastructure, not a studied technique** → identical in
baseline and optimized arms so it never contaminates the ablation. **Freeze + group/corral
deadlocks deferred to stretch**; if added, add to BOTH arms.

### D5 — Dedup: **closed list / transposition table (state → min `g`)**
Skip revisit only when `g > stored` (strict — dominated paths pruned, the min-`g` path is always
kept). **NOT `≥`** — `≥` would wrongly drop equal-cost optimal paths. This is the "dedup" the
baseline is defined to include; constant across both arms, and it is the closed list weighted A*
(D1) requires — Sokoban's transposition makes it mandatory, not optional. **State key = sorted
crate-cell tuple + normalized player cell** (also the serial identity). Replaces Java's Base64
bit-packing with a plain Python tuple hash. Memory is O(distinct states) by design (captured by
`peak_frontier`); if a map OOMs, switch to a bounded/hashed TT (config flag, not redesign).
`candidate_states_evaluated` = states expanded (popped + closed); no re-expansion ambiguity under
weighted A*.

### D6 — Shared CSV schema (DRAFT — needs Enzo harness sign-off + Roan HP confirm)
One row per run. NA where a column doesn't apply.

| Column | Meaning |
|---|---|
| `run_id` | unique |
| `domain` | `sokoban`\|`hp` |
| `instance_id` | map name / protein id |
| `instance_size` | cells / chain length |
| `algorithm` | `wastar`\|`bnb`\|`nmcs`\|`metropolis` |
| `weight_w` | tuning param (NA for stochastic) |
| `symmetry_pruning` | 0/1 |
| `seed` | RNG seed (NA/fixed for systematic) |
| **`candidate_states_evaluated`** | **PRIMARY** — nodes expanded / samples drawn; the cross-domain join key |
| `solved` | 1/0/timeout (or reached-E for HP) |
| `solution_quality` | push count / final energy |
| `quality_target` | threshold used (optimal / energy E) |
| `wall_clock_ms` | secondary TTS |
| `peak_frontier` | memory proxy — Sokoban: max(open+closed) size (weighted A*); HP: note its own meaning so cross-domain reads aren't taken as inconsistent |
| `git_sha` | provenance |

Ablations = row filters on `weight_w` / `symmetry_pruning`, no schema change per experiment.

### D7 — Module layout for `src/sokoban/` (deep modules, agentic-navigable)
```
src/sokoban/
  board.py       # static map: walls, goals, passability, dead-square precompute
  state.py       # push-state: crates + player region, normalization, canonical key, legal-push successors
  heuristic.py   # base-h seam (Manhattan sum now; Hungarian later — same signature)
  deadlock.py    # static dead-square reverse-pull BFS (constant infra)
  solver.py      # weighted A*: f=g+w·h, closed-list TT (skip on g>stored), symmetry hook
  symmetry.py    # symmetry pruning (technique, on/off flag)
  metrics.py     # counters: candidate_states_evaluated, peak_frontier, timers
  emit.py        # CSV row writer — shared schema (D6)
  loader.py      # headless map file -> Board (MUST match Java FileReader/MapData format for oracle parity)
  oracle.py      # run Java solver, diff solution validity
  cli.py         # run one/many maps; flags: --w, --symmetry, --base-h, --timeout, --seed
tests/           # TDD; Java oracle solutions as fixtures
maps/            # shared map suite
```
- Successors live in `state.py` (split to `moves.py` only if >~200 lines).
- `oracle.py` **is built** (cheap, catches silent solver bugs all of wk2–3).
- `loader.py` map format = pin from Java `FileReader`/`MapData` at build time (fact, not decision).

### D8 — Efficiency-ratio quality target: **first valid solution**
Ratio = `baseline_evals / optimized_evals` to **first valid solution**; both arms stop at first
solve. `solution_quality` (push count) reported alongside as the speed/quality tradeoff axis —
the textbook WA* framing (`w` trades quality for speed). Symmetry pruning is optimality-preserving
→ its ratio is a pure win at equal quality; weight-tuning trades quality for evals. Clean paper
contrast. Upgrade to a Pareto plot in wk3 if ahead (data already captured).

## Oracle validation bar (all choices)
Different algorithm by design → oracle checks **solution correctness only** (does Python's
solution actually solve the map), NOT node counts. Even a faithful port wouldn't match Java
counts (`int`-cast ties; Java `PriorityQueue` vs Python `heapq` tie-breaking). Do not chase
count parity as a bug.

## Security (pre-existing — do not propagate)
Discord bot token hardcoded in `CSINTSY-sokobot2024/main.py` ~L176. `oracle.py` shells out to the
Java **solver**, which is not that file. Do NOT import/copy that file or the token into
`src/sokoban/`. Flag/rotate if that code is ever touched.

## Build order (wk1, port = #1 schedule risk)
1. `board.py` + `loader.py` (parity with Java map format) + `deadlock.py` precompute.
2. `state.py` (push successors, normalization, canonical key).
3. `heuristic.py` (Manhattan sum) + `solver.py` (WIDA* + TT).
4. `metrics.py` + `emit.py` (CSV per D6).
5. `oracle.py` + `tests/` (Java solutions as fixtures) → validate.
6. `cli.py` flags. THEN Phase-2 techniques: symmetry pruning + weight sweep.
Fallback if wk1 slips: keep Java, wrap for CSV emit — metric is language-agnostic, comparison
still holds.

## Open (not blocking port; Phase 2 / other owners)
- Map suite composition (size-graded, count) — CJ + Enzo, for scaling curves.
- Symmetry-pruning detailed design (rotation/reflection + checkerboard parity) — Phase 2.
- Roan's HP engine choice (B&B / NMCS / Metropolis) — 48h fuse, does not block this.
