# Category Theory Slot

While the global domains of Sokoban (PSPACE-complete) and HP-Lattice (NP-complete) cannot be globally isomorphic, their heuristic constructions exhibit a formal Level 3 Functorial Equivalence. Both heuristics are derived via forgetful functors to the same relaxed mathematical structure, where admissibility is modeled as a natural transformation.

## Defining the Categories and Morphisms

To prove functoriality, we cannot just define states; we must define categories with both objects and morphisms.

1. Sokoban Category $\mathbf{Cat_{Soko}}$
   - Objects: Valid Sokoban board configurations $S$.
   - Morphisms: $S \to S'$ is a valid push sequence that transitions the board from $S$ to $S'$. Composition is the concatenation of pushes.
2. HP Lattice Category $\mathbf{Cat_{HP}}$
   - Objects: Valid, self-avoiding partial chain configurations $P$.
   - Morphisms: $P \to P'$ is a valid sequence of monomer placements transitioning the fold from $P$ to $P'$.
3. The Shared Relaxed Category $\mathbf{Cat_{Match}}$
   - Objects: Weighted bipartite graphs $G = (U, V, E, w)$.
   - Morphisms:
      - $G \to G'$ represents a subgraph reduction or edge-weight update.
      - Specifically, a morphism exists if $G'$ can be formed from $G$ by:
         - removing a node (an item is matched/placed) or
         - updating an edge weight (an item moves closer to/further from a target).
      - Composition is successive graph updates.
4. The Objective Category $\mathbf{Cat_{Cost}}$
    - A posetal category of real numbers representing costs to the goal.
    - Objects: Non-negative reals $\mathbb{R}^{\ge 0}$.
    - Morphisms: A unique morphism $x \to y$ exists if and only if $x \le y$. This is standard for modeling bounds.
