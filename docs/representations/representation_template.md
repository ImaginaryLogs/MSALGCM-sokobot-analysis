# Cross-Domain Algorithm Comparison Framework

A reusable template for rigorously comparing an algorithm in a "toy" domain against
its counterpart in a "transfer" domain — designed so the correspondence claim is
explicit and gradeable, not just narratively plausible.

---

## Why comparisons go "foggy"

Almost every foggy cross-domain comparison has the same shape: two well-defined
algorithms, connected by an implied arrow that nobody actually draws. The reader
sees Layer 1–4 (representation, objective, strategy, reduction) done well for both
domains, then a conclusion ("these transfer"), with nothing formal in between.
**Layer 5 below — the Bridge — is that missing arrow.** Making it its own explicit
step (and its own slide) is usually what turns "interesting analogy" into
"rigorous comparison" in a reader's eyes.

---

## The Template

Fill this out **independently for Domain A and Domain B first** (Layers 0–4), then
do Layer 5 as a separate, explicit act — not a byproduct of writing 0–4.

### Layer 0 — Domain Identity Card

- Real-world problem name
- Formal problem statement (decision version *and* optimization version, if both exist)
- Known complexity class, with citation
- One-sentence description of what a "solution" is

### Layer 1 — State-Space Representation

- State encoding: what data structure *is* a state?
- Initial state(s) and goal/terminal condition
- Transition function: what generates a legal edge between states?
- Underlying graph properties (fill a table like this for each domain):

| Property                                              | Value |
| ----------------------------------------------------- | ----- |
| Branching factor (avg / range)                        |       |
| Solution length (avg / range)                         |       |
| Search-space size (upper bound)                       |       |
| Underlying graph (directed / undirected)              |       |
| Cost of computing a lower bound (full / incremental)  |       |

### Layer 2 — Objective Function

- What is being minimized or maximized (or decided)?
- Cost/reward structure
- If heuristic search is involved: what admissibility condition must `h` satisfy?

### Layer 3 — Algorithmic Strategy

- Search paradigm name (IDA*, branch-and-bound, NMCS, etc.)
- Node evaluation formula, stated explicitly (e.g. `f(n) = g(n) + h(n)`)
- Expansion order / policy
- Termination or convergence criterion

### Layer 4 — Reduction Techniques

For **each** pruning/abstraction technique used, state three things:

1. What gets discarded or collapsed?
2. The soundness argument — *why* it's safe to discard (this is what separates a
   real reduction from a heuristic guess)
3. What it costs to compute (this is where "overhead vs. savings" tradeoffs live)
