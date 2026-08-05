# Cross-Domain Structural Analysis: Design Prototype
### Sokoban ↔ HP-Lattice Search-Space Comparison
**Project:** MSALGCM-sokobot-analysis — exploratory extension
**Scope:** design-level prototype for Ideas 1–3 (topology, shared characteristics, category-theoretic scaffolding). Not a reduction of one domain to the other — both domains keep their native state/move definitions throughout.

---

## 0. Shared instrumentation (prerequisite for everything below)

All three ideas consume the same underlying trace. If Phase 2 runs only logged summary rows (nodes_expanded, solution cost, etc.), the additions below are the one shared cost across ideas 1–3.

### 0.1 Per-node expansion trace

For every expanded node, in both solvers, log a row:

```
node_id            : unique int, assigned at expansion time (expansion order)
parent_id          : node_id of the state it was generated from (None for root)
state_hash         : domain-native canonical hash of the state
g, h, f            : cost-so-far, heuristic estimate, f = g + w*h
depth              : moves from root
n_legal_successors : |successors(state)| under domain move rules
n_pruned           : successors rejected by domain constraint (deadlock / self-avoidance)
move_type          : domain-specific tag, see §2.3
status             : one of {frontier, expanded, pruned, goal} — see §3.1
timestamp_order    : monotonically increasing integer (expansion sequence)
```

This is one table schema for both `src/sokoban/` and `src/protein-fold/`, keyed by `(instance_id, config_id, node_id)`. `move_type` and the deadlock/self-avoidance semantics differ per domain, but the columns are identical — this is what makes cross-domain comparison a join rather than a translation.

### 0.2 Induced-subgraph reconstruction

From `(node_id, parent_id)` you can reconstruct the induced expansion subgraph directly — no re-running the solver. Every method in Idea 1 that needs graph structure (curvature, discrete Morse, intrinsic-distance persistence) reads this reconstructed graph, not a live solver.

### 0.3 Cost estimate

Roughly one added `log_row()` call per expansion in each solver, plus a shared `traces.py` / `analysis/` module that both domains write into the same schema. No solver logic changes — only instrumentation.

---

## 1. Topological analysis of the search-expansion graph

Object of study: the induced subgraph of expanded nodes, with `f` (or `h`) as a scalar function over it. All five sub-methods below read the trace in §0 and nothing else.

### 1.1 Disconnectivity graphs (borrowed from HP energy-landscape theory)

- **Input:** node trace with `f` values; induced subgraph edges from `parent_id`.
- **Algorithm:** sweep a threshold `τ` from `min(f)` to `max(f)`. At each `τ`, take the sublevel-set subgraph `{n : f(n) ≤ τ}`, compute connected components, and record component-merge events as `τ` rises.
- **Output artifact:** a branching tree (standard disconnectivity-graph plot) per `(instance, config)`.
- **Cross-domain comparison metric:** basin count at merge, basin-size distribution, tree depth vs. `nodes_expanded`. Compare Sokoban-with-`h`-as-potential against HP-with-native-contact-energy using identical tree statistics.
- **Prototype scope:** reuse whatever disconnectivity-graph code already exists for the HP-lattice side (if the MC engine in ADR 0002's alternative had any); apply unmodified to Sokoban's `f`.

### 1.2 Persistent homology on the expanded-node point cloud

Two variants, both worth running (they're cheap in relative terms and answer different questions):

**(a) Feature embedding** — points = `(g, h)` or `(g, h, f)` per node, Euclidean distance, Vietoris–Rips filtration.
**(b) Intrinsic embedding** — distance = shortest-path distance in the induced subgraph (landmark-subsampled for large instances), same filtration machinery.

- **Output artifact:** persistence diagrams / barcodes for `β₀` and `β₁`.
- **Interpretation:**
  - `β₀` bars ≈ same cluster-merge information as §1.1, cross-check against it.
  - `β₁` bars = literal transpositions (Sokoban) / re-converging fold trajectories (HP) — a persistent 1-cycle means two distinct expansion routes closed a loop in the metric.
- **Cross-domain comparison metric:** `β₁` bar count and total persistence, normalized by `nodes_expanded`, plotted against heuristic strength (Arm A) and weight (Arm B). This is the most direct "does path-redundancy scale the same way" test.
- **Prototype scope:** `ripser` or `giotto-tda` on (a) first — no graph-shortest-path cost. (b) as a follow-up on a handful of representative instances.

### 1.3 Discrete Morse theory on `f`

- **Input:** induced subgraph + `f` per node.
- **Algorithm:** build a discrete vector field (Forman-style) pairing adjacent cells by `f`-value comparison; identify unpaired (critical) cells.
- **Output artifact:** critical-cell list, indexed 0/1/2, per instance.
- **Interpretation:** index-0 critical cells = local `f`-minima the search can't leave except via a worse state — deadlocks (Sokoban) / kinetic traps (HP), same object under domain-neutral vocabulary.
- **Cross-domain comparison metric:** critical-cell count by index, compared against Morse-inequality-implied Betti numbers from §1.2 as a consistency check.
- **Prototype scope:** implement only index-0 detection first (simplest, most interpretable); this alone gives a domain-neutral trap count without full Morse machinery.

### 1.4 Mapper

- **Input:** same point cloud as §1.2(a), filter function = `f` (or `h`).
- **Algorithm:** cover `range(f)` with overlapping intervals; cluster nodes within each preimage by graph-adjacency (not Euclidean — reuse the induced subgraph here); connect clusters sharing nodes.
- **Output artifact:** Mapper graph, visually comparable to §1.1's disconnectivity tree.
- **Cross-domain comparison metric:** agreement/disagreement with §1.1 — where the two disagree, note whether it's a cover-resolution artifact (Mapper) or a thresholding artifact (disconnectivity graph) before treating the discrepancy as signal.
- **Prototype scope:** `kmapper` with graph-adjacency clustering; run only after §1.1 exists, since its value here is as a cross-check.

### 1.5 Graph curvature (Ollivier-Ricci / Forman-Ricci)

- **Input:** induced subgraph only — no embedding, no `f` needed.
- **Algorithm:** per-edge curvature from local neighborhood overlap (Ollivier-Ricci: optimal transport between neighbor distributions; Forman-Ricci: combinatorial, cheaper).
- **Output artifact:** per-edge curvature scalar; aggregate into per-node or per-region curvature.
- **Interpretation:** negative-curvature edges = bottlenecks (only route through); positive = redundant well-connected regions.
- **Cross-domain comparison metric:** curvature distribution shape; correlate low-curvature edges with §1.2's `β₁` cycle locations (curvature says *where* it's thin, persistence says *whether it closes into a hole* — pair the two).
- **Prototype scope:** `GraphRicciCurvature` package (Forman variant first — no OT solver needed) directly on the reconstructed graph from §0.2.

### Null-model check (applies to all of §1)

For each method, also run it on a random induced subgraph of the same size drawn from the full domain state graph (not search-selected). A topological feature that appears identically in the null model is a generic property of grid-like combinatorial spaces, not something attributable to the heuristic or search strategy.

---

## 2. Shared-characteristic analysis without reduction

All four sub-items read `n_legal_successors`, `n_pruned`, `move_type` from the §0 trace — no additional instrumentation beyond §0.

### 2.1 Branching factor spectra
Distribution of `n_legal_successors` over expanded nodes, per domain. Compare mean/variance/skew across Arm A (heuristic strength) and Arm B (weight) settings, domain-vs-domain.

### 2.2 Constraint density / feasibility ratio
Per node: `feasibility_ratio = n_legal_successors / (n_legal_successors + n_pruned)`. Plot against heuristic error (`|h − true remaining cost|`, or `h` alone where true cost isn't tractable) and against local `nodes_expanded` growth rate. Compare the shape of this relationship across domains.

### 2.3 Local vs. global move classification
Requires `move_type` tagging at instrumentation time:
- Sokoban: single push = local; multi-box push chain / long traversal-then-push = nonlocal.
- HP-lattice: corner-flip / end-move = local; pivot = nonlocal (reorients a subchain).
Compare local/nonlocal expansion ratio across Arm A/B settings.

### 2.4 Plateau/shoulder detection
Along each run's expansion sequence (ordered by `timestamp_order`), detect runs where `f` is non-decreasing beyond a small `ε` for `≥ k` consecutive expansions. Compare plateau-length distributions across domains — deadlocks and kinetic traps should both surface as plateaus.

---

## 3. Category-theoretic scaffolding

Not full functor proofs — a classification scheme applied to data already being logged, plus two items (3.1, 3.4) that need additional instrumentation design, detailed below.

### 3.1 Shape category 𝒮 + forgetful labeling — **instrumentation**

**Objects of 𝒮** (small, fixed, domain-neutral):

```
FRONTIER   — generated, not yet expanded
EXPANDED   — popped and expanded by the solver
PRUNED     — rejected by a domain constraint (deadlock check / self-avoidance check)
TRAP       — expanded, but all successors have f ≥ current f (index-0 critical, §1.3)
GOAL       — terminal accepting state
```

**Morphisms of 𝒮:** `can-transition-to`, i.e., a directed edge `A → B` exists if some domain move can carry a state with status A to a state with status B. This is fixed once, not per-domain.

**Instrumentation needed (new, beyond §0):**
- `status` column in §0's schema must be populated at *every* state touch, not only at expansion — this means the solver's frontier-management code (open-list push, prune check) needs a `log_status(node, status)` call at each of: generation → FRONTIER, pop-and-expand → EXPANDED, constraint rejection → PRUNED, all-successors-worse check → TRAP (this reuses the §1.3 index-0 test as a live check rather than a post-hoc one — cheap to compute inline: compare `f` of current node against `min(f)` over generated successors), goal check → GOAL.
- A second table, `status_transitions`, one row per observed `(prior_status, new_status, instance_id, config_id)` — this is what gets aggregated into the transition matrix in §3.2, and needs to be logged at generation time since a node's status can change over its lifetime (FRONTIER → EXPANDED → possibly TRAP is discovered later).
- Cost: touches solver control flow (not just post-processing) in both `src/sokoban/` and `src/protein-fold/`, at exactly the 4 call sites above. This is the one place in the whole document that isn't pure post-hoc analysis on existing logs.

**Functors:** `F_Sokoban`, `F_HP` : each domain's state category → 𝒮, defined simply as "read the logged `status` column." No additional code beyond the logging above — the functor *is* the label.

### 3.2 Transition-matrix comparison
From `status_transitions`, build a 5×5 stochastic matrix per `(domain, config)`. Compare `F_Sokoban`'s matrix to `F_HP`'s matrix via KL divergence and via eigenvalue spectrum of the transition matrix (mixing rate / stationary distribution). A natural transformation candidate is tested by checking whether corresponding entries differ by a near-constant multiplicative factor across all populated cells — constancy stands in for the naturality square commuting.

### 3.3 Heuristic as natural transformation (cost-functor slack)
`C_domain(state)` = true remaining cost (exact for Sokoban via post-hoc backward cost from solved instances; approximate for HP via best-found remaining energy path). `Ĥ_domain(state) = h(state)`. Target category = `(ℝ≥0, ≤)`. Naturality/admissibility slack = `C − Ĥ`, logged per node using values already in §0 (`h`) plus one derived column (`C`, computed post-hoc from the solved trace, no new solver instrumentation). Compare slack distributions across domains and across Arm A/B settings.

### 3.4 Product/monoidal factorization — **instrumentation**

**Claimed decomposition:**
- Sokoban: `state ≅ player_position × box_configuration`
- HP-lattice: `state ≅ backbone_shape × contact_set`

**What "separable efficiency gain" means concretely:** whether the reduction in `nodes_expanded` from a stronger heuristic (Arm A) or higher weight (Arm B) can be attributed independently to pruning gained on each factor, i.e., whether
`gain_total ≈ gain_factor1 × gain_factor2` (or additively in log-space) rather than an inseparable joint effect.

**Instrumentation needed (new):** this requires *ablation heuristics*, not just better logging of existing runs — you can't recover per-factor gain from a single full-heuristic run's trace alone.
- Define two ablated heuristic variants per domain:
  - Sokoban: `h_position_only` (ignores box-configuration term, e.g. just player-to-nearest-box distance), `h_boxes_only` (ignores player position, e.g. box-to-goal Hungarian/Manhattan cost with player distance dropped or fixed at a constant).
  - HP-lattice: `h_shape_only` (backbone compactness proxy, ignoring contact energy), `h_contacts_only` (contact-count estimate, ignoring backbone geometry).
- Run each ablated heuristic through the existing solver, at `w=1`, on the same instance set — this reuses the current solver and CLI unchanged; only the heuristic-function argument varies. Log `nodes_expanded` for: full heuristic, `factor1_only`, `factor2_only`, and no-heuristic baseline (already exists as a config in most such suites).
- Compute `gain_factor_i = nodes_expanded(baseline) / nodes_expanded(factor_i_only)`, `gain_total = nodes_expanded(baseline) / nodes_expanded(full)`, then test `gain_total` against `gain_factor1 × gain_factor2` (multiplicative) and `log(gain_total)` against `log(gain_factor1) + log(gain_factor2)` (additive-in-log, equivalent test, sometimes numerically nicer).
- Cost: 2 new heuristic-function variants per domain (4 total), reusing the existing solver harness and benchmark suite — no new solver logic, no new state representation, no new logging schema beyond what §0 already captures per ablated run.

---

## 4. Suggested layout

```
docs/
  equivalence/
    topology-prototype.md        <- §1, links to analysis notebook
    shared-characteristics.md    <- §2
    category-scaffold.md         <- §3, including 3.1/3.4 instrumentation spec above
analysis/
  traces_schema.py                <- §0 schema, shared by both solvers
  topology/
    disconnectivity.py            <- §1.1
    persistence.py                 <- §1.2
    morse.py                       <- §1.3
    mapper.py                      <- §1.4
    curvature.py                   <- §1.5
  shared_characteristics.py        <- §2.1–2.4
  category/
    status_labeling.py             <- §3.1 (touches solver call sites)
    transition_matrix.py           <- §3.2
    naturality_slack.py            <- §3.3
    ablation_heuristics.py         <- §3.4 (new heuristic variants + comparison)
```

This keeps every idea's analysis code separable and testable against the null model in §1's closing note before any of it is treated as a real cross-domain finding.