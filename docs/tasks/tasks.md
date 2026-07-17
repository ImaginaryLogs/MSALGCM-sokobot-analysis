# Tasks

Owners: **CJ** = Sokoban · **Roan** = HP · **Enzo** = lit review + harness + paper.
Dates: Lit Review due **Jul 24** (present Jul 27) · Final Paper **Aug 7** (present Aug 10). Today Jul 17.

## Phase 1: Building (wk1, Jul 17–24)
- [ ] Sokoban — **CJ**
  - [ ] Port CSINTSY solver + headless map loader to `src/sokoban/` (Python). **Skip GUI/visualizer** — not in paper.
  - [ ] Convert A*-like search → IDA*.
  - [ ] Node/eval instrumentation → CSV.
  - [ ] Keep Java solver as **reference oracle** (diff solutions + node counts to validate port).
  - [ ] Fallback if wk1 slips: keep Java, wrap for data (eval metric is language-agnostic).
- [ ] HP Lattice — **Roan**
  - [x] Main Driver / Game Engine (existing Metropolis MC)
  - [ ] **ENGINE DECISION (48h fuse, critical path):** B&B chain-growth (thesis-clean) · NMCS (Roucairol 2023, keeps MC flavor + a search tree) · plain Metropolis (on-theme via Category-D Simulated Annealing; weakest shared metric).
  - [ ] Build chosen solver; reuse `geometry.py`/`validation.py`/lattice utils regardless.
  - [ ] Finish `equivalence.md` Layer 6.
  - [ ] Eval instrumentation → CSV (same schema as Sokoban).
- [ ] Shared harness — **Enzo**
  - [ ] CSV schema (see Measurement below). Adapt CSINTSY `tester.py` + `analyzer.ipynb`, don't build from zero.
  - [ ] Lit Review doc (due Jul 24) — see split below.

## Phase 2: Techniques + test sets (wk2, Jul 24–31)
- [ ] Commit techniques (each with ablation on/off flag):
  - [ ] **Heuristic weight tuning** (CJ Sokoban / Roan HP) — low risk, transfers.
  - [ ] **Symmetry pruning** (CJ / Roan) — rotation/reflection + parity; transfers via checkerboard parity.
  - [ ] *Stretch:* macro-graph tunnel abstraction (Botea) — only if ahead; weakest transfer.
- [ ] Test sets: Sokoban map suite (CJ) · ~100 generated proteins (Roan/Enzo).
- [ ] Paper skeleton + Methods + related-work drafted early (Enzo) — writable before results exist.

## Phase 3: Data (wk3, Jul 31–Aug 7)
- [ ] Feature freeze. Full runs both domains → CSV.
- [ ] Analysis notebook: efficiency ratios, per-technique ablation, scaling curves.

## Phase 4: Paper
- [ ] Aug 7 submit. Aug 10 present.

## Measurement (locked)
- **Primary metric:** candidate states evaluated to reach quality threshold — = nodes expanded (IDA*/B&B/NMCS) **and** samples drawn (Metropolis). Paradigm-neutral.
- **Baseline:** vanilla solver — dedup only, unit/default weights, no symmetry, no macro.
- **Efficiency ratio:** baseline_evals / optimized_evals. Ablate each technique.
- **Secondary:** wall-clock TTS, peak frontier size (memory), solved/timeout flag.
- Systematic = "evals to solved/optimal"; MC = "evals to reach energy E". Comparable as work-to-target.

## Lit Review split (due Jul 24)
Each builder annotates their own 4 (they're the build sources); Enzo sources missing textbooks/conf pubs + writes synthesis.
- **CJ:** Junghanns 2001, Botea 2003, Korf 2001, Culberson 1997.
- **Roan:** Lau-Dill 1989, Berger-Leighton 1998, Crescenzi 1998, Roucairol 2023.
- **Enzo:** 2 textbooks + 2 conference pubs (missing) + write the review; = paper's related-work early.
