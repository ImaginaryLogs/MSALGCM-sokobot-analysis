# Tasks

Owners: **CJ** = Sokoban · **Roan** = HP · **Enzo** = lit review + harness + paper.
Dates: Lit Review due **Jul 24** (present Jul 27) · Final Paper **Aug 7** (present Aug 10). Today Jul 17.

## Phase 1: Building (wk1, Jul 17–24)

- [ ] Sokoban — **CJ**
  - [ ] Port CSINTSY solver + headless map loader to `src/sokoban/` (Python). **Skip GUI/visualizer** — not in paper. Full spec: **`docs/specs/sokoban-port-plan.md`**.
  - [ ] Implement **Weighted A\* + closed list** (`f=g+w·h`, skip on `g>stored`) — NOT IDA\* (Sokoban transposition makes a closed list mandatory).
  - [ ] Instrumentation → CSV: log BOTH `nodes_expanded` + `candidates_scored`; eval-budget stop + `cutoff_reason`.
  - [ ] **Pure-Python `validator.py`** (validity replay + small-map UCS optimality oracle: assert `w=1`==BFS `Q*`). Java oracle removed from wk1 (optional/deferred).
  - [ ] Fallback if wk1 slips: keep Java, wrap for data (eval metric is language-agnostic).
- [ ] HP Lattice — **Roan**
  - [x] Main Driver / Game Engine (existing Metropolis MC)
  - [x] **ENGINE DECISION:** B&B chain-growth confirmed 2026-07-18. See [ADR 0002](docs/adr/0002-hp-engine-bnb.md).
  - [ ] Build chosen solver; reuse `geometry.py`/`validation.py`/lattice utils regardless.
  - [ ] Finish `equivalence.md` Layer 6.
  - [ ] Eval instrumentation → CSV (same schema as Sokoban).
- [ ] Shared harness — **Enzo**
  - [ ] CSV schema (see Measurement below). Adapt CSINTSY `tester.py` + `analyzer.ipynb`, don't build from zero.
  - [ ] Lit Review doc (due Jul 24) — see split below.

## Phase 2: Techniques + test sets (wk2, Jul 24–31)

- [ ] Commit techniques (each with ablation flag):
  - [ ] **Heuristic weight tuning** (CJ Sokoban / Roan HP) — `w>1`, quality-trading → **Pareto curve** (no scalar ratio).
  - [x] **Heuristic strength** (CJ) — Manhattan vs **Hungarian** `h` @ `w=1`, optimality-preserving → **scalar efficiency ratio**. Replaces symmetry pruning. `hungarian()` via scipy `linear_sum_assignment`, same signature as `manhattan()`. Implemented, tested.
  - [ ] _Dropped:_ symmetry pruning — board symmetry rare → ~null ratios; optional stretch only.
  - [ ] _Stretch:_ macro-graph tunnel abstraction (Botea) — only if ahead; weakest transfer.
- [x] Test sets: Sokoban map suite (CJ) — 155 maps sourced from `CSINTSY-sokobot2024/maps/` (originals + 1-in-10 sample of `sokoban-info/`'s 2716 XSokoban maps), filtered by w=1 Manhattan solvability (`scripts/build_map_suite.py`, D2 baseline-anchor rule); crate counts 1-11+; 152 excluded/logged in `src/sokoban/maps/EXCLUDED.md` · ~100 generated proteins (Roan/Enzo, still open).
- [x] Batch runner (CJ) — `scripts/run_experiments.py`: Arm A (manhattan vs hungarian, w=1) + Arm B (manhattan, weight grid) in-process, one shared D6 CSV. Eval budget `N=2,000,000` locked from full-suite sweep. Design: `docs/DECISIONS.md` #9. Smoke-tested; full 155-map run not yet executed.
- [ ] Paper skeleton + Methods + related-work drafted early (Enzo) — writable before results exist.

## Phase 3: Data (wk3, Jul 31–Aug 7)

- [ ] Feature freeze. Full runs both domains → CSV.
- [ ] Analysis notebook: efficiency ratios, per-technique ablation, scaling curves.

## Phase 4: Paper

- [ ] Aug 7 submit. Aug 10 present.

## Measurement (revised via grill — see `docs/specs/sokoban-port-plan.md` D5/D6/D8)

- **Primary metric:** candidate states evaluated. Sokoban logs BOTH `nodes_expanded` + `candidates_scored`; cross-domain join key **LOCKED** to `nodes_expanded` (B&B confirmed 2026-07-18, [ADR 0002](docs/adr/0002-hp-engine-bnb.md)). Paradigm-neutral.
- **Baseline:** vanilla solver — dedup (closed list) only, `w=1`, Manhattan `h`.
- **Efficiency reporting:** scalar ratio **only** for the optimality-preserving arm (equal quality); weighted arm → **Pareto curve** (evals vs push-count). One evals-vs-quality plot per map.
- **Stopping:** primary = eval budget `N` (reproducible across machines); wall-clock = hang-safety only; log `cutoff_reason`.
- **`instance_size`** = crate count (Sokoban difficulty axis) / chain length (HP).
- **Secondary:** wall-clock TTS, peak frontier size (memory), `solved` (1/0/cutoff).
- **`w=1` optimality is verified** (small-map UCS oracle), not assumed. Systematic = "evals to solved/optimal"; MC = "evals to reach energy E". Comparable as work-to-target.

## Lit Review split (due Jul 24)

Each builder annotates their own 4 (they're the build sources); Enzo sources missing textbooks/conf pubs + writes synthesis.

- **CJ:** Junghanns 2001, Botea 2003, Korf 2001, Culberson 1997.
- **Roan:** Lau-Dill 1989, Berger-Leighton 1998, Crescenzi 1998, Roucairol 2023.
- **Enzo:** 2 textbooks + 2 conference pubs (missing) + write the review; = paper's related-work early.
