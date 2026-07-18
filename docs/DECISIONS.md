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

## Deferred

(none)

## Framing notes

- Existing Metropolis MC code is on-topic (SA is a Category-D example), not dead weight.
- `docs/equivalence/` predicts weak transfer ("Level 2, graphs fundamentally different") — a
  negative transfer result is a valid, publishable finding. Don't force a positive-transfer story.
