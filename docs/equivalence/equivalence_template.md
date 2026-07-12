# Domain Equivalence

## Layer 5 — The Bridge

This is a standalone act of writing down the actual map between Domain A and Domain B, and being honest about how strong the claim is. State it in this order:

**1. The map itself**, as explicit functions:

```txt
f : States_A         -> States_B
g : Transitions_A    -> Transitions_B
c : Cost/Objective_A -> Cost/Objective_B
```

**2. The strength of the claim** — pick one only

| Level | Name                              | What it means |
| ----- | --------------------------------- | ------------- |
| 0     | Narrative analogy                 | "These feel similar." No formal map exists. Weakest claim — flag it as such, never present it as equivalence. |
| 1     | Structural homomorphism           | A map exists between states/transitions, but it's partial or lossy — some structure in A has no counterpart in B. Most toy -> transfer-domain claims genuinely live here. |
| 2     | Local isomorphism                 | An exact structural match, but only over a substructure (e.g., "deadlock detection ≅ self-trap detection" because both are *local irrecoverability tests on a constraint graph*, even if the full search algorithms around them differ). |
| 3     | Functorial / group-theoretic map  | A provable, structure-preserving map over the *entire* space — objects, morphisms, and composition all correspond. Strongest claim; rare to achieve outside formal frameworks. |

**3. Similaries and Differences** — list both explicitly. A comparison that only lists what transfers, with no acknowledgment of what breaks, reads as oversold.

## Layer 6 — Empirical Characteristics Comparison

Put the Layer-1 tables for both domains side by side.

---

## Extension slots (for later — group theory / category theory / information geometry)

The Bridge (Layer 5) is intentionally left generic above so we can swap in a stricter formal language later without restructuring the whole framework:

**Group theory slot** — use when the reduction technique is a symmetry pruning. Define the automorphism group `G` acting on the state space, and treat the reduction as search over the quotient `States / G`. (This is the natural home for "dihedral symmetry pruning" claims — state the group explicitly rather than gesturing at "symmetry.")

**Category theory slot** — use when we want Layer 5 to hit Level 3. Treat each domain as a category: objects = states, morphisms = valid transitions, composition = sequencing moves. The Bridge becomes a functor `F : Cat_A → Cat_B`. An admissible heuristic in both domains is then a *natural transformation* — a family of cost maps that commutes with `F`. This is also the natural place to formalize "relaxation" (dropping a constraint, e.g. self-avoidance or collision) as a forgetful functor into a common, easier category, with both domains' heuristics defined as `h = cost ∘ (relaxation functor)`.

**Information geometry slot** — use only when the algorithms in question generate *distributions* over states or policies (e.g., NMCS/MCTS rollout policies, not plain deterministic search). Treat the policy space as a statistical manifold, compare algorithms via a metric (Fisher information metric) or divergence (KL divergence) between their induced distributions, rather than via discrete graph structure. This slot doesn't apply to deterministic branch-and-bound or A*, only to the stochastic-search side of our comparison (NMCS <-> NMCS-on-HP is exactly where this would eventually go).
