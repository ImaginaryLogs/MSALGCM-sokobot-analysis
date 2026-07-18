# ADR 0002 — HP-lattice engine: Branch-and-Bound chain-growth

**Date:** 2026-07-18
**Status:** Accepted

## Decision

Roan confirmed **Branch-and-Bound (B&B) chain-growth** as the HP-lattice search engine, resolving
the "ENGINE DECISION" 48h-fuse item (STATUS.md, critical path since 2026-07-17). Rejected
alternatives: NMCS (Roucairol 2023 — keeps MC flavor + a search tree) and plain Metropolis (on-theme
via Category-D Simulated Annealing, but weakest shared metric).

This resolves the cross-domain join-key ambiguity: B&B expansions map cleanly to Sokoban's
`nodes_expanded` (systematic node-expansion counter), not `candidates_scored`. See
[DECISIONS.md](../DECISIONS.md) for the dated entry locking `candidate_states_evaluated` to
`nodes_expanded`.

## Why

Relayed from Roan via CJ, recorded here at the level of detail available at time of writing:

- **Thesis-clean**: B&B is systematic search, matching `CONTEXT.md`'s "systematic search" category
  alongside Sokoban's weighted A* — both are complete, tree-structured, node-expansion-driven. This
  gives the comparative study two engines from the same paradigm (Level 2 local isomorphism, per
  `docs/equivalence/`), rather than forcing a systematic-vs-stochastic comparison to carry the whole
  paper.
- Rejected NMCS because a nested playout is *many* evaluations per sample, complicating the
  join-key story even though it keeps a search tree.
- Rejected plain Metropolis because Category-D Simulated Annealing framing is weakest on shared
  metric (1 proposal = 1 eval, but no branching factor / node-expansion structure to compare
  against Sokoban's WA*).

**Flagged for Roan to expand:** this ADR captures only the CJ-relayed summary. Roan should amend
with the fuller HP-side rationale (state-space structure, chain-growth branching factor, bound
function choice) when the HP build lands.

## Consequences

- `candidate_states_evaluated` (D6, `docs/specs/sokoban-port-plan.md`) is now **locked** to
  `nodes_expanded`, not provisional. Sokoban still logs `candidates_scored` too (cheap, D5), just
  not as the join key.
- `algorithm` CSV value for the HP side = `bnb`.
- `CONTEXT.md`'s "Candidate-state evaluation" glossary entry updated to reflect the resolved join
  key (was previously marked PROVISIONAL).
