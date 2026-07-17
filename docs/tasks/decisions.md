# Planning Decisions & Handoff — 2026-07-17

## Resolved

1. **Sokoban port target:** Python (into `src/sokoban/`). Solver + headless loader + data emit only; no GUI. **Java oracle removed from wk1** — replaced by pure-Python `validator.py` (validity replay + small-map UCS optimality oracle asserting `w=1`==BFS `Q*`); Java oracle optional/deferred. Java-wrap still the fallback if wk1 slips.
2. **Technique scope (revised via grill):** 2 headline arms — **heuristic weight tuning** (`w>1`, quality-trading → Pareto curve) + **heuristic strength** (Manhattan vs Hungarian `h` @ `w=1`, optimality-preserving → scalar ratio). **Symmetry pruning DROPPED** (board symmetry rare → ~null ratios; optional stretch only). Macro-graph tunnel abstraction still stretch.
3. **Task split:** CJ=Sokoban, Roan=HP, Enzo=lit review + shared harness + paper assembly.
4. **Measurement (revised):** paradigm-neutral effort unit; **log BOTH `nodes_expanded` + `candidates_scored`** — join-key choice **PROVISIONAL** pending Roan's HP engine (Metropolis 1-eval/proposal ↔ `candidates_scored`; NMCS nested playout / B&B expansions ↔ `nodes_expanded`). Efficiency reporting **split**: scalar ratio only for the optimality-preserving arm (equal quality), **Pareto curve** for the weighted arm (no scalar). Primary stop = **eval budget `N`** (reproducible), wall-clock = hang-safety only; `cutoff_reason` logged. `instance_size` = crate count. Secondary TTS + peak frontier.
5. **Lit Review:** distributed by domain (each builder annotates their 4 papers), Enzo sources missing sources + synthesizes. Due Jul 24.

6. **Sokoban port architecture (grilled, revised 2026-07-17):** Weighted A* + closed list (`f=g+w·h`, skip on `g>stored`; NOT IDA* — Sokoban transposition makes a closed list mandatory), greedy Manhattan base-`h` (swappable seam; **Hungarian = committed Phase-2 build**, the strong-`h` arm), crate-push macro moves, static dead-squares as constant infra, **efficiency reporting split (scalar for optimality-preserving arm / Pareto for weighted; symmetry pruning dropped)**, eval-budget stop, dual counters (join key provisional), pure-Python validator with UCS optimality oracle, module layout + shared CSV schema draft. Full spec + build order: **`sokoban-port-plan.md`**. Corrects HANDOFF: specs do NOT cite IDA*; Java solver is greedy best-first, not A*; `w=1` optimality is verified by the UCS oracle (not assumed from admissibility alone).

## Deferred — Roan only

- **HP engine choice.** Options ranked: B&B chain-growth (thesis-clean) > NMCS (keeps MC flavor + search tree, Roucairol 2023) > plain Metropolis (on-theme via Category-D Simulated Annealing; weakest shared metric). **48-hour fuse — critical path.** Note: paradigm-neutral metric means this no longer blocks harness/paper design.

## Framing notes

- Existing Metropolis MC code is on-topic (SA is a Category-D example), not dead weight.
- `equivalence.md` predicts weak transfer ("Level 2, graphs fundamentally different") — a **negative transfer result is a valid, publishable finding.** Don't force a positive-transfer story.

## Handoff to next agent (top action = Roan's engine decision)

- Plan durable in `tasks.md` + this file. Safe to compact now.
- Front-load paper Methods/related-work in wk1–2; adapt CSINTSY `tester.py` + `analyzer.ipynb` for the harness.
