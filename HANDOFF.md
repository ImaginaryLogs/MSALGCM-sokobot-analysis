# Handoff — Sokoban ↔ HP-Lattice Comparative Search Study

**Date:** 2026-07-29
**From:** Current Agent
**To:** Next Agent (Literature & Related Works Specialist)

---

## 1. Executive Summary & Current Project State

We are conducting a comparative search study evaluating algorithmic shortcuts (**Heuristic Strength** and **Heuristic Weight Tuning**) across two PSPACE/NP-complete state-space search domains:

1. **Sokoban** ($A^*$ with Manhattan vs. Hungarian min-cost matching heuristics, Weighted $A^*$).
2. **HP-Lattice Protein Folding** (Systematic Branch-and-Bound chain growth).

### Key Decisions & Locked Parameters ([DECISIONS.md](docs/DECISIONS.md))

- **Arm A (Optimality-Preserving):** Heuristic Strength — Manhattan vs. Hungarian min-cost matching at $w=1.0$. Reported via **scalar efficiency ratio**.
- **Arm B (Quality-Trading):** Heuristic Weight Tuning — Weighted $A^*$ ($w \in \{1.0, 1.25, 1.5, 2.0, 3.0, 5.0\}$). Reported via **Pareto curves** (evaluations vs. solution quality).
- **Cross-Domain Join Key:** `nodes_expanded` (candidate states evaluated).
- **Evaluation Budget:** $N = 2,000,000$ evaluations per instance.
- **Sokoban Benchmark Suite:** 155 eligible maps in `src/sokoban/maps/`.
- **Phase-2 Full Data Run:** Completed (1085 experimental rows generated into `results/results.csv`).

---

## 2. Literature Quota Status & Gap Analysis

Per the assignment specifications ([docs/reference/project-specs.md](docs/reference/project-specs.md)), the final literature review must include at least:

- **10 Peer-Reviewed Papers**
- **2 Textbooks**
- **2 Conference Publications**
  _(Total: 14 items)_

### Current Proposal Inventory ([docs/reference/project-proposal.md](docs/reference/project-proposal.md)) — 9 Items Total:

#### **Conference Publications (1 of 2):**

1. **Reif, J. H. (1979).** _Complexity of the Mover's Problem and Generalizations._ 20th Annual IEEE Symposium on Foundations of Computer Science (FOCS 1979), 421–427.

#### **Peer-Reviewed Papers (8 of 10):**

2. **Culberson, J. (1997).** _Sokoban is PSPACE-complete._ Fun with Algorithms / Technical Report.
3. **Junghanns, A., & Schaeffer, J. (2001).** _Sokoban: Enhancing general single-agent search methods using domain knowledge._ Artificial Intelligence, 129(1-2), 219-251.
4. **Korf, R. E., Reid, M., & Edelkamp, S. (2001).** \*Time complexity of iterative-deepening-A\*_._ Artificial Intelligence, 129(1-2), 199-218.
5. **Botea, A., Müller, M., & Schaeffer, J. (2002).** _Using Abstraction for Planning in Sokoban._
6. **Lau, K. F., & Dill, K. A. (1989).** _A lattice statistical mechanics model of the conformational and sequence spaces of proteins._ Macromolecules, 22(10), 3986–3999.
7. **Berger, B., & Leighton, T. (1998).** _Protein folding in the hydrophobic-hydrophilic (HP) model is NP-complete._ Journal of Computational Biology, 5(1), 27–40.
8. **Crescenzi, P., et al. (1998).** _On the complexity of protein folding._ Journal of Computational Biology, 5(3), 423-465.
9. **Roucairol, M., & Cazenave, T. (2023).** _Solving the HP model with Nested Monte Carlo Search._ arXiv:2301.09533.

---

## 3. Recommended Additions for Next Agent

To fill the 5 remaining literature gaps and complete the 14-item quota, the next agent should add and synthesize the following:

### **A. Textbooks (Add 2)**

1. **Russell, S., & Norvig, P. (2020).** _Artificial Intelligence: A Modern Approach (4th ed.)._ Pearson.
   - _Role:_ Authoritative text for $A^*$ search, heuristic admissibility, weighted $A^*$ bounded suboptimality, and Branch-and-Bound search space traversal.
2. **Garey, M. R., & Johnson, D. S. (1979).** _Computers and Intractability: A Guide to the Theory of NP-Completeness._ W. H. Freeman and Company.
   _(Alternative: Arora, S., & Barak, B. (2009). Computational Complexity: A Modern Approach. Cambridge University Press.)_
   - _Role:_ Foundational textbook for PSPACE and NP-completeness complexity classes and reduction methods.

### **B. Conference Publication (Add 1)**

3. **Botea, A., Müller, M., & Schaeffer, J. (2003).** _Extending Abstract Planning in Sokoban._ Proceedings of the Thirteenth International Conference on Automated Planning and Scheduling (ICAPS 2003), 187–196.
   _(Alternative: Felner, A., Korf, R. E., & Hanan, S. (2004). Additive Pattern Database Heuristics. AAAI 2004.)_
   - _Role:_ Official conference publication for macro-graph planning and room/tunnel abstraction.

### **C. Peer-Reviewed Papers (Add 2)**

4. **Culberson, J. C., & Schaeffer, J. (1998).** _Pattern databases._ Computational Intelligence, 14(4), 318-334.
   - _Role:_ Seminal paper on lower-bound domain abstraction and tighter admissible heuristics (supports Arm A: Heuristic Strength).
5. **Pohl, I. (1970).** _Heuristic search reasoning: concepts, algorithms and applications._ Machine Intelligence, 6, 219-236.
   _(Alternative: Thayer, J. T., & Ruml, W. (2011). Bounded Suboptimal Search: A Survey. AI Communications.)_
   - _Role:_ Original foundational paper proposing Weighted $A^*$ ($f = g + w \cdot h$) to trade solution optimality for search effort reduction (supports Arm B: Weight Tuning).

---

## 4. Key Files to Pass to NotebookLM

For NotebookLM sync, provide the following 4 core context documents:

1. `docs/reference/project-proposal.md` — Research Questions & Reference Table
2. `CONTEXT.md` — Glossary & Metric Definitions
3. `docs/DECISIONS.md` — Locked Architecture & Baseline Parameters
4. `docs/equivalence/sokoban_hp-latice_equivalence.md` — Domain Mapping & Local Isomorphism Theory
