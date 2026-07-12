# HP Lattice Template

## Layer 0 — Domain Identity Card

- **Real-world problem name**: Simplified Protein Folding (Hydrophobic-Polar Lattice Model)
- **Formal problem statement**:
  - **Decision Version**:
    - Given an amino acid sequence $s \in \{H, P\}^n$ and an energy threshold $K$,
    - Does there exist a self-avoiding walk (SAW) embedding of $s$ on a lattice
    - such that the total free energy $E \le -K$?
  - **Optimization Version**:
    - Given a sequence $s$,
    - Find a self-avoiding walk embedding on a lattice
    - That maximizes the number of topological $H-H$ contacts (thereby minimizing the total free energy).
- **Known complexity class**: NP-complete
- **Solution**:
  - A sequence of relative lattice directions (e.g., Left, Right, Forward) or
  - Absolute coordinates of length $\vert{}s\vert{}-1$
  - That maps each amino acid to a distinct lattice point without self-intersection.

## Layer 1 — State-Space Representation

- State encoding: `(current_index, coordinates_list)`
  - A state represents a partially embedded chain prefix. It is encoded as a tuple containing:
    - the current sequence index and
    - the ordered list of spatial coordinates occupied so far
- Initial state(s) and goal/terminal condition:
  - **Initial state**: The first monomer $s[0]$ is placed at the origin $(0,0)$, and the second monomer $s[1]$ is placed at $(1,0)$ to fix initial rotational symmetry.
  - **Goal/terminal condition**: The state reaches a depth where current_index == |s| - 1 (all monomers successfully placed) while maintaining the self-avoiding condition.
- **Transition function**:
  - Legal Move:
    - The next monomer $s[i]$ is placed on an empty lattice site immediately adjacent to the coordinate of $s[i-1]$.
  - If all adjacent positions are occupied, the state has no outgoing edges (dead end).
- Underlying graph properties (fill a table like this for each domain):

| Property                                              | Value |
| ----------------------------------------------------- | ----- |
| Branching factor (avg / range)                        |       |
| Solution length (avg / range)                         |       |
| Search-space size (upper bound)                       |       |
| Underlying graph (directed / undirected)              |       |
| Cost of computing a lower bound (full / incremental)  |       |

## Layer 2 — Objective Function

- What is being minimized or maximized:
  - Maximizing the number of topological H-H contacts
  - Minimizing the free energy E = -contacts
- Cost/reward structure:
  - A reward of $+1$ contact (or $-1$ energy) is given for every pair of hydrophobic H monomers that are adjacent on the spatial lattice but not adjacent in the primary sequence chain.
- If heuristic search is involved:
  - In Maximization Branch-and-Bound or A* equivalent framework, the upper bound function U(n) must be an admissible overestimation of the maximum possible total contacts: $U(n) \ge f^*(n)$.

## Layer 3 — Algorithmic Strategy

- Search paradigm name: Depth-First Branch-and-Bound (DFBnB) or Nested Monte Carlo Search (NMCS).
- Node evaluation formula, stated explicitly:
  - Heuristic function `U(n) = g(n) + h(n)`
    - `f(n)` - total cost of the  to the target that goes through n
    - `g(n)` - is the number of valid $H-H$ contacts formed by the current prefix
    - `h(n)` - the upper bound of possible remaining contacts.
- Expansion order:
  - Depth-first to quickly locate complete candidate sequences and establish a strong global lower bound
  - Children are ordered greedily, prioritizing moves that maximize immediate local H-H contacts.
- Termination or convergence criterion:
  - Complete exhaustion of the pruned search tree. The algorithm terminates when all unpruned branches are explored,
  - Returning the configuration associated with the highest contact count.

## Layer 4 — Reduction Techniques

### Parity-Based Constraint Pruning

1. Discarded State: Entire partial fold subtrees are discarded.
   - If their ideal potential upper bound $U(n)$ cannot strictly exceed the best globally established contact score (Best_Energy).

2. Soundness:
   1. A square lattice can be separated in a checkboard parts - this forms a bipartite graph.
   2. Consequently, an H monomer at an odd sequence index can only form a topological contact with an H monomer at an even sequence index.
   3. By counting the remaining available unplaced Odd-H and even-h monomers, we can compute a mathematically absolute maximum on future contacts.
      - Odd_H := Available unplaced odd-H
      - Even_H := Available unplaced even-H
      - The minimum of the two tells us how many adjacent H-H contacts.
   4. If g(n) + min(Odd_H, Even_H) <= Best_Energy, the branch is guaranteed to be sub-optimal and is safely discarded.

3. Computation Cost: O(1) incremental lookups if the remaining pools of odd/even $H$ monomers are tracked using a global array or down-counters during the forward search.

### Coordinate-Free Symmetry Eliminators

1. Discarded State: Symmetric states that are mirror images or rigid rotations of already explored structural states.
2. Soundness:
   1. The physics of the HP lattice are completely isotropic / symmetric.
   2. If a sequence prefix transitions relative to itself (e.g., taking a step Left vs Right on the very first turn), the absolute grid orientation changes.
   3. But the distance matrix—and thus the energy capacity—remains perfectly identical.
   4. Forcing the first directional change to a single arbitrary direction breaks dihedral symmetry safely without losing optimal solutions.

3. Computation Cost: O(1) incremental lookups if the remaining pools of odd/even $H$ monomers are tracked using a global array or down-counters during the forward search.
