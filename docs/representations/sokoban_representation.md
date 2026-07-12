# Sokoban Template

## Layer 0 — Domain Identity Card

- **Real-world problem name**: Sokoban "Warehouse Keeper" - a single-agent puzzle in which an agent pushes boxes onto designated storage goal tiles on a 2D grid.
- **Formal problem statement**:
  - Decision version: Given a sokoban board configuration does there exist a finite sequence of pushes that transforms
  - Optimization version:
- **Known complexity class**: PSPACE Complete
- **Solution**: A finite sequence of directional movements (Up, Down, Left, Right) executed by the agent that transitions the board from the initial configuration to the goal configuration

## Layer 1 — State-Space Representation

- State encoding:  Most algorithms have the following state encodings: `(agent_position, set_of_box_positions)`
  - State is uniquely represented by a tuple of the ff.:
    - The agent's position
    - Set of box positions located within the map
  - Important states such as map information, walls, goal positions remain *static and is shared globally through the algorithm*
- Initial state(s) and Terminal Condition:
  - Initial State: Starting coordinates of the agent and all boxes
  - Terminal State:
    - Winning State: Every box coordinate matches a coordinate in the set of designated goal locations.
    - Failure State: Deadlock configurations, where a box is stuck permanently in a restricted space, act as terminal failure states.
- Transition function: Legal Moves available are thee ff.:
  - The Agent moves to an adjacent empty square.
  - The Agent pushes a box from one space to an empty square in the direction of movement.
  - The Agent pushes a box from one space to an goal square in the direction of movement.
  - Note: This is a Cyclic Directed graph, as the agent can loop around itself.
- Underlying graph properties (fill a table like this for each domain):

| Property                                              | Value                                                         |
| ----------------------------------------------------- | ------------------------------------------------------------- |
| Branching factor (avg / range)                        | 1.44                                                          |
| Solution length (avg / range)                         | mean: 122.04, std: 87.89                                      |
| Search-space size (upper bound)                       | (R x B choose C) x (R x C - B)                                |
| Underlying graph (directed / undirected)              | Directed (pushes are irreversible; boxes cannot be pulled)    |
| Cost of computing a lower bound (full / incremental)  | O(B^3)                                                        |

Source: <https://github.com/ImaginaryLogs/CSINTSY-sokobot2024>

## Layer 2 — Objective Function

- What is being minimized or maximized: Minimizing total cost to reach the goal state.
- Cost/reward structure: There are two reward structures:
  - In push-optimality, any agent movement without pushing is 0, else 1.
  - In move-optimality, any agent movement w or w/o pushing is 1.
- If heuristic search is involved:
  - The heuristic function must be admissible, meaning it never overestimates the true remaining cost to the goal: $h(n) \le h^*(n)$.
  - Common choice is the minimum weight matching of boxes to goals using Manhattan distances.

## Layer 3 — Algorithmic Strategy

- Search paradigm name: Iterative Deepening A* combined with Transposition Tables
- Node evaluation formula, stated explicitly:
  - Heuristic function `f(n) = g(n) + h(n)`
    - `f(n)` - total cost of the best path to the target that goes through n
    - `g(n)` - the exact known cost to reach node n from the starting point
    - `h(n)` - estimated heuristic cost to reach the goal node
- Expansion order:
  - Sort by descending `f(n)` cost.
  - Ties are broken with the highest `g(n)` value.

- Termination or convergence criterion
  - Terminates successfully when the node selected for expansion satisfies the goal condition.
  - Terminates with failure if the open list becomes empty.

## Layer 4 — Reduction Techniques

### Static Deadlock Pruning
  
- Discarded State: Any state where a box occupies a tile from which it can never be pushed onto any goal tile.
- Soundness:
    1. Boxes cannot be pulled.
    2. If a box enters a static deadlock tile, it is permanently stuck outside of the goal set.
    3. Since all boxes must reach goals to satisfy the terminal condition, no goal state can evolve from this state.
    4. Thus, its safe to discard.
- Computation Cost:
  - O(R x C) pre-computation time at startup to map the board's dead zones.
  - Checking a state during search costs O(1) by verifying the moved box's new coordinates against the pre-computed map.

### Transposition Tables

  1. Discarded State: Duplicate states where the boxes are in identical positions and the agent resides within the same reachable connected component (zone) of empty tiles.
  2. The exact path the agent walks to position itself behind a box does not change the future legality of box pushes, provided the agent can reach that position without moving any boxes. Collapsing these paths into a single agent zone prevents redundant search paths.
  3. $O(1)$ incremental hash updates using Zobrist hashing to track box positions, combined with a flood-fill algorithm costing $O(R \times C)$ to identify the agent's reachable zone during node evaluation.

<https://en.wikipedia.org/wiki/Zobrist_hashing>
