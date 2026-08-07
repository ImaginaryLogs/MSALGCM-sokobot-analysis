# Cross-Domain Search Structure: Synthesized Methodology

## Purpose and audience

This document is written for an agent (human or AI) picking up work on the Sokoban ↔ HP-lattice
comparative search study without having sat through the sessions that produced
`docs/DECISIONS.md`, `notebooks/cross_domain_analysis.ipynb`, and `notebooks/analysis.ipynb`. It
does three things: it fixes the terminology so "search space," "search graph," "solution graph,"
and "scaling plot" stop being used interchangeably; it defines every topology/higher-math term
that shows up in the existing analysis in plain computer-science language, with an intuitive
one-line reading attached to each; and it lays out the research question as a set of
sub-questions, each pointed at the notebook section that already answers it (fully or partially),
so a new agent can tell at a glance what exists, what's missing, and where to add work.

The standing instruction for anyone extending this project: **a reader who understands graphs,
automata, and Big-O should be able to follow every section without a topology or category-theory
background.** Where that's not yet true, fix the prose, not the reader.

---

## Terminology: four objects that keep getting conflated

Four different things have been called "the search space" across this project's discussions, and
they behave very differently, so it's worth keeping them separate in writing.

The **search space** (or **state space**) is the full space of legal states and legal transitions
for a domain, existing independently of any particular algorithm or run — every board Sokoban
could ever be in, every partial fold HP-lattice could ever produce, connected however the rules
allow. Nobody in this project has visualized this directly, because it's astronomically large; it
only matters as the abstract object that a formal correspondence claim (an isomorphism or
bijection between Sokoban and HP-lattice) would actually be a claim about.

The **search-expansion graph** (sometimes called a trace) is the much smaller subgraph that one
run of one algorithm on one instance actually visits: nodes are the specific states the solver
touched, edges are parent-to-child expansions, and each node carries a status label (expanded,
pruned, goal, frontier, and so on). Every S1/S2/S3 computation in `cross_domain_analysis.ipynb`
operates on this object, one instance at a time, before results get pooled across instances into
population statistics. This is the thing that actually gets measured; the search space is the
thing those measurements are indirect evidence about.

A **solution graph**, in the sense the WeakC4 Connect 4 video used the term, is a compressed
cross-instance *policy* structure: a graph whose branches represent an opponent's possible
responses, and whose leaves hand off to a small deterministic rule set that wins from there
without further search. This is a genuinely different object from a search-expansion graph — it's
built by generating and pruning across the whole space of possible opponent play, not by logging
one solver's single run — and it presumes an adversarial two-player structure that Sokoban and
HP-lattice, as single-agent search problems, don't have. Nothing in this project has built one of
these, and it isn't obvious a single-agent domain has a direct analog, since there's no opponent
choosing the hard branch on purpose.

A **scaling plot** is a population-level scatter with *one point per instance*, plotting some
measure of instance difficulty (crate count, monomer/chain length) against aggregate run cost
(nodes expanded, time taken). This is what the uploaded GIF
(`3d_scatter_plot_crates_nodes_made_nodes_processed_time_taken.gif`, from
`ImaginaryLogs/CSINTSY-sokobot2024`) actually is — a 3D scatter of `no_of_crates` against
`child_nodes_made` and `nodes_expanded`, colored by `time_taken`, one triangle per Sokoban
instance. It contains no graph structure at all — no per-state nodes, no edges, no topology — and
it is not a solution graph in the WeakC4 sense despite an earlier pass at labeling it that way.
It's closer in spirit to Arm A's ratio-vs-instance-size relationship than to anything in S1. Its
real contribution to this project is methodological, not visual: it puts instance size on an axis
instead of throwing that information away by pooling, which is exactly the ingredient current S1
population plots are missing (see the dedicated section below).

Keep these four separate in any write-up. "We visualized the search space" is currently not true
of anything built so far; "we visualized a search-expansion graph" and "we built a scaling plot"
are both true and should be the actual claims made.

---

## A plain-language glossary of the topology and higher-math vocabulary

Every term below appears somewhere in S1 or S3 of `cross_domain_analysis.ipynb`. Each is given a
CS-native anchor and, where the project has already produced a concrete finding using it, the
intuitive reading that finding supports — following the pattern already established for Ricci
curvature.

**Connected component / disconnectivity curve.** A connected component is just what it sounds
like in any graph course: a maximal set of nodes reachable from one another. The disconnectivity
curve sweeps a cost threshold τ upward and counts how many components exist among nodes with
`f ≤ τ` at each step — mechanically identical to the union-find sweep used in Kruskal's MST
algorithm, just applied to a threshold instead of edge weight. Intuitively: pick a maximum budget
τ, keep only the states affordable within it, and count how many disconnected islands remain.
Sokoban's curve stays pinned at a single island (AUC ≈ 1.0) at `w = 1` for a provable algebraic
reason — Manhattan distance is *consistent*, meaning every push changes `h` by exactly ±1, which
forces the total cost `f = g + h` to never decrease along any edge in the search tree, which in
turn forces every `f ≤ τ` region to already be tree-connected no matter what τ is. That floor
breaks the instant `w` moves past 1.0 in the weighted-A* sweep, confirming the algebraic argument
empirically rather than by assumption. HP's curve shows no such floor and diverges meaningfully
from a same-size random search, meaning its fragmentation is a real property of the domain's
bound-guided search, not an artifact of graph size.

**Persistent homology, β0 and β1.** β0 is the same connected-component count as above, just
computed via a slightly different machine (a Vietoris–Rips complex built by connecting nearby
points in a `(g, h, f)` embedding). β1 counts *independent cycles* — the same quantity software
engineers already know as cyclomatic complexity in a control-flow graph, here applied to the
search tree plus whatever transposition edges connect states reached by more than one move order.
"Persistence" is how large a threshold range a given component or cycle survives before merging
into something else, which is the same idea as a variable's live range in liveness analysis: a
long bar is a robust structural feature, a short one is a threshold-dependent fluke not worth
reading too much into. Concretely: Sokoban's largest instance shows 4–6 real persistent β1 bars
(genuine transposition loops — different push orders reaching the same board), while HP shows zero
at the same embedding and scale. That's a literal, measured statement that Sokoban's search graph
contains loop structure HP's doesn't, at least at the sizes tested.

**Mapper graph / fragmentation ratio.** Mapper bins nodes by a filter value (here, `f`), clusters
within each bin by graph adjacency, and counts the resulting clusters relative to nodes visited.
This is the same operation as DFA state-minimization partition refinement — grouping states into
equivalence-class-like blocks — except the bins are allowed to overlap rather than forming a strict
partition, and the point is to count the resulting blocks rather than collapse them into a smaller
machine. A high fragmentation ratio means the search visits many small, disconnected regions
rather than a few large well-connected ones. The gap here is dramatic: a 48-node Sokoban instance
already yields about 25 Mapper clusters, while HP needs an instance of 11,000+ nodes to reach a
comparably sized (~30-cluster) Mapper graph — roughly a 230x difference in how much raw search
each domain needs before its Mapper graph looks similarly fragmented, independently confirming the
disconnectivity-curve story from a different angle.

**Forman-Ricci curvature.** Computed directly from local graph structure (node degree and shared
triangles) with no embedding required — cheaper than the more common Ollivier-Ricci curvature
because it needs no optimal-transport solver. The intuitive reading, already established for this
project: **negative curvature means a more constrained region of the search space** — an edge
whose removal would disconnect a lot, the curvature analog of a graph bridge or articulation
point, meaning the search had essentially one thread of passage through that area. **Positive
curvature means a more redundant region** — an edge sitting inside a densely interconnected
cluster with many parallel routes, meaning those states carry duplicate information and could in
principle be merged or reduced without losing reachability. Both domains show broadly negative
mean curvature overall (search trees are mostly bottlenecked, unsurprisingly), but the *null-model
comparison* is where this becomes a real finding rather than a description: Sokoban's real-search
curvature is statistically indistinguishable from a same-size random walk (delta ≈ +0.05), while
HP's real-search curvature is substantially more negative than its random-walk baseline (delta ≈
−1.11). Read plainly: Sokoban's bound-guided A* isn't measurably steering into more bottlenecked
territory than random chance would, at `w = 1`; HP's guided B&B genuinely is.

**Null model.** A domain-legal but *unguided* search (uniform-random priority instead of
`f = g + w·h`), truncated to the same node count as the real trace being compared against. This is
the same idea as a random-baseline ablation in any ML evaluation — you don't get to claim a model
learned something until you've shown it beats chance. Every S1 finding above is only meaningful
because it was checked against this baseline; without it, "the disconnectivity curve looks a
certain shape" could just be "that's what a same-size chunk of this domain's raw graph looks like
regardless of guidance."

**Status transition matrix and Markov chain.** Once a node's status is logged (expanded, frontier,
pruned, goal), a transition matrix records the probability that a node of one status leads to a
child of each other status. This is exactly a Markov chain over the automaton's own status labels
— no new machinery, and the "category theory" language sometimes used for this (objects and
morphisms) can be dropped in favor of "states and transition probabilities" without losing
anything.

**KL divergence.** The standard information-theoretic distance between two probability
distributions — the same measure used to compare a language model's output distribution against a
reference. Here it compares each domain's row of the transition matrix (e.g., "given I just
expanded a node, what happens next") against the other domain's. The `expanded` row is the only
row carrying real signal (KL ≈ 0.215) since goal and pruned rows have no outgoing transitions in
either domain by construction, and the `frontier` row's reported value (0.000) has not yet been
verified to be a genuine zero rather than an artifact of how a fully-vacuous row is handled — see
the open items list below before citing that number.

**Eigenspectrum / dominant eigenvalue.** The eigenvalues of the transition matrix, same underlying
math as PageRank's stationary distribution and mixing-time analysis. A dominant eigenvalue close
to 1 means the chain is "sticky" — once in a status-behavior pattern, it tends to stay there for a
while before the second eigenvalue's gap resolves it into something else. HP's dominant eigenvalue
(0.903) is notably closer to 1 than Sokoban's (0.595), meaning HP's search settles into a
persistent local behavior pattern more readily than Sokoban's does — though this number currently
inherits whatever uncertainty exists in the frontier-row computation above, since the eigenspectrum
is computed over the full matrix.

---

## Reformatted problem statement

The project has, without always saying so explicitly, been running two claims of very different
strength side by side. The first is a **formal claim**: that a complexity-class-matched
(monotone, reversibility-free) variant of Sokoban and HP-lattice protein folding admit a genuine
structural correspondence — the actual subject of the CSINTSY thesis's six-layer framework. The
second is an **empirical claim**: that generic search-efficiency techniques transfer between the
two domains, and that their search-expansion graphs look structurally similar under population
comparison. Everything built so far — both notebooks — produces evidence for or against the
second claim. Neither notebook has touched the first, because neither operates on the monotone
Sokoban restriction the thesis argument actually requires, and neither tests a specific proposed
state-to-state mapping rather than comparing two unrelated populations.

Stated plainly, for any agent picking this up: **this project currently tests whether Sokoban and
HP-lattice search behave similarly, not whether they are formally equivalent.** A finding of
strong technique transfer or topological similarity is suggestive evidence toward the formal
claim, not proof of it; a finding of weak transfer (which is what most of the evidence gathered so
far actually shows) is equally informative evidence against a strong correspondence, consistent
with `docs/equivalence/`'s own "Level 2, weak transfer" prediction, and should be reported as a
real finding rather than treated as a shortfall.

---

## Reformatted research question and sub-questions

**Primary research question:** to what extent, and through what mechanism, do systematic
search-efficiency techniques and structural search-space properties generalize between Sokoban and
HP-lattice protein folding — two domains conjectured to share combinatorial structure but
differing in complexity class, constraint semantics, and search paradigm?

That question splits into six sub-questions, plus two more (RQ7/RQ8) added this session, pulled
directly from `docs/reference/project-proposal.md`'s supporting-question table ("Assumptions" and
"Scalability" rows) rather than the primary question's own six-way split — they'd gone unanswered
by the RQ1-6 topology framework, which characterizes each domain's structure and each technique's
efficiency ratio separately but never joins the two, and never touches `peak_frontier`/`wall_clock_ms`
scaling at all. Each row has a home in existing work; the table below is a map, not a summary — read
the methodology section that follows for the actual content of each.

| # | Sub-question | Where it's answered | Status |
|---|---|---|---|
| RQ1 | Do the two domains encode "illegal state" through comparable mechanisms? | Synthesized from `DECISIONS.md` #1, #12, #15, #19, #22 | Built — narrative section plus a rejection-type × pipeline-stage × domain taxonomy table; found Sokoban has two independent rejection mechanisms (deadlock + transposition) to HP's effectively one, not covered by the original narrative alone |
| RQ2 | Does the reachable-state topology look structurally similar, and is any similarity attributable to guidance rather than raw graph size? | `cross_domain_analysis.ipynb`, S1 + null model | Built; needs reordering (null model stated as a prerequisite, not a late addition). Size axis done (Track E, `DECISIONS.md` #23) |
| RQ3 | Do local node-level behaviors and step-to-step transition dynamics look similar? | `cross_domain_analysis.ipynb`, S2/S3 | Built; one open item (frontier-row KL) needs verification before final citation |
| RQ4 | Does tightening the heuristic/bound yield comparable efficiency gains, and what mediates the magnitude of the gain? | `analysis.ipynb`, Arm A | Built; synthesis rewritten, HP outlier table and exclusion count added (Track C, `DECISIONS.md` #24) |
| RQ5 | Does weight-relaxation (trading optimality for speed) generalize as a paradigm, or is it specific to A*-style search? | `analysis.ipynb` Arm B + `cross_domain_analysis.ipynb` weight-sweep extension | Built in two places; not yet cross-referenced into one finding |
| RQ6 | Do RQ2–RQ5's population-level findings hold for a specific proposed instance correspondence, rather than just in aggregate? | Single-pair shortcut: `25-30_Sokoban-Microban-30` / `hp_len11_0_seed42` (see below). Multi-pair: not built | Single-pair shortcut now computed with real numbers (`DECISIONS.md` #25) after `original3`/CRAMBIN turned out to be unconverged/artifact-affected. General multi-pair correspondence stays out of scope — the equivalence doc's mapping still isn't a runnable construction |
| RQ7 | What structural features of the search-expansion graph predict how much a pruning/weight-tuning technique actually saves, per instance? | `scripts/analyze_structural_pruning.py` (standalone script, not in either notebook) | Built this session (`DECISIONS.md` #26) |
| RQ8 | How do memory footprint and execution time scale with grid dimension and object count, and does pruning/weight-tuning change the scaling exponent? | `scripts/analyze_scaling.py` (standalone script, not in either notebook) | Built this session (`DECISIONS.md` #26) |

---

## Methodology by sub-question

**RQ1 — constraint and legality semantics.** This section requires no new experiments, only
writing: the evidence already exists as printed numbers spread across three decision-log entries.
The taxonomy below organizes it by **rejection type × pipeline stage × domain** — the dimension the
narrative paragraph that follows doesn't make explicit on its own, and the dimension RQ2 actually
needs, since "does illegal-state topology look similar" isn't answerable until it's clear the two
domains don't even have the same *number* of rejection mechanisms, let alone the same one.

| Rejection type | What it rejects | Pipeline stage | Sokoban | HP |
|---|---|---|---|---|
| Domain-constraint (deadlock) | a state that's legal but provably unrecoverable, independent of search quality | at successor-generation, before frontier insertion | `is_dead()` — rejects ~59% of candidate pushes (`DECISIONS.md` #15) | `connectivity_prune`, opt-in proof-of-concept — fires thousands of times on long chains but cuts `nodes_expanded` only ~0.1–0.2%; roughly halves trap rate (0.90%→0.37%) by catching dead ends earlier, at an ancestor (`DECISIONS.md` #15) |
| Search-optimality (bound) | a candidate that provably can't beat the current incumbent | continuous, at bound-check time during expansion | no separate mechanism — folded into the transposition row below | bound-prune (parity-capacity bound) — the *dominant* prune, outnumbering `connectivity_prune` 10–100x (`DECISIONS.md` #15) |
| Transposition/dominance | a **revisit** of an already-seen or now-dominated state via a worse path | at pop/reconsideration time — the closed-list skip predicate `g > stored` (ADR 0001, `DECISIONS.md` #1) | `discarded` status: `dominated_closed`, `dominated_open`, `stale_pop` (`DECISIONS.md` #19) | structurally absent — chain-growth places one monomer at a time, so no partial fold can be reached by two different placement orders (`docs/equivalence/`, `DECISIONS.md` #19) |

**Sokoban has two independent rejection mechanisms where HP effectively has one (plus a marginal
add-on)** — that asymmetry, not just the coupled-vs-decoupled framing below, is itself part of why
RQ2's topology comparison isn't a clean apples-to-apples: Sokoban's `discarded` transpositions are
exactly the mechanism that turned out to matter most this session, not as a legality concept but as
a *computational* one — `DECISIONS.md` #22's disconnectivity-curve bug existed precisely because a
`discarded` row (this row's own rejection type) could overwrite a node's real `expanded` entry in
naive per-node lookups. Any future cross-domain code that keys off "the" status of a node needs to
know this row type exists and what it means, not just that it's absent from HP.

Sokoban's `is_dead()` check rejects roughly 59% of candidate pushes, entirely independent of
heuristic quality — a crate sitting in a dead corner can still look heuristically close to its
goal, which is exactly why the deadlock check has to exist as a separate mechanism from the
heuristic. HP's situation is structurally different: its bound-based prune outnumbers its
purpose-built connectivity prune by a factor of 10 to 100, and adding the connectivity check on top
of the existing bound only reduced total nodes expanded by about 0.1–0.2%, because the
parity-capacity bound already implicitly captures most of what a separate deadlock check would
catch. The connectivity check does still measurably halve the trap rate (roughly 0.90% down to
0.37% on the tested instance slice) without moving the expanded-to-pruned transition probability —
meaning it catches the same dead ends earlier, at an ancestor node, rather than catching more of
them. The throughline for a reader: in Sokoban, "how good is the heuristic" and "how good is the
deadlock detector" are two separable knobs; in HP, they're fused into one. That distinction is the
mechanism behind RQ4's findings and belongs in the document *before* RQ2, since nothing about
"illegal state" can be compared topologically until it's been defined for each domain first.

**Scope note applying to all four sections below (RQ2–RQ5).** Every finding in this block is a
population-level or aggregate comparison (30-instance samples, whole-corpus pooling, or a single
matched-pair spot check) — a *proxy* for whether the two domains' search spaces genuinely
correspond, not a direct test of it. A direct test would need the runnable instance-to-instance
mapping RQ6 asks for, which doesn't exist yet (see RQ6 below). Read every "Sokoban and HP show
similar/dissimilar X" claim below with that caveat attached, not as a settled equivalence result.

**RQ2 — topology of the visited region.** Built and solid — and, as of this session, actually
verified rather than assumed. Sokoban's disconnectivity curve sits at a hard floor at `w = 1` for
the algebraic reason described in the glossary above, a floor that the Arm-B weight sweep confirms
empirically by showing it break the instant `w` exceeds 1.0. That "floor" claim used to rest on one
spot-checked instance (`original3`, via the null-model cell) plus an unverified population fan
chart with no printed number to check it against — a real bug in `disconnectivity_curve` (fixed
`docs/DECISIONS.md` #22, found while building the RQ5 cross-reference figure below) had been
silently inflating the population AUC for any Sokoban instance with transposition revisits, by 1-2
orders of magnitude, invisibly, because the one place the "≈1.0" number got printed happened to be
immune to the bug by accident. Re-verified after the fix: **every one of the 28 valid sampled
Sokoban curves reads exactly `1.0000`**, not approximately — the algebraic argument now has a clean
population-scale confirmation, not just a plausibility argument plus one example. HP shows a real,
non-floor-bound gap between its guided search and a size-matched random walk, on both the
disconnectivity curve and the Forman-Ricci curvature — this side was never affected by the bug (no
transpositions in chain-growth), and its population AUC spread is wide (0.61-3727, median ~11),
which is itself now a more trustworthy number than before. The Mapper-graph fragmentation gap
(roughly 230x more nodes needed for HP to reach comparable cluster counts) and the
persistent-homology β1 gap (Sokoban has real transposition loops; HP has none at tested scale) both
point the same direction from independent angles. Each of these numbers now also has a size axis
(Track E, `DECISIONS.md` #23) — see the dedicated section below — which turned out to matter:
Sokoban's curvature and branching factor both show real size trends within the sampled range, while
HP's largely don't (its one exception being disconnectivity AUC), so "pooled but roughly
constant-shape" was true for some of these metrics and false for others, not a single answer across
the board.

**RQ3 — local dynamics and transitions.** Also largely built. The status transition matrix and its
KL divergence and eigenspectrum are the right tools for "does step-to-step search behavior look
similar," and the one real finding here — HP's `frontier` status row is contaminated by a
trace-capture artifact (the solver logs a node's status post-order, after recursing into its
children, so hitting the row-count cap mid-recursion can leave a node permanently mislabeled as
`frontier` even though the real search fully expanded it) — is exactly the kind of thing worth
stating plainly rather than glossing over, since it means any cross-domain reading of the
`frontier` row specifically should be treated as unreliable, while the `expanded` row (unaffected
by this artifact) remains the trustworthy signal. Before this section is finalized, the KL
divergence computed against that same frontier row (currently printed as an exact 0.0000, while
vacuous rows like `goal` and `pruned` are correctly labeled N/A) should be traced through the code
to confirm it isn't silently treating a zero-observation row as a valid distribution.

**RQ4 — heuristic-strength transfer.** Built, and now fully verified rather than resting on a
plausibility argument (Track C, `DECISIONS.md` #24). Sokoban's manhattan-versus-Hungarian ratio
(155 of 155 eligible instances solved to equal optimal quality, mean 1.899, median 1.086, max
18.098) and HP's weak-versus-tight bound ratio (46 of 59 attempted instances, mean 1.103, median
1.022, max 1.567) were previously summarized as "comparable order of magnitude," which is true of
the medians but obscures a real and mechanistically explainable asymmetry in the tails: Sokoban's
mean is nearly double HP's, and its largest outlier is more than eleven times HP's largest outlier.
RQ1's finding explains why directly — in Sokoban a better heuristic compounds with an
independently-operating deadlock detector on contention-heavy maps, producing genuine double-digit
gains; in HP the bound already does double duty as both the heuristic and the de facto deadlock
filter, capping how much headroom a weak-to-tight switch can expose. The correct framing, now
stated directly in `analysis.ipynb` rather than left implicit here, is not "heuristic strength
transfers at a comparable magnitude" but "the *direction* of the effect transfers reliably; the
*magnitude* is domain-structural, governed by whether deadlock detection is coupled to the
heuristic or independent of it."

The two cheap additions this section previously flagged are both done, with real numbers rather
than a hypothesis: **HP's largest ratios correlate with chain length (Spearman ρ=0.76, Pearson
r=0.61), not hydrophobic density (ρ=-0.36, r=-0.23)** — unlike Sokoban's tail, which reads as a
contention effect, HP's reads as "the tight bound's advantage compounds over a longer chain,"
regardless of how H-rich it is. And **HP's denominator is 46/59 (78%), not a clean 100% the way
Sokoban's is**: of 59 attempted HP instances (54 synthetic + 5 real PDB proteins), all had both
bounds run, but 13 hit `eval_budget` on *both* bounds before solving, so no ratio could be computed
— those 13 are the 4 longest synthetic chains plus **all 5 real proteins in the dataset**. RQ4's
46-instance result is therefore a synthetic-sequence-dominated finding; none of the real proteins
this study tracks (CRAMBIN, TC5b, VILLIN, both insulin chains) are validated by it, since none of
them reach an equal-quality solve on both bounds under the current `eval_budget`.

**RQ5 — weight-relaxation transfer.** Two pieces of existing work answer this from different
angles and have not yet been placed next to each other. `analysis.ipynb`'s Arm B section reports
the cost side — Pareto curves of evaluations against solution quality across the locked weight
grid {1.0, 1.25, 1.5, 2.0, 3.0, 5.0} — for Sokoban only, since HP's B&B engine has no
weight-relaxation knob by design (trading away its optimality proof for an inadmissible bound would
be a different algorithm, not a parameter tweak, and has no equivalent literature anchor the way
Pohl's weighted-A* does for Sokoban). `cross_domain_analysis.ipynb`'s extension section reports the
shape side — how the same weight sweep, on the same three instances, affects disconnectivity AUC
— and finds the AUC floor breaks immediately at `w = 1.25`. These are the same underlying
intervention (relaxing `w`) measured on two different axes (cost, shape), on overlapping instances,
and they causally explain each other: the shape change at `w = 1.25` is the structural reason the
cost curve has the shape it does. A single combined figure putting both axes on a shared
weight-grid x-axis, using data both notebooks already computed, would make that connection
explicit instead of leaving it implicit across two documents.

**RQ6 — instance-specific correspondence.** The one genuine gap, now scoped by actually checking
both of its proposed paths rather than assuming either is open.

*The general, multi-pair path is blocked, confirmed by reading the source doc directly.*
`docs/equivalence/sokoban_hp-latice_equivalence.md`'s Layer 5 mapping (`f`/`g`/`c` in the file) is
a category-level analogy written in prose and pseudo-notation — "Box Locations → Monomer
Coordinates," "Static Walls → Dynamic self-avoidance" — not an algorithm that takes a concrete
Sokoban board and emits a concrete HP sequence (or vice versa). Its own Layer 6, "Empirical
Characteristics Comparison," is literally "To Be filled later." There is nothing runnable here yet,
so a systematic multi-pair correspondence test stays out of scope for this data collection.

*The single-pair shortcut this section previously called "cheapest available step, requiring no
new formal work" was initially attempted against `original3`/CRAMBIN — the pair decision #18's
null-model control already used, since it's the largest available trace per domain — but that pair
turned out to be blocked by two independent, checked data problems: `original3` had never been run
to a proven-optimal solve on either heuristic (`solved=cutoff` at the 2,000,000-eval cap, no
Hungarian run at all), and CRAMBIN's capped trace happened to contain zero `status=pruned` rows (a
`trace_node_cap` artifact, decision #20 — not evidence HP doesn't prune on chains this size).
Rather than re-running either instance to convergence (attempted once on real hardware, aborted —
the run crashed before completing at a 50M-eval budget), a different, already-converged matched
pair from the existing corpus was used instead, per this section's own fallback recommendation.
Both instances below were already run to a proven-optimal, equal-quality solve on both heuristic
arms in the corpus this project already has — no new runs needed.

**The replacement pair: `25-30_Sokoban-Microban-30` (Sokoban, 3 crates) and `hp_len11_0_seed42`
(HP, chain length 11).** Picked from `results/results.csv`/`results/traces` by filtering to
instances solved to equal quality on both heuristic arms with a small, uncapped trace, then
preferring an HP candidate with a non-zero pruned-row count (avoiding CRAMBIN's artifact) and a
Sokoban candidate whose pruned rate happened to land close to the ~59% population figure already
cited elsewhere in this document, for a cleaner side-by-side than an arbitrary pick would have
given:

1. **RQ4's ratio, computed for real.** Sokoban: manhattan=20 evals, hungarian=16 evals (both solve
   to `solution_quality=5`), **ratio = 1.25**. HP: weak=3,238 evals, tight=2,817 evals (both solve
   to `solution_quality=2`), **ratio ≈ 1.149**. Both sit close to their respective domain's overall
   median (Sokoban 1.086, HP 1.022, `DECISIONS.md` #24) — unsurprising for two small, unremarkable
   instances rather than tail outliers, and a useful contrast with `original3`/CRAMBIN's total
   inability to produce a ratio at all.
2. **RQ1's taxonomy extension, computed for both sides this time.** Sokoban's trace: 28 of 48
   expanded-or-pruned nodes pruned, **58.33%** — consistent with the ~59% population figure and
   `original3`'s own 59.18% instance-level number. HP's trace: 352 of 3,169 expanded-or-pruned nodes
   pruned, **11.11%** — a real, non-degenerate number this time, not the zero-pruned artifact
   CRAMBIN produced. The two numbers aren't expected to match each other (RQ1's taxonomy already
   establishes the two domains reject candidates through different mechanisms — Sokoban's deadlock
   prune and HP's bound-prune aren't the same kind of event), so the meaningful comparison isn't
   "which percentage is bigger" but "both domains now have a real, checked, non-artifact number for
   this specific matched pair," which `original3`/CRAMBIN could not provide for the HP side.

**Net effect:** the single-pair shortcut is no longer blocked — both problems that stopped
`original3`/CRAMBIN are absent for this pair, since it was selected specifically for having already
converged and having a clean trace. It's still not the general multi-pair correspondence test:
that path stays out of scope regardless of which pair is used, since
`docs/equivalence/sokoban_hp-latice_equivalence.md`'s Layer 5/6 mapping still doesn't exist as a
runnable construction. RQ2–RQ5's population-level findings remain a proxy for equivalence, not a
direct test of it, and that limitation should be stated plainly wherever those findings are
reported rather than left implicit — this single matched pair is one additional, real data point
alongside the population findings, not a replacement for them.

**RQ7 — structural predictors of pruning/weight-tuning payoff.** New this session, answered by
`scripts/analyze_structural_pruning.py` — a standalone script, not a notebook cell, since it joins
two things nothing else already joins: `results.csv`'s per-instance efficiency ratios and
trace-derived structural features. This is a different question from RQ4/RQ5's "does the ratio
transfer": RQ4/RQ5 ask whether the *magnitude* of the pruning payoff is comparable across domains;
RQ7 asks what *predicts* that payoff within a domain. Per-instance Arm A ratio
(manhattan/hungarian, Sokoban; weak/tight, HP) and Arm B ratio (w=1/w=5, Sokoban only, the same
weight-grid endpoints RQ5 uses) were correlated (Pearson + Spearman, Spearman as the primary read
since n is modest and a couple of large-map outliers can dominate a Pearson r) against five
structural features computed from each instance's baseline trace: branching factor, feasibility
ratio, trap rate, disconnectivity AUC, and mean Forman curvature — the same feature set RQ2's
population comparison and Track E's size-axis retrofit already compute, just correlated against a
different y-axis (pruning payoff instead of instance size).

Findings are domain-split and not expected to agree — RQ1's decoupled-vs-fused taxonomy already
predicts why. **Sokoban's strongest predictor of pruning payoff is graph shape, not fragmentation**:
mean curvature (Spearman ρ=-0.61 Arm A, n=155; ρ=-0.38 Arm B, n=154 — more negative/tree-like
graphs benefit more) and branching factor (ρ=+0.49 / +0.41 — more simultaneously-legal moves give
pruning more room to matter) dominate both arms. Disconnectivity AUC, despite being RQ2's headline
topology metric, barely correlates with either arm's payoff (ρ=0.18, n=144 / ρ=0.11, n=143) — a
metric can be the right tool for "do the domains look similar" (RQ2) and the wrong tool for "what
predicts this technique's payoff" (RQ7) at the same time. **HP's strongest predictor is trap rate**
(ρ=+0.75, n=46 — the largest correlation coefficient found in either domain for this question),
consistent with RQ1's fused bound-prune/heuristic mechanism: where dead ends are dense is exactly
where tightening the bound helps most. Branching factor and curvature — Sokoban's top two — are
noise-level for HP (both p>0.2). Sokoban's Arm B (w=1→w=5) median solution-quality cost on this
sample is ~0% more pushes — on this sample, the correlated weight-tuning gain isn't purchased with
a measurable quality loss at the median, though CONTEXT.md's quality-trading framing for this arm
still applies in general (it's an equal-quality arm only by coincidence on this sample, not by
construction the way Arm A is).

**Caveat**: n is capped by trace availability, not `results.csv`'s full instance count — 155/158
Sokoban Arm A pairs, 154/158 Arm B pairs, 46/59 HP Arm A pairs (the same 13-instance exclusion
RQ4/`DECISIONS.md` #24 already documents — the 4 longest synthetic chains plus all 5 real PDB
proteins, none reaching an equal-quality solve on both bounds). Full correlation table:
`results/analysis/structural_pruning_correlations.csv`.

**RQ8 — memory/time scaling vs. grid dimension and object count.** New this session, answered by
`scripts/analyze_scaling.py`. Distinct from "The missing axis" section below: that section replots
*topology* metrics (curvature, disconnectivity AUC, branching factor, …) against instance size;
RQ8 instead fits log-log power laws (`y = a·x^b`) for the two *cost* metrics STATUS.md's
Measurement section names as the memory/time proxies — `peak_frontier` and `wall_clock_ms` —
against `grid_cells` (Sokoban board area) and `instance_size` (crate count / chain length),
separately per technique config, so the fitted exponent `b` is directly comparable across baseline
vs. optimized runs — a technique that "reduces exploration time as scale grows" should show up as
a smaller `b`, not just a lower intercept.

Sokoban (n=155 instances per config, deduped — see data-integrity note below): both cost metrics
scale super-linearly, and crate count matters more than board area (partial regression isolating
each axis: `peak_frontier ~ grid_cells^2.56 · instance_size^3.96`, `wall_clock_ms ~
grid_cells^3.37 · instance_size^4.18`, both at baseline w=1 manhattan). Pruning/weight-tuning
monotonically **flattens every exponent** rather than only shifting the intercept:
`wall_clock_ms` vs. `instance_size` goes 4.65 (baseline) → 3.93 (hungarian, w=1) → 3.71 (manhattan,
w=5); vs. `grid_cells`, 4.13 → 3.87 → 3.57. That's a direct, quantitative answer to "does
state-pruning/weight-tuning reduce exploration time as scale grows": yes, and it does so by
reducing the growth-rate exponent itself, not merely applying a constant-factor speedup at every
size.

HP-lattice has no grid axis — the search is over an unbounded lattice, not a fixed board
(`src/protein-fold/bnb_cli.py` sets `grid_cells="NA"` for every HP row, `DECISIONS.md` #10).
`peak_frontier ~ instance_size^1.00` with R²=1.000 exactly, under both bounds (n=46 each) — the
B&B engine's frontier is deterministically equal to chain length, a genuinely different, degenerate
scaling shape from Sokoban's priority-queue-dependent frontier, worth stating as a domain-structural
fact rather than a numerical coincidence. `wall_clock_ms` scales far steeper than Sokoban's (b≈7.07
weak, 7.35 tight) and heuristic strength barely moves the exponent — consistent with RQ4's already
small HP effect size.

**Data-integrity fix, applies beyond RQ8.** While building this, found `results/results.csv`
contains duplicate re-run rows for ~155/158 Sokoban baseline instances — repeated
`scripts/run_experiments.py` invocations appended to the same CSV, the same pattern
`scripts/analyze_arms.py`'s `arm_b_pareto` already documents and dedupes for. Undeduped, this
silently inflates any naive `len(rows)`-based sample-size count ~2x for nearly the whole Sokoban
corpus without biasing a fitted slope (the duplicate rows sit on/near the same point — confirmed by
comparing fits before/after the fix, exponents changed by <0.02 across the board).
`scripts/analyze_scaling.py` dedupes to last-row-per-instance before fitting; any future script
reading `results.csv` directly for per-instance analysis should do the same rather than assume one
row per instance. Full fit table: `results/analysis/scaling_fits.csv`.

---

## The missing axis: scaling by instance size

The uploaded GIF is a scaling plot from the Sokoban engine's own repository, not a solution graph
and not a search-expansion graph — it plots `no_of_crates` against `child_nodes_made` and
`nodes_expanded`, colored by `time_taken`, one point per Sokoban instance, with no per-state graph
structure represented at all. Visually, the three axes form a near-diagonal sheet: crate count,
nodes made, and nodes expanded are all highly collinear with each other, meaning two of the three
spatial axes are largely confirming the same trend rather than each contributing independent
information. That's worth remembering as a design lesson for any future plot in this style: put
size on one axis and a genuinely different quantity (a topology metric, a ratio) on the other,
rather than stacking two correlated cost measures.

Its real contribution to the methodology is what it does *not* throw away. Every population metric
currently reported in S1 and S2 — disconnectivity AUC, β1 bar count, curvature, fragmentation
ratio, branching factor, feasibility ratio, trap rate — and every Arm A ratio, is already computed
per instance before being pooled into a single boxplot or a single mean/median pair per domain.
That pooling discards instance size entirely, which means the current methodology cannot currently
distinguish two very different stories that would otherwise look identical: a domain whose
topology genuinely changes as instances get harder, versus a domain whose population spread is
just noise around a size-independent baseline. Since every per-instance value already exists keyed
to an instance ID before it gets pooled, the fix is a plotting change, not a new experiment: replot
each population metric against `instance_size` (crate count for Sokoban, chain/monomer length for
HP, each normalized to its own domain's range since the two aren't the same unit) instead of
collapsing it into a single boxplot. This applies directly to RQ2, RQ3, and RQ4 as described in
each section above, and should be treated as a standing addition to those sections rather than a
separate new S-section, since it re-scopes existing metrics rather than introducing new ones.
Before building this for HP, confirm the `instance_size` column in the D6 schema is actually
populated with a meaningful chain-length value for HP rows rather than left `NA` the way
`grid_cells` was — `DECISIONS.md` #4 (`instance_size` = crate count) and #10 (`grid_cells`="NA" for
HP) suggest it should be, but this hasn't been directly verified.

**Resolved this session (Track E, `DECISIONS.md` #23).** `instance_size` was already fully
populated for HP (0/136 rows `NA`), so no emission fix was needed. All six population metrics
listed above (plus Arm A's ratio, already done in `analysis.ipynb`) now have a real per-instance
scatter against normalized `instance_size` in `cross_domain_analysis.ipynb`. The two stories this
section worried about being indistinguishable turned out to both occur, split by domain and
metric rather than uniformly: Sokoban shows genuine, often strong size trends for curvature
(Spearman ρ=-0.84) and branching factor (ρ=0.68), consistent with its topology actually changing
shape as crate count grows; HP shows almost no size trend for the matching metrics (branching
factor pinned near its lattice ceiling regardless of chain length, fragmentation ratio flat), with
disconnectivity AUC as the one exception (moderate positive rank correlation, ρ=0.61). Full
per-metric numbers are in Track E's checklist entry above — this reads as a real cross-domain
asymmetry in how much a metric's population spread is actually explained by size, not settled in
one direction for "the methodology" as a whole.

---

## Standing priorities for anyone extending this work

When a choice exists between adding another summary statistic and building one clear, well-captioned
figure, build the figure. A reader who already understands graphs and automata will get more from
one plot with a plain-language paragraph explaining what it shows and why than from a table of
additional p-values. Every topology or higher-math term introduced anywhere in this project should
be defined the way the glossary above defines Forman-Ricci curvature: a CS-native anchor first,
then a one-sentence intuitive reading a reader can actually use to interpret a number without
re-deriving the math. If a new metric gets added and no such intuitive reading has been found for
it yet, that's a sign the metric isn't ready to be reported as a finding — find the reading before
publishing the number, not after.

---

## Parallel task list

The items below are grouped so multiple agents can work simultaneously where possible. Items within
a track are mostly sequential; tracks themselves are largely independent of each other except where
noted.

**Track A — RQ1 write-up (done this session)**
- [x] Draft the constraint-semantics taxonomy section (rejection type × pipeline stage × domain),
      pulling directly from `DECISIONS.md` #1, #12, #15, #19; no new computation needed. Found a
      third rejection type the original narrative-only paragraph didn't name explicitly: Sokoban's
      transposition/dominance `discarded` status has no HP analog, on top of the deadlock-vs-bound
      asymmetry already covered — Sokoban has two independent rejection mechanisms to HP's one.
- [x] Placed before RQ2/S1 (it already was, textually; the taxonomy table now leads that section).

**Track B — Verification pass on RQ3 (done this session)**
- [x] Traced the KL-divergence code path: the printed `0.0000` for the `frontier` row was a
      masking artifact, confirmed against the executed matrix (Sokoban's frontier row is genuinely
      all-zero; HP's isn't — `0.276 0.711 0.013 0.000`, the `#20` `trace_node_cap` artifact). Fixed
      the notebook's N/A guard to a three-way check (both-vacuous / one-sided-vacuous / real KL);
      re-executed, now correctly prints `N/A (one-sided vacuous...)`.
- [x] Eigenspectrum numbers (0.595 Sokoban, 0.903 HP) are unchanged by the fix — confirmed they
      still inherit whatever uncertainty `#20`'s frontier-row content artifact carries, since
      `eigen_spectrum` runs over the full matrix regardless of how the KL cell labels that row.

**Track C — RQ4 additions (done this session, `DECISIONS.md` #24)**
- [x] Build an HP top-10 outlier table mirroring the existing Sokoban table (same
      `sorted(...)[:10]` pattern applied to `hp_ratios`), and check whether HP's largest ratios
      correlate with chain length or hydrophobic density. Added to `analysis.ipynb`, joined against
      each instance's H/P sequence (synthetic FASTA files read directly; the 5 real PDB proteins
      converted via `utils.convert_to_hp`, mirroring `bnb_cli.py`'s own `to_hp_sequence` fallback).
      **Correlates with chain length (Spearman ρ=0.76, Pearson r=0.61), not hydrophobic density**
      (ρ=-0.36, r=-0.23, density range 0.0-0.90 on the 46-instance sample) — the opposite of
      Sokoban's contention-driven tail.
- [x] Determine and state HP's Arm A exclusion count: how many attempted HP instances did not reach
      equal-quality solves under both bounds, and why, alongside the existing clean 155-of-155
      Sokoban figure. **46/59 (78%)** — all 59 attempted instances had both `weak` and `tight` rows
      present, but 13 hit `eval_budget` cutoff on *both* bounds before solving: the 4 longest
      synthetic chains (length 17-20) plus **all 5 real PDB proteins** (`1CRN`/CRAMBIN, `1L2Y`,
      `1VII`, both `4INS` chains). No partial-arm cases (never "only weak" or "only tight" run).
- [x] Rewrite the Arm A synthesis paragraph to state the mean/median/max numbers explicitly and
      frame the asymmetry via RQ1's coupled-versus-decoupled deadlock-detection mechanism, replacing
      the current "comparable order of magnitude" framing. Rewrote both `analysis.ipynb`'s
      "Does heuristic strength transfer?" cell and its final Summary cell; re-executed end-to-end,
      0 errors, output numbers match the standalone verification above exactly.

**Track D — RQ5 cross-reference (done this session)**
- [x] Built the combined figure (`2-11`, `52-13`, `53-44`, shared `w`-axis, cost top / shape
      bottom). It surfaced a real, previously-unknown bug in `analysis/topology_lite.py`, not a
      replot issue: `disconnectivity_curve`'s node lookup could silently keep a `discarded`
      transposition row's stale, worse `f` over a node's real `expanded` entry, inflating AUC by
      1-2 orders of magnitude for any Sokoban instance with revisits. Fixed (`DECISIONS.md` #22)
      and re-verified at population scale (all 28 valid sampled Sokoban curves now read exactly
      `1.0000`, not just the two previously spot-checked instances). The combined figure now shows
      all three instances at exactly `1.0` at `w=1`, breaking the instant `w` exceeds 1 — the
      existing narrative's claim, now backed by correct numbers instead of a plausibility argument.

**Track E — Scaling-axis retrofit (done this session, `DECISIONS.md` #23)**
- [x] Confirm whether the D6 schema's `instance_size` column is populated for HP rows with a
      meaningful chain/monomer-length value, or left `NA`; fix the emission path if the latter.
      **Already correct** — checked `results/results.csv` directly: 0/136 HP rows are `NA`, range
      3-46. No emission-path fix needed.
- [x] Add an `instance_size` join to the `pop_data` structure in `cross_domain_analysis.ipynb` so
      each per-instance metric (disconnectivity AUC, β1 count, curvature, fragmentation ratio,
      branching factor, feasibility ratio) can be plotted against normalized instance size rather
      than only pooled into a boxplot. Added `instance_id_of()` (`analysis/trace_io.py`, verified
      against all 217 real trace files, 0 misses) plus `size_of()`/`scatter_by_size()` helpers, then
      one scatter cell per metric (all six, including the two S2 node-pooled ones which needed a new
      per-instance mean computed over the same `pop_by_domain` sample rather than reusing
      `agg_by_domain`'s whole-corpus pooling). Real findings, not placeholders — population sample
      of 30/domain, so directional, not a scaling law:
      - Sokoban's disconnectivity AUC is flat at exactly `1.0` across its whole sampled size range,
        as the `w=1` consistency argument predicts (no size dependence to find). HP's AUC has a
        moderate positive rank correlation with size (Spearman ρ=0.61 on n=27; Pearson r=0.10,
        weak, pulled around by high-AUC outliers).
      - HP's β1 (persistent-loop) bar count is **exactly 0 for all 30 sampled instances at every
        chain length 3-36** — a domain-structural fact (no transpositions in chain-growth), not a
        size effect. Sokoban's β1 has real variance (0-111 bars) but no clean size trend (Spearman
        ρ=-0.22).
      - Neither domain's Mapper fragmentation ratio trends with size (Sokoban ρ=0.40, HP ρ=-0.04,
        both weak) — the large single-instance gap noted elsewhere in this doc looks like
        per-instance/domain spread, not something size explains.
      - Sokoban's mean Forman curvature has a strong negative size trend (Pearson r=-0.85, Spearman
        ρ=-0.84: bigger instances' search graphs get more tree-like). HP's curvature-vs-size signal
        is weak and internally inconsistent (Pearson/Spearman disagree in sign) — no confident
        trend.
      - Sokoban's mean branching factor rises with size (Pearson r=0.69, Spearman ρ=0.68, structural
        — more simultaneously-pushable crates). HP's stays pinned near its lattice ceiling (≤3)
        across the whole 3-36 chain-length range — no real size trend, and Pearson/Spearman
        disagree in sign there too.
      - Feasibility ratio is only weakly size-associated in both domains (Sokoban ρ=0.21, HP
        ρ=0.21), with HP's mean (0.95) sitting well above Sokoban's (0.82) at every size sampled —
        consistent with HP's real filtering happening elsewhere (silent self-avoidance), not in
        this ratio.
- [x] Add the same size join to Arm A's ratio output in `analysis.ipynb`. **Already done** — read
      `notebooks/analysis.ipynb` cells 3 and 7 directly: both the Sokoban and HP Arm A ratio plots
      already use `instance_size` as the x-axis. No new work needed.

**Track F — RQ6 scoping (fully resolved this session, including both follow-ups, `DECISIONS.md` #21/#25)**
- [x] Determine whether `docs/equivalence/sokoban_hp-latice_equivalence.md`'s proposed mapping
      exists as a runnable construction. **No** — its Layer 5 mapping is prose/category-level, Layer
      6 is unwritten. Multi-pair RQ6 stays out of scope.
- [x] Check whether the `original3`/CRAMBIN pair supports the "cheapest available step" extension
      as this section previously claimed. **No, for two independent reasons, both verified against
      `results/results.csv` and the trace files directly**: neither instance has a proven-optimal
      solve on both heuristic arms (blocks RQ4's ratio), and CRAMBIN's capped trace has zero
      `pruned` rows (blocks RQ1's HP-side number) — see the RQ6 section above for the numbers.
      Sokoban's RQ1 number (59.18% pruned, `original3`) is real and now stated there.
- [x] Reopened this session (`DECISIONS.md` #25). A real re-run of `original3` with Hungarian was
      attempted first at a 50M-eval budget on other hardware and crashed before completing — rather
      than debug that, took this section's own fallback: picked a different matched pair already
      solved to proven optimality on both heuristic variants from the existing corpus,
      `25-30_Sokoban-Microban-30` / `hp_len11_0_seed42`. Both blockers are resolved for this pair —
      RQ4 ratios computed (Sokoban 1.25, HP ≈1.149) and RQ1's HP-side pruned rate is a real non-zero
      number (11.11%, vs. Sokoban's 58.33%) — see the rewritten RQ6 section above for the full
      numbers. The general multi-pair path is still out of scope; only the single-pair shortcut was
      reopened.
- [x] Scope note for RQ2–RQ5 write-ups: state plainly that population-level findings are a proxy
      for equivalence, not a direct test of it, per the resolution above. Added as a shared note
      immediately before the RQ2 section (applies to RQ2–RQ5 collectively, rather than repeating the
      same sentence four times).

**Track G — RQ7/RQ8 added (done this session, `DECISIONS.md` #26)**
- [x] Confirm neither of `docs/reference/project-proposal.md`'s "Assumptions"/"Scalability"
      supporting questions was already answered anywhere in `docs/` or `notebooks/`. Checked by
      grepping for their key phrases ("structural feature", "movable object", "grid dimension")
      across both — no hits outside the proposal table itself.
- [x] Build `scripts/analyze_structural_pruning.py` (RQ7): joins Arm A/B per-instance efficiency
      ratios from `results.csv` against structural features computed from each instance's baseline
      trace via the existing `analysis/` modules (`shared_characteristics.py`, `topology_lite.py`,
      `curvature.py` — no new feature-computation code written, only new correlation/join code).
      Findings above; correlation table at `results/analysis/structural_pruning_correlations.csv`.
- [x] Build `scripts/analyze_scaling.py` (RQ8): log-log power-law fits of `peak_frontier` /
      `wall_clock_ms` against `grid_cells` / `instance_size`, per technique config. Findings above;
      fit table at `results/analysis/scaling_fits.csv`.
- [x] Found and fixed a real data-integrity issue while building RQ8: duplicate re-run rows for
      ~155/158 Sokoban instances in `results.csv`, silently inflating naive sample-size counts.
      Deduped in `analyze_scaling.py`; `analyze_arms.py`'s Arm B already had the same fix, `analyze_
      structural_pruning.py`'s dict-keyed joins were already immune (last-row-wins by construction).
