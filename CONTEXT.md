# Context — Glossary

Ubiquitous language for the Sokoban ↔ HP-Lattice comparative study. Glossary only — no implementation details.

- **Systematic search** — complete, tree-structured exploration with node expansion and pruning (IDA*, Branch-and-Bound, NMCS). Produces a branching factor.
- **Stochastic sampling** — Metropolis Monte Carlo: perturbs a *complete* configuration and accepts/rejects. No search tree, no branching factor. Distinct paradigm from systematic search; conflating the two is the project's central modeling hazard.
- **Candidate-state evaluation** — the paradigm-neutral unit of work: a node expanded (systematic) or a sample drawn (stochastic). The shared primary metric.
- **Efficiency ratio** — baseline evaluations ÷ optimized evaluations, to a fixed quality target (solved/optimal for systematic; energy threshold for stochastic).
- **Heuristic weight tuning** — adjusting the weights of cost-function terms to reduce evaluations. Committed technique.
- **Symmetry pruning** — discarding states equivalent under board rotation/reflection and checkerboard parity. Committed technique.
- **Macro-graph tunnel abstraction** — Botea-style decomposition of the board into rooms + tunnels for macro-level planning. Stretch technique; weakest cross-domain transfer.
- **Transfer (equivalence) claim** — currently *Level 2, local isomorphism*: the two search graphs differ globally but share deadlock/parity substructure. Weak transfer is an acceptable finding, not a failure.
- **Reference oracle** — the original Java Sokoban solver, run alongside the Python port to validate solutions and node counts.
