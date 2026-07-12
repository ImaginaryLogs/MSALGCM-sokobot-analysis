# Equivalence Mapping

## Layer 5 - Mapping Bridge

### Maping

```txt
f : States_Sokoban  -> States_HP
    * Grid Space    -> Spatial Lattice
    * Box Locations -> Monomer Coordinates
    * Static Walls  -> Dynamic self-avoidance (previously placed monomers act as walls)
    * Goal Tiles    -> Favorable H-H contact adjacencies

g : Transitions_Sokoban -> Transitions_HP
    * Push box into empty space -> Place next monomer into empty space
    * Agent reachability constraint -> Chain connectivity constraint

c : Cost/Objective_Sokoban -> Cost/Objective_HP
    * Total steps/pushes (Minimize g(n)) -> Total sequence length placed (Maximize depth)
    * Min-cost matching heuristic (Minimize h(n)) -> Max-contact parity bound (Maximize h(n))
```

### Strength of Claim

Level 2: Local isomorphism.

Justification: The overall search graphs are fundamentally different.

However, an exact structural match exists over the substructure of spatial deadlocks (local irrecoverability). A Sokoban box pushed into a corner is structurally identical to an HP chain folding itself into a dead-end pocket. Both domains require local constraint-graph analysis to detect when a spatial tile has become permanently inaccessible or inescapable.

### Similarities and Differences

- Similarities
  - Spatial collision constraints: Both domains require strict non-overlapping elements on a discrete grid.- Deadlock/Trap dynamics: Both domains heavily rely on early pruning of states where future valid transitions drop to zero.
  - Bipartite grid properties: The Manhattan distance parity (odd/even checkerboard coloring) fundamentally dictates heuristics in both domains (Sokoban minimum matching distances and HP sequence parity contacts).

- Differences:
  - Agent decoupling: In Sokoban, an independent agent navigates the empty space to act on objects. In HP, the "agent" is simply the growing tip of the object itself.
  - Graph structure (Cycles vs. Trees): Sokoban states can be revisited via different agent paths (necessitating transposition tables). HP states are constructed one monomer at a time; you cannot arrive at an identical partial chain configuration via two different sequence orderings.
  - Goal structure: Sokoban targets specific absolute coordinates (goal tiles). HP targets relative topological alignments (H-H contacts) regardless of absolute grid position.

## Layer 6 — Empirical Characteristics Comparison

To Be filled later.
