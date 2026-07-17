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
just weighted A* with IDA* cosmetics, so we name it honestly. Keeps a tunable `w` — the flagship
**Sokoban-side** technique (tunable effort/quality tradeoff). **NOT claimed as a cross-domain
"transferable technique":** `w` is A*-specific with no clean HP counterpart (Metropolis temperature
/ NMCS playout depth are loose exploration-pressure analogies, not the same mechanism). The
genuinely transferable thing is the **effort metric** `candidate_states_evaluated` (D6), the
paradigm-neutral join key — not any single algorithmic knob. WA* is a complete systematic search
(matches CONTEXT.md glossary, pairs cleanly vs Roan's B&B). `w=1` = admissible optimal baseline;
`w>1` = bounded-suboptimal tuned runs. tasks.md's "IDA*" was self-imposed; the Korf citation still
backs the weighted-search / bounded-suboptimal story. `algorithm` CSV value = `wastar` (was
`widastar`).

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

**`candidate_states_evaluated` counts every candidate whose quality function was called** — i.e.
increment on each successor you call `heuristic()` on, **including successors later dropped by the
closed list or deadlock prune**. NOT pops-only. This makes the unit a paradigm-neutral "objective/
heuristic evaluation" that lines up with the stochastic side (every proposed HP config whose energy
is computed). Counting pops-only would under-count systematic effort vs stochastic sampling and
bias the cross-domain join. Deadlock/closed-list drops are still *scored* work and must count. (See
D6; needs Roan to confirm HP counts proposals-scored, not accepted-only.)

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
| **`candidate_states_evaluated`** | **PRIMARY** — count of candidates whose quality fn was called (Sokoban: every successor scored by `heuristic()`, incl. ones later pruned by closed-list/deadlock — NOT pops-only; HP: every proposed config whose energy was computed). Paradigm-neutral effort unit; the cross-domain join key |
| `solved` | `1` solved / `0` proven unsolvable (open list emptied) / `cutoff` (stopped early) — or reached-E for HP |
| `cutoff_reason` | NA (solved/unsolvable) \| `budget` (eval cap hit) \| `clock` (wall-clock safety hit) |
| `solution_quality` | push count / final energy |
| `quality_target` | threshold used (optimal / energy E) |
| `wall_clock_ms` | secondary TTS |
| `peak_frontier` | memory proxy — Sokoban: max(open+closed) size (weighted A*); HP: note its own meaning so cross-domain reads aren't taken as inconsistent |
| `git_sha` | provenance |

Ablations = row filters on `weight_w` / `symmetry_pruning`, no schema change per experiment.

**Stopping rule (keeps the primary metric reproducible):** primary stop = **eval budget** — cap
`candidate_states_evaluated` at a fixed `N` shared across the whole map suite and all machines
(config flag). Secondary = a hard **wall-clock safety** (e.g. 300 s) to kill true hangs only.
Wall-clock must NOT be the primary cutoff — it would make eval counts machine-dependent censored
data and poison the cross-domain axis. Log which fired via `cutoff_reason`.

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
  loader.py      # parse single maps/<name>.txt grid -> Board (chars below); no Java map/items split
  validator.py   # PURE-PYTHON solution validator: replay push seq -> assert crates == goals (built wk1, primary bug net)
  cli.py         # run one/many maps; flags: --w, --symmetry, --base-h, --eval-budget N, --timeout (clock safety), --seed
tests/           # TDD; own solved maps + validator as fixtures (NOT Java solutions)
maps/            # shared map suite
# oracle.py      # OPTIONAL/DEFERRED — shell out to Java to confirm solvability + agree on solved/unsolved. Off wk1 critical path.
```
- Successors live in `state.py` (split to `moves.py` only if >~200 lines).
- **`validator.py` is the real safety net** (pure Python, no JVM): replay the emitted push sequence,
  assert all crates land on goals; runs on every solve, catches silent solver bugs all of wk2–3.
- **Java oracle removed from wk1.** Python `w=1` optimality is self-validated (admissible `h` +
  correct `g>stored` predicate ⇒ optimal `Q*`), so no external optimal oracle is needed. A Java
  `oracle.py` is optional/deferred — only adds independent *solvability* confirmation + false-negative
  catch; build it later behind a flag if wanted, never on the schedule-risk week.
- `loader.py` parses the single `.txt` directly. Chars: `#` wall, `.` goal, `$` crate, `@` player,
  `*` crate+goal, `+` player+goal, ` ` floor (from Java `FileReader`/`SokoBot`, fact not decision).

### D8 — Efficiency reporting: **one evals-vs-quality plane; scalar ratio only for the optimality-preserving arm**
Both arms still stop at **first valid solution** (no solver change). But a scalar
`baseline_evals / optimized_evals` is only defensible when quality is held equal — otherwise the
ratio silently folds in a quality gap. So split by technique kind:

- **Symmetry pruning (optimality-preserving)** → both arms reach optimal `Q*` by construction,
  quality equal → **scalar efficiency ratio** `baseline_evals / optimized_evals` is clean and honest.
- **Weight tuning (`w>1`, quality-trading)** → a first-valid-solution ratio is **not** a valid
  efficiency number (worse quality bought the speedup). Report as a **Pareto curve**
  (`candidate_states_evaluated` x, push-count y) sweeping `w`. No scalar ratio for this arm.

Present both on a **single evals-vs-quality plot per map**: symmetry pruning = a point shifted left
at the optimal-quality line (scalar ratio = horizontal distance there, read off the plot); weight
tuning = a curve moving down-left as `w` rises. One figure, no apples-to-oranges, no confound. Data
capture is identical either way (every run already logs evals + `solution_quality`), so **zero
extra runs** — no anytime-search or re-solve machinery needed.

## Validation bar (all choices)
Primary check = **pure-Python `validator.py`**: replay the emitted push sequence, assert all crates
land on goals. Correctness only, NOT node counts. Optimality of `w=1` is self-validated (admissible
`h` + `g>stored`), so `Q*` needs no external oracle. If the Java oracle is ever built, it checks
**solution validity / solvability agreement only**, never counts — even a faithful port wouldn't
match Java counts (`int`-cast ties; Java `PriorityQueue` vs Python `heapq` tie-breaking). Do not
chase count parity as a bug.

## Security (pre-existing — do not propagate)
Discord bot token hardcoded in `CSINTSY-sokobot2024/main.py` ~L176. With the Java oracle removed
from wk1, `src/sokoban/` no longer shells out to Java at all. If a deferred `oracle.py` is later
built, it invokes the Java **solver**, not that file. Do NOT import/copy that file or the token into
`src/sokoban/`. Flag/rotate if that code is ever touched.

## Build order (wk1, port = #1 schedule risk)
1. `board.py` + `loader.py` (parity with Java map format) + `deadlock.py` precompute.
2. `state.py` (push successors, normalization, canonical key).
3. `heuristic.py` (Manhattan sum) + `solver.py` (weighted A* + closed-list TT, `g>stored` predicate).
4. `metrics.py` + `emit.py` (CSV per D6).
5. `validator.py` (pure-Python replay: crates==goals) + `tests/` → validate every solve. (Java oracle deferred, optional.)
6. `cli.py` flags. THEN Phase-2 techniques: symmetry pruning + weight sweep.
Fallback if wk1 slips: keep Java, wrap for CSV emit — metric is language-agnostic, comparison
still holds.

## Open (not blocking port; Phase 2 / other owners)
- Map suite composition (size-graded, count) — CJ + Enzo, for scaling curves.
- Symmetry-pruning detailed design (rotation/reflection + checkerboard parity) — Phase 2.
- Roan's HP engine choice (B&B / NMCS / Metropolis) — 48h fuse, does not block this.
