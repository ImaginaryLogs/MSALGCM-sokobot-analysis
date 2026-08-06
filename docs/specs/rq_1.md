Here is the write-up for the RQ1 constraint-semantics taxonomy section. I have structured it using a hybrid of prose and bullet points to ensure the structural differences remain highly scannable, and I have integrated the `original3` instance data as a confirmatory data point. It is formatted to be dropped directly into `METHODOLOGY_SYNTHESIS.md` right before the RQ2 heading.

---

### RQ1: Constraint-Semantics Taxonomy

Both domains must reject illegal or terminal dead states, but where this check occurs in the pipeline and whether it is coupled to the heuristic evaluation differs structurally. This structural distinction forms the central throughline for addressing RQ4 later in the analysis.

* **Sokoban: Decoupled Deadlock Detection**
* Sokoban relies on an `is_dead()` domain-constraint rejection that operates completely decoupled from the heuristic.


* Because a crate pushed into a dead corner can still appear heuristically close to the goal, and because Manhattan and Hungarian heuristics carry no deadlock information, deadlock detection must operate as a separate mechanism.


* This separate check rejects approximately 59% of candidate pushes independently of the heuristic h.


* Instance-level confirmation supports this: the `original3` trace shows exactly 59.18% of expanded or pruned nodes were pruned.




* **HP Lattice: Fused Bound-Pruning**
* Conversely, HP relies on a bound-based prune (enforcing search-optimality) that is inherently fused with the heuristic.


* This bound-based prune outnumbers a purpose-built connectivity prune by 10 to 100 times.


* Adding a connectivity-prune on top of the search only cuts `nodes_expanded` by roughly 0.1–0.2%, because the parity-capacity bound already implicitly captures most of what a separate deadlock check would catch.


* While the separate check does not catch more dead ends overall, it does catch the same dead ends earlier at an ancestor, which measurably halves the trap rate from 0.90% to 0.37%.





Ultimately, in Sokoban, heuristic-quality and deadlock-quality are two separable knobs; in HP they're one fused knob. Nothing about "illegal state" topology (disconnectivity, curvature, or Mapper fragmentation) is interpretable until each domain's rejection mechanism is defined here first.