# Planning Decisions & Handoff — 2026-07-17

## Resolved
1. **Sokoban port target:** Python (into `src/sokoban/`). Solver + headless loader + data emit only; no GUI. Java kept as reference oracle; Java-wrap is the fallback if wk1 slips.
2. **Technique scope:** 2 committed (heuristic weight tuning, symmetry pruning) + 1 stretch (macro-graph tunnel abstraction).
3. **Task split:** CJ=Sokoban, Roan=HP, Enzo=lit review + shared harness + paper assembly.
4. **Measurement:** paradigm-neutral "candidate states evaluated to reach quality threshold"; baseline = vanilla solver; efficiency ratio = base/opt evals; per-technique ablation; secondary TTS + peak frontier.
5. **Lit Review:** distributed by domain (each builder annotates their 4 papers), Enzo sources missing sources + synthesizes. Due Jul 24.

6. **Sokoban port architecture (9 grilled decisions):** Weighted A* + closed list (`f=g+w·h`, skip on `g>stored`; NOT IDA* — Sokoban transposition makes a closed list mandatory), greedy Manhattan base-`h` (swappable seam, Hungarian later), crate-push macro moves, static dead-squares as constant infra, first-valid-solution efficiency-ratio target, module layout + shared CSV schema draft. Full spec + build order: **`sokoban-port-plan.md`**. Corrects HANDOFF: specs do NOT cite IDA*; Java solver is greedy best-first, not A*.

## Deferred — Roan only
- **HP engine choice.** Options ranked: B&B chain-growth (thesis-clean) > NMCS (keeps MC flavor + search tree, Roucairol 2023) > plain Metropolis (on-theme via Category-D Simulated Annealing; weakest shared metric). **48-hour fuse — critical path.** Note: paradigm-neutral metric means this no longer blocks harness/paper design.

## Framing notes
- Existing Metropolis MC code is on-topic (SA is a Category-D example), not dead weight.
- `equivalence.md` predicts weak transfer ("Level 2, graphs fundamentally different") — a **negative transfer result is a valid, publishable finding.** Don't force a positive-transfer story.

## Handoff to next agent (top action = Roan's engine decision)
- Plan durable in `tasks.md` + this file. Safe to compact now.
- Front-load paper Methods/related-work in wk1–2; adapt CSINTSY `tester.py` + `analyzer.ipynb` for the harness.
