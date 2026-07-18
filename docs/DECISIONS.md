# Decisions

Append-only dated log of resolved project decisions. Single source of truth — `HANDOFF.md`,
`STATUS.md`, and `docs/plans/*.md` link here instead of repeating content. Big
algorithm/architecture/module-boundary calls get their own `docs/adr/NNNN-title.md`; this file
links out to those and keeps a one-line summary.

## 2026-07-17

1. **Sokoban port target:** Python, into `src/sokoban/`. Solver + headless loader + data emit
   only — no GUI. Java oracle removed from wk1, replaced by pure-Python `validator.py` (validity
   replay + small-map UCS optimality oracle asserting `w=1` == BFS `Q*`); Java oracle
   optional/deferred. Java-wrap remains the fallback if wk1 slips.
2. **Technique scope (revised via grill):** two headline arms — **heuristic weight tuning**
   (`w>1`, quality-trading → Pareto curve) + **heuristic strength** (Manhattan vs Hungarian `h` @
   `w=1`, optimality-preserving → scalar ratio). Symmetry pruning **dropped** as headline (board
   symmetry rare in real maps → ~null ratios; optional stretch only). Macro-graph tunnel
   abstraction remains stretch.
3. **Task split:** CJ = Sokoban, Roan = HP, Enzo = lit review + shared harness + paper assembly.
4. **Measurement:** paradigm-neutral effort unit. Log BOTH `nodes_expanded` and
   `candidates_scored` — cross-domain join-key choice **provisional**, pending Roan's HP engine
   (Metropolis 1-eval/proposal ↔ `candidates_scored`; NMCS nested playout / B&B expansions ↔
   `nodes_expanded`). Efficiency reporting split: scalar ratio only for the optimality-preserving
   arm (equal quality), Pareto curve for the weighted arm (no scalar). Primary stop = eval budget
   `N` (reproducible); wall-clock = hang-safety only, `cutoff_reason` logged. `instance_size` =
   crate count. Secondary metrics: TTS, peak frontier size.
5. **Lit review split:** distributed by domain — each builder annotates their own 4 papers, Enzo
   sources the missing textbooks/conf pubs and writes the synthesis. Due Jul 24.
6. **Sokoban port architecture:** Weighted A* + closed list, `f=g+w·h`, closed-list skip predicate
   is strict `g > stored`. Full rationale: [ADR 0001](adr/0001-sokoban-search-algorithm.md). Full
   build spec: [`docs/specs/sokoban-port-plan.md`](specs/sokoban-port-plan.md).

## 2026-07-18

7. **HP engine confirmed: B&B chain-growth.** Roan resolved the 48h-fuse ENGINE DECISION. Full
   rationale: [ADR 0002](adr/0002-hp-engine-bnb.md).
8. **Cross-domain join key locked: `nodes_expanded`.** No longer provisional (was pending the HP
   engine choice, decision 4). B&B expansions map to `nodes_expanded`, not `candidates_scored`.
   `candidate_states_evaluated` (D6 schema) now populates from `nodes_expanded` by default.
   `candidates_scored` still logged (cheap, D5) as a secondary counter, not the join key.

9. **Phase-2 experiment plan locked** (grill session, full record in git history of
   `docs/plans/sokoban-phase2-experiments-plan.md`, deleted on resolution per docs-management
   rule):
   - **Map suite fixed: 155 maps, not 19.** `build_map_suite.py` only ever scanned
     `maps/_all/` — `CSINTSY-sokobot2024/maps/sokoban-info/` (2716 classic XSokoban-format maps,
     loader-compatible) was never fed in. Sampled every 10th file (272 candidates) into `_all/`,
     reran the D2 filter (timeout raised 300s→60s per-map for the rerun's practicality) → 155
     suite-eligible maps, crate counts 1–11+. `EXCLUDED.md` regenerated (152 excluded).
   - **D6 CSV schema still DRAFT** (pending Enzo sign-off) — running real data against it anyway;
     Sokoban side is deterministic so a re-run is cheap if columns shift.
   - **Eval budget locked: `N=2,000,000`** (candidate_states_evaluated / `nodes_expanded` join
     key). Set from a full-155-map sweep at `w=1` manhattan: observed max `candidates_scored`
     was 975,695 — `N` is ~2x headroom above that, not the old untested `1,000,000` CLI default.
   - **Arm A (heuristic strength):** manhattan vs hungarian, `w=1` fixed, scalar ratio (D8) —
     code-ready, no design left.
   - **Arm B (weight tuning):** manhattan **only** (no cross with hungarian — keeps the two arms
     independent variables; a hungarian×weight cross is optional stretch). Weight grid:
     `{1.0, 1.25, 1.5, 2.0, 3.0, 5.0}`, dense near 1.0 where quality degrades fastest. Revisit
     grid after CJ's Korf/Junghanns lit-review annotations if their bounded-suboptimal values
     suggest otherwise.
   - **Batch runner:** `scripts/run_experiments.py` — in-process (no subprocess-per-cell),
     imports `solver.py`/`emit.py` directly, one shared CSV. `cli.py` stays the single-run/debug
     entry point. The `(manhattan, w=1.0)` cell is shared by both arms and only run once.
     Smoke-tested on 2 maps × 7 configs (2026-07-18) — dedup and weight/heuristic behavior
     verified correct; full 155-map run not yet executed (separate data-collection step).

## Deferred

(none)

## Framing notes

- Existing Metropolis MC code is on-topic (SA is a Category-D example), not dead weight.
- `docs/equivalence/` predicts weak transfer ("Level 2, graphs fundamentally different") — a
  negative transfer result is a valid, publishable finding. Don't force a positive-transfer story.
