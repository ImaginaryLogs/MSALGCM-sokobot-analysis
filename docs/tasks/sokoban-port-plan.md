# Sokoban Port Plan — grilled decisions (2026-07-17)

Owner: **CJ**. Produced via `/grill-with-docs`. This is the spec the **next agent** implements
into `MSALGCM-sokobot-analysis/src/sokoban/`. The Java project `CSINTSY-sokobot2024/` is a
**reference, not source of truth** — align to the project plan, do not faithfully copy its
algorithm.

## Factual correction (supersedes HANDOFF)

- `project-specs.md` does **NOT** cite IDA* or Korf — it is the generic course rubric.
  The IDA* requirement traces only to `tasks.md` (self-imposed) + CJ's Korf lit-review paper.
  It was revisable, and we revised it (see D1).
- The Java solver is **greedy best-first**, NOT A\*: `SokoStateComparator` sorts purely by
  `SokoState.getCost` = product of 3 weighted **non-admissible** heuristics (`moveCount` folded
  in multiplicatively). No `f = g + h`. Satisficing, not optimal. Do not port this as-is.

## Locked decisions

### D1 — Search architecture: **Weighted A\* with closed list (`f = g + w·h`)**

Chosen over faithful GBFS port, pure admissible IDA*, and TT-backed IDA*. **NOT literal IDA\***:
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
week 1. **Hungarian min-cost matching** = same-signature upgrade and a **committed Phase-2 build**:
it is the strong-`h` half of the optimality-preserving experimental arm (Manhattan vs Hungarian @
`w=1`, D8), so it gets built regardless. It _also_ doubles as the anchor rescue lever (tighter bound
⇒ fewer evals ⇒ `w=1` finishes) if a map slips past Manhattan's reach — but suite sizing (below)
makes that a contingency, not the reason to build it. (Java's multiplicative product is
non-admissible — do NOT reuse it as `h`.)

**Baseline-anchor rule (`w=1` must actually reach optimal `Q*`):** the Pareto plot's optimal-quality
line and the heuristic-strength scalar ratio (D8) both require `w=1` to prove optimal on a map. If `w=1` hits
the eval budget first:

- **exclude** that map from anchored analysis, logged as `w=1`-censored (`solved=cutoff`). Do NOT
  substitute best-found-so-far as pseudo-optimal — it isn't proven optimal and would silently
  corrupt every ratio on that map.
- **Suite is sized to Manhattan's reach** (governing rule): both `h` solve _every_ suite map at
  `w=1`, so the heuristic-strength scalar ratio (D8) is defined throughout. Hungarian's rescue role
  is a **contingency**, not a suite-sizing target — it fires only if a map assumed within Manhattan's
  reach turns out censored. Maps where Manhattan is genuinely censored have no `weak_h` eval count,
  so they cannot enter the scalar ratio anyway; report those separately as anecdote if wanted, never
  fold into the headline ratio.

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
baseline is defined to include; constant across both arms, and it is the closed list weighted A\*
(D1) requires — Sokoban's transposition makes it mandatory, not optional. **State key = sorted
crate-cell tuple + normalized player cell** (also the serial identity). Replaces Java's Base64
bit-packing with a plain Python tuple hash. Memory is O(distinct states) by design (captured by
`peak_frontier`); if a map OOMs, switch to a bounded/hashed TT (config flag, not redesign).

**Log BOTH counters — do not collapse them (cheap, `metrics.py` already has the infra):**

- `nodes_expanded` — states popped + closed (the prior locked value).
- `candidates_scored` — every successor you call `heuristic()` on, **including ones later dropped by
  closed list or deadlock prune** (NOT pops-only).

**Which one is the cross-domain join key is PROVISIONAL** — it depends on Roan's unchosen HP engine
(D6 unsigned): a Metropolis proposal = 1 energy eval (lines up with `candidates_scored`); an NMCS
sample = a nested playout = _many_ evals; B&B = node expansions (lines up with `nodes_expanded`).
Capturing both now means no re-run whichever way Roan lands. Populate `candidate_states_evaluated`
(D6) from whichever counter the signed schema selects; default `candidates_scored` pending sign-off.

### D6 — Shared CSV schema (DRAFT — needs Enzo harness sign-off + Roan HP confirm)

One row per run. NA where a column doesn't apply.

| Column                           | Meaning                                                                                                                                                                                                                                                                                                                                                 |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `run_id`                         | unique                                                                                                                                                                                                                                                                                                                                                  |
| `domain`                         | `sokoban`\|`hp`                                                                                                                                                                                                                                                                                                                                         |
| `instance_id`                    | map name / protein id                                                                                                                                                                                                                                                                                                                                   |
| `instance_size`                  | **difficulty axis** — Sokoban: **crate count** (combinatorial driver, parallels HP chain length); HP: chain length                                                                                                                                                                                                                                      |
| `grid_cells`                     | optional secondary — Sokoban free/total cell count (NA for HP); geometry context, NOT the headline size                                                                                                                                                                                                                                                 |
| `algorithm`                      | `wastar`\|`bnb`\|`nmcs`\|`metropolis`                                                                                                                                                                                                                                                                                                                   |
| `weight_w`                       | tuning param (NA for stochastic)                                                                                                                                                                                                                                                                                                                        |
| `base_h`                         | `manhattan`\|`hungarian` — the optimality-preserving arm (both at `w=1`); replaces dropped `symmetry_pruning`                                                                                                                                                                                                                                           |
| `seed`                           | RNG seed (NA/fixed for systematic)                                                                                                                                                                                                                                                                                                                      |
| **`candidate_states_evaluated`** | **PRIMARY (join key PROVISIONAL — pending Roan/D6 sign-off)** — populated from whichever Sokoban counter the signed schema picks; default `candidates_scored`. See D5: log BOTH `nodes_expanded` and `candidates_scored`, because HP engine choice (Metropolis 1-eval/proposal vs NMCS nested playout vs B&B expansions) determines which is comparable |
| `nodes_expanded`                 | Sokoban: states popped+closed (raw, always logged)                                                                                                                                                                                                                                                                                                      |
| `candidates_scored`              | Sokoban: every successor scored by `heuristic()`, incl. closed/deadlock-pruned (raw, always logged)                                                                                                                                                                                                                                                     |
| `solved`                         | `1` solved / `0` proven unsolvable (open list emptied) / `cutoff` (stopped early) — or reached-E for HP                                                                                                                                                                                                                                                 |
| `cutoff_reason`                  | NA (solved/unsolvable) \| `budget` (eval cap hit) \| `clock` (wall-clock safety hit)                                                                                                                                                                                                                                                                    |
| `solution_quality`               | push count / final energy                                                                                                                                                                                                                                                                                                                               |
| `quality_target`                 | threshold used (optimal / energy E)                                                                                                                                                                                                                                                                                                                     |
| `wall_clock_ms`                  | secondary TTS                                                                                                                                                                                                                                                                                                                                           |
| `peak_frontier`                  | memory proxy — Sokoban: max(open+closed) size (weighted A\*); HP: note its own meaning so cross-domain reads aren't taken as inconsistent                                                                                                                                                                                                               |
| `git_sha`                        | provenance                                                                                                                                                                                                                                                                                                                                              |

Ablations = row filters on `weight_w` / `base_h`, no schema change per experiment.

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
  solver.py      # weighted A*: f=g+w·h, closed-list TT (skip on g>stored)
  metrics.py     # counters: nodes_expanded + candidates_scored (both, see D5), peak_frontier, timers
  emit.py        # CSV row writer — shared schema (D6)
  loader.py      # parse single maps/<name>.txt grid -> Board (chars below); no Java map/items split
  validator.py   # PURE-PYTHON: (a) replay push seq -> assert crates==goals (validity); (b) small-map optimality oracle: uniform-cost BFS over push graph, assert w=1 Q* == BFS optimal
  cli.py         # run one/many maps; flags: --w, --base-h {manhattan|hungarian}, --eval-budget N, --timeout (clock safety), --seed
# symmetry.py    # DROPPED from headline — optional stretch only (see D8); board symmetry rare, ~null ratios
tests/           # TDD; own solved maps + validator as fixtures (NOT Java solutions)
maps/            # shared map suite
# oracle.py      # OPTIONAL/DEFERRED — shell out to Java to confirm solvability + agree on solved/unsolved. Off wk1 critical path.
```

- Successors live in `state.py` (split to `moves.py` only if >~200 lines).
- **`validator.py` is the real safety net** (pure Python, no JVM): replay the emitted push sequence,
  assert all crates land on goals; runs on every solve, catches silent solver bugs all of wk2–3.
- **Java oracle removed from wk1** — but NOT because optimality goes unchecked. Optimality is
  verified by the in-Python **small-map UCS oracle in `validator.py`** (assert `w=1` `Q*` == BFS
  optimal), which is strictly stronger than the greedy (non-optimal) Java solver for this. "Admissible
  `h` + `g>stored`" argues the _algorithm_ is optimal; the UCS oracle catches an _implementation_ bug
  (e.g. `g≥stored`). A Java `oracle.py` is optional/deferred — only adds independent _solvability_
  confirmation + false-negative catch; build later behind a flag, never on the schedule-risk week.
- `loader.py` parses the single `.txt` directly. Chars: `#` wall, `.` goal, `$` crate, `@` player,
  `*` crate+goal, `+` player+goal, ` ` floor (from Java `FileReader`/`SokoBot`, fact not decision).

### D8 — Efficiency reporting: **one evals-vs-quality plane; scalar ratio only for the optimality-preserving arm**

Both arms still stop at **first valid solution** (no solver change). But a scalar
`baseline_evals / optimized_evals` is only defensible when quality is held equal — otherwise the
ratio silently folds in a quality gap. So split by technique kind:

- **Heuristic strength (optimality-preserving)** → Manhattan (weak `h`) vs Hungarian (strong `h`),
  both `w=1`; both prove optimal `Q*`, quality equal by construction → **scalar efficiency ratio**
  `weak_h_evals / strong_h_evals` is clean and honest, and fires on _every_ solved map (no
  null-result trap). This is the second experimental arm.
- **Weight tuning (`w>1`, quality-trading)** → a first-valid-solution ratio is **not** a valid
  efficiency number (worse quality bought the speedup). Report as a **Pareto curve**
  (`candidate_states_evaluated` x, push-count y) sweeping `w`. No scalar ratio for this arm.

Present both on a **single evals-vs-quality plot per map**: heuristic strength = a point shifted
left at the optimal-quality line (scalar ratio = horizontal distance there, read off the plot);
weight tuning = a curve moving down-left as `w` rises. One figure, no apples-to-oranges, no
confound. Data capture is identical either way (every run already logs evals + `solution_quality`),
so **zero extra runs** — no anytime-search or re-solve machinery needed.

(**Board-symmetry pruning is dropped** as a headline technique — rotation/reflection symmetry is
rare in real Sokoban maps, so it fires almost never and yields ~1.0 null ratios. Kept only as an
optional stretch if a deliberately-symmetric map sub-suite is ever built.)

## Validation bar (all choices)

Primary check = **pure-Python `validator.py`**: replay the emitted push sequence, assert all crates
land on goals (validity), NOT node counts. **Optimality is load-bearing** (it anchors both the
scalar ratio and the Pareto optimal-quality line, D8) and is **NOT** established by "admissible `h` +
`g>stored`" alone — that argues the _algorithm_ is optimal, not that the _implementation_ is (the
`g>stored` vs `g≥stored` bug, D5, yields valid-but-suboptimal results the crates==goals check passes
blind). So `validator.py` also runs a **small-map optimality oracle**: brute-force uniform-cost BFS
over the push graph, assert `w=1` `Q*` equals BFS optimal on the small fixtures. This is what makes
"drop the Java oracle" _correct_, not merely cheaper — and it's strictly stronger than the greedy
(non-optimal) Java solver for checking `Q*`. If a Java oracle is ever built, it checks
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
3. `heuristic.py` (Manhattan sum) + `solver.py` (weighted A\* + closed-list TT, `g>stored` predicate).
4. `metrics.py` + `emit.py` (CSV per D6).
5. `validator.py` (replay: crates==goals; + small-map UCS optimality oracle asserting `w=1`==BFS `Q*`) + `tests/` → validate every solve. (Java oracle deferred, optional.)
6. `cli.py` flags. THEN Phase-2 experiments: Hungarian `h` (optimality-preserving arm) + weight sweep (Pareto arm).
   Fallback if wk1 slips: keep Java, wrap for CSV emit — metric is language-agnostic, comparison
   still holds.

## Open (not blocking port; Phase 2 / other owners)

- Map suite composition (crate-count-graded, count) — CJ + Enzo, for scaling curves; **sized to
  Manhattan's reach** so `w=1` reaches optimal under _both_ `h` on every suite map (baseline-anchor
  - heuristic-strength arm, D2/D8). Hungarian rescue = contingency, not a sizing target.
- Roan's HP engine choice (B&B / NMCS / Metropolis) — 48h fuse, does not block this.
- (Dropped) Board-symmetry pruning — optional stretch only; build a symmetric-map sub-suite first
  if ever revived (D8).
