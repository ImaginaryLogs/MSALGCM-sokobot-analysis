# Decisions

Append-only dated log of resolved project decisions. Single source of truth — `HANDOFF.md`,
`STATUS.md`, and `docs/plans/*.md` link here instead of repeating content. Big
algorithm/architecture/module-boundary calls get their own `docs/adr/NNNN-title.md`; this file
links out to those and keeps a one-line summary.

## 2026-07-17

1. **Sokoban port target:** Python, into `src/sokoban/`. Solver + headless loader + data emit
   only — no GUI. Java oracle removed from wk1, replaced by pure-Python `validator.py` (validity
   replay + small-map UCS optimality oracle asserting `w=1` == BFS `Q*`); Java oracle
   optional/deferred. Java-wrap remains the fallback if wk1 slips.
2. **Technique scope (revised via grill):** two headline arms — **heuristic weight tuning**
   (`w>1`, quality-trading → Pareto curve) + **heuristic strength** (Manhattan vs Hungarian `h` @
   `w=1`, optimality-preserving → scalar ratio). Symmetry pruning **dropped** as headline (board
   symmetry rare in real maps → ~null ratios; optional stretch only). Macro-graph tunnel
   abstraction remains stretch.
3. **Task split:** CJ = Sokoban, Roan = HP, Enzo = lit review + shared harness + paper assembly.
4. **Measurement:** paradigm-neutral effort unit. Log BOTH `nodes_expanded` and
   `candidates_scored` — cross-domain join-key choice **provisional**, pending Roan's HP engine
   (Metropolis 1-eval/proposal ↔ `candidates_scored`; NMCS nested playout / B&B expansions ↔
   `nodes_expanded`). Efficiency reporting split: scalar ratio only for the optimality-preserving
   arm (equal quality), Pareto curve for the weighted arm (no scalar). Primary stop = eval budget
   `N` (reproducible); wall-clock = hang-safety only, `cutoff_reason` logged. `instance_size` =
   crate count. Secondary metrics: TTS, peak frontier size.
5. **Lit review split:** distributed by domain — each builder annotates their own 4 papers, Enzo
   sources the missing textbooks/conf pubs and writes the synthesis. Due Jul 24.
6. **Sokoban port architecture:** Weighted A* + closed list, `f=g+w·h`, closed-list skip predicate
   is strict `g > stored`. Full rationale: [ADR 0001](adr/0001-sokoban-search-algorithm.md). Full
   build spec: [`docs/specs/sokoban-port-plan.md`](specs/sokoban-port-plan.md).

## 2026-07-18

7. **HP engine confirmed: B&B chain-growth.** Roan resolved the 48h-fuse ENGINE DECISION. Full
   rationale: [ADR 0002](adr/0002-hp-engine-bnb.md).
8. **Cross-domain join key locked: `nodes_expanded`.** No longer provisional (was pending the HP
   engine choice, decision 4). B&B expansions map to `nodes_expanded`, not `candidates_scored`.
   `candidate_states_evaluated` (D6 schema) now populates from `nodes_expanded` by default.
   `candidates_scored` still logged (cheap, D5) as a secondary counter, not the join key.

9. **Phase-2 experiment plan locked** (grill session, full record in git history of
   `docs/plans/sokoban-phase2-experiments-plan.md`, deleted on resolution per docs-management
   rule):
   - **Map suite fixed: 155 maps, not 19.** `build_map_suite.py` only ever scanned
     `maps/_all/` — `CSINTSY-sokobot2024/maps/sokoban-info/` (2716 classic XSokoban-format maps,
     loader-compatible) was never fed in. Sampled every 10th file (272 candidates) into `_all/`,
     reran the D2 filter (timeout raised 300s→60s per-map for the rerun's practicality) → 155
     suite-eligible maps, crate counts 1–11+. `EXCLUDED.md` regenerated (152 excluded).
   - **D6 CSV schema still DRAFT** (pending Enzo sign-off) — running real data against it anyway;
     Sokoban side is deterministic so a re-run is cheap if columns shift.
   - **Eval budget locked: `N=2,000,000`** (candidate_states_evaluated / `nodes_expanded` join
     key). Set from a full-155-map sweep at `w=1` manhattan: observed max `candidates_scored`
     was 975,695 — `N` is ~2x headroom above that, not the old untested `1,000,000` CLI default.
   - **Arm A (heuristic strength):** manhattan vs hungarian, `w=1` fixed, scalar ratio (D8) —
     code-ready, no design left.
   - **Arm B (weight tuning):** manhattan **only** (no cross with hungarian — keeps the two arms
     independent variables; a hungarian×weight cross is optional stretch). Weight grid:
     `{1.0, 1.25, 1.5, 2.0, 3.0, 5.0}`, dense near 1.0 where quality degrades fastest. Revisit
     grid after CJ's Korf/Junghanns lit-review annotations if their bounded-suboptimal values
     suggest otherwise.
   - **Batch runner:** `scripts/run_experiments.py` — in-process (no subprocess-per-cell),
     imports `solver.py`/`emit.py` directly, one shared CSV. `cli.py` stays the single-run/debug
     entry point. The `(manhattan, w=1.0)` cell is shared by both arms and only run once.
     Smoke-tested on 2 maps × 7 configs (2026-07-18) — dedup and weight/heuristic behavior
     verified correct; full 155-map run not yet executed (separate data-collection step).

## 2026-08-03

10. **HP B&B solver built: `src/protein-fold/bnb.py`.** Depth-first chain-growth per
    `docs/representations/hp-lattice-folding_representation.md` Layers 1-4, `BnBResult`
    counter-shape mirrors Sokoban's `SolveResult` (`nodes_expanded`, `candidates_scored`,
    `peak_frontier`, `wall_clock_ms`, `solved`/`cutoff_reason`) so runs join on
    `nodes_expanded` per ADR 0002.
    - **Bound formula corrected from the representation doc's literal Layer 4 text.** The
      doc's `h(n) = min(unplaced_odd_H, unplaced_even_H)` (counting monomers, 1 unit each)
      is unsound: verified by brute-force cross-check (`tests/test_bnb.py`) that it (a)
      ignores contacts between an unplaced monomer and an already-placed one, and (b) caps
      each unplaced monomer's contribution at 1 when a monomer can be party to >1
      simultaneous contact. Both undercounted reachable contacts and pruned true optima
      (e.g. "HHHH", "HPHPPH"). Fixed by summing structural contact *capacity* (2 interior /
      3 chain-end monomers) instead of counting monomers, on both the unplaced side
      (precomputed suffix sums) and the placed side (`po_free`/`pe_free` running totals,
      O(1)-incremental). Full derivation in `bnb.py`'s module docstring.
    - First-turn mirror-symmetry break (Layer 4) implemented as specified, no correctness
      issue found.
    - CSV emission: `src/protein-fold/bnb_cli.py` reuses `sokoban.metrics.CSV_COLUMNS`
      directly (single canonical schema, not a duplicate registry) — `domain=hp_lattice`,
      `algorithm=bnb`, `base_h=parity`, `weight_w`/`seed`/`grid_cells`="NA" (not applicable
      to this engine).
    - Added `pyyaml` to `pyproject.toml` — `config.py` already imported it unconditionally
      but it was never declared as a dependency.

11. **Opt-in capped per-node trace added to both solvers**, as a low-risk pilot of
    `docs/equivalence/cross-domain-analysis-design.md` §0, ahead of committing to that
    doc's full instrumentation rewrite (which is out of scope before the Aug 7 submission —
    treat cross-domain-analysis-design.md as post-submission stretch work, not part of the
    Phase 3/4 plan). `trace=True` (default off, zero behavior/perf change otherwise) +
    `trace_node_cap=100_000` (rows capped independently of `eval_budget`; the search itself
    always runs to its normal stopping condition, only trace accumulation stops) on both
    `sokoban.solver.solve()` and `bnb.solve()`.
    - Gives EXPANDED/GOAL for free (already known), and PRUNED near-free by reusing each
      solver's existing constraint-rejection branch (Sokoban: `board.is_dead()`; HP: the
      bound-prune) rather than adding new call sites.
    - §3.1/§1.3's suggested live TRAP check (`min(successor f) >= current f`) was tried as
      literally specified and found to be noise, not signal: under a *consistent* heuristic
      (Manhattan/Hungarian both are — one push changes h by exactly ±1) f is non-decreasing
      along nearly every edge by construction, an ordinary A* property, not search
      difficulty — it fired on 8/9 nodes on a trivial fixture. Replaced with two honestly-
      separated, differently-named columns instead of one misleading "trap" label:
      `all_pruned` (every successor domain/bound-rejected — rare, genuinely meaningful) and,
      Sokoban-only, `f_plateau` (the naive check, uninformative at w=1, becomes real signal
      at w>1 once weighting breaks strict f-monotonicity — verified empirically). HP has no
      `f_plateau` analog: a DFBnB candidate that survives the bound-prune is by construction
      already better than the incumbent, so "legal but not improving" isn't a state that
      exists there the way Sokoban's separate dedup/deadlock gates allow.
    - HP's "pruned" is semantically different from Sokoban's: Sokoban's is a domain-
      constraint rejection (`is_dead`); HP's is search-optimality (bound-prune) — HP's actual
      domain constraint (self-avoidance) is enforced silently at candidate generation with no
      rejection event to log. Any cross-domain PRUNED comparison needs to account for this.
    - True per-node FRONTIER (states generated but neither expanded nor pruned) is NOT
      covered — would need a log call at every generation regardless of outcome, which
      neither solver's loop has a free branch for. `peak_frontier` (already in the D6
      summary schema) remains the only frontier-size signal without that added cost.
    - Full derivation and empirical findings: module docstrings in `solver.py` / `bnb.py`;
      tests in both `tests/test_sokoban.py::TraceTests` and `tests/test_bnb.py::TraceTests`.

12. **Arm A/B analysis (`scripts/analyze_arms.py`) and S1/S2/S3-lite cross-domain analysis
    (`analysis/` package + `scripts/analyze_traces.py`) built**, both driven by data that
    already existed (`results.csv`, `results/traces/*.csv`) — `notebooks/analysis.ipynb`
    was found empty (Phase-2 data genuinely not yet analyzed, matching HANDOFF.md).
    - Arm A/B script computes Arm A's scalar efficiency ratio (manhattan vs hungarian, w=1)
      and Arm B's Pareto curve (manhattan, weight grid), Sokoban-only — noted plainly that
      HP's `bnb` engine has neither a heuristic-strength nor weight-w knob, so it can't
      populate either arm as STATUS.md's original both-domain Arm B framing intended.
    - Cross-domain lite pieces (§0 in `analysis/topology_lite.py` / `shared_characteristics.py`
      / `category_lite.py`): S2.1/2.2/2.4 (branching factor, feasibility ratio, plateau runs)
      read existing trace columns directly; S1.3 (trap rate) aggregates `all_pruned`; S1.1-lite
      (disconnectivity curve) is a union-find sweep over `f`, sampled to the largest few
      instances per domain (heavier, per-instance); S3.1/3.2 (transition matrix + KL
      divergence/eigenspectrum) derives transitions from `parent_id` joins post-hoc. S1.2/1.4/1.5
      (need ripser/giotto-tda/kmapper/GraphRicciCurvature, none installed) and S3.3/3.4 (need a
      cost-to-go oracle / new ablated heuristic variants + reruns) remain deferred, per the
      original scope decision.
    - **Three bugs found and fixed by actually running this against real data**, not just
      unit tests: (1) Arm B's Pareto grouping counted duplicate re-runs at the same `w` as a
      2-point curve — fixed to require *distinct* weights. (2) `bnb.py`'s trace never logged a
      `status="pruned"` row for bound-pruned candidates (only tallied `n_pruned` on the parent),
      unlike Sokoban's trace — so every cross-domain S3.2 comparison silently skipped ("status
      sets differ"). Fixed to log one row per pruned candidate, mirroring Sokoban. **Trace CSVs
      generated before this fix are missing HP `pruned` rows and should be regenerated** if
      S3.2 output is needed from them. (3) `analysis.trace_io.domain_of` inferred HP vs Sokoban
      from an `hp_`-prefixed filename — true only for `generate_hp_sequences.py`'s own naming,
      silently wrong for raw sequences (`seq0`) or `--fasta`-derived labels (real download
      instance names). Fixed to read the header's column set instead (`f_plateau` is
      Sokoban-only, `is_new_best` is HP-only) — a structural signal, not a naming convention.
    - Verified end-to-end against the real 220-file / 6.6M-row trace corpus already in
      `results/traces/` (full run: ~70s) and a small live Arm A/B sweep.

13. **HP heuristic-strength baseline added: `bnb.solve(..., bound="weak"|"tight")`.** Decided
    only heuristic-strength gets an HP analog, not weight-w: ADR 0002 picked B&B specifically
    because it's a complete, optimality-proving search matching Sokoban's paradigm at `w=1`;
    a "weight" knob would mean trading that proof away for an inadmissible bound, which isn't
    a parameter tweak but a different algorithm, with no equally-established literature anchor
    the way Weighted A* (Pohl 1970) has for Sokoban. Weight-tuning (Arm B) stays Sokoban-only —
    a finding to report ("one technique transfers, the other is A*-specific"), not a gap.
    - `bound="tight"` (default, unchanged behavior) = the existing real-time free-slot-tracked
      bound. `bound="weak"` substitutes each already-placed monomer's *static* structural
      capacity (`_contact_capacity`, precomputed once as a prefix-sum array, mirroring the
      existing suffix arrays) for the real-time-tracked `po_free`/`pe_free`. Since true
      remaining free-slot count can never exceed static structural capacity, `weak >= tight`
      always — a strictly looser but still-admissible bound, not a different (unsound) formula,
      so both provably reach the same optimum, mirroring Sokoban's manhattan-vs-hungarian
      exactly (equal quality, different cost). Both bound functions share one dispatch table
      (`_BOUNDS`) selected by the new `bound` parameter; the per-node bound computation was
      refactored into `bound_tight`/`bound_weak` functions taking a shared `ctx` dict rather
      than closing over module state, so both reuse the exact same trace/pruning call sites.
    - Re-verified against the brute-force oracle for BOTH bound values on every existing test
      sequence (`tests/test_bnb.py`), plus a new invariant test asserting `weak.nodes_expanded
      >= tight.nodes_expanded` at equal quality whenever both solve. Live-verified on a real
      14-mer: tight=221,575 nodes, weak=235,739 nodes, both quality=6 (proven optimal) —
      ratio ≈1.06, same ballpark as Sokoban's manhattan/hungarian ratio on small maps (≈1.0–1.14).
    - `bnb_cli.py --bound {tight,weak}` (default tight) sets `base_h` in the D6 row to the bound
      name (previously always the placeholder `"parity"`). `scripts/analyze_arms.py` generalized
      from a Sokoban-only `arm_a_scalar_ratio` to a domain-generic `heuristic_strength_ratio`,
      now reporting both Sokoban's and HP's Arm A side by side from the same `results.csv`.

14. **Two notebooks built** (`notebooks/analysis.ipynb`, `notebooks/cross_domain_analysis.ipynb`),
    executed end-to-end against real project data via `jupyter nbconvert --execute` (not shipped
    with empty/stale outputs) — `notebooks/analysis.ipynb` was found completely empty, despite
    being STATUS.md's expected Phase-3 deliverable. Both reuse `scripts/analyze_arms.py` /
    `analysis/*` functions rather than reimplementing logic, so the notebook numbers are exactly
    what the CLI scripts report.
    - Two execution-only bugs fixed along the way (data/logic were already correct):
      `plt.show()` doesn't embed under nbconvert's default backend without `%matplotlib inline`;
      and `analyze_arms.py`'s module-level `matplotlib.use("Agg")` silently overrides that magic
      if imported *after* it — fixed by importing first, then re-asserting inline.
    - `cross_domain_analysis.ipynb` then extended to cover the **rest of S1** (S1.2 persistent
      homology, S1.4 Mapper, S1.5 Forman-Ricci curvature — previously deferred for lacking
      `ripser`/`kmapper`/`GraphRicciCurvature`; all three now installed, in the `notebooks`
      dependency group since they're exploratory-analysis-only, not needed by any core solver).
      New modules: `analysis/persistence.py`, `analysis/mapper.py` (implemented directly rather
      than via `kmapper`, since the doc calls for graph-adjacency clustering within each filter
      interval, not `kmapper`'s default Euclidean clusterer — reuses S1.1's union-find),
      `analysis/curvature.py`.
    - **Three more real bugs found by actually running this against real data**: (1) a bug in
      the third-party `GraphRicciCurvature` library itself — its debug-logging path does
      unconditional `%d`-style formatting on node ids, crashing outright on our string ids
      regardless of log level; worked around by relabeling to integers before calling it and
      mapping results back. (2) `mapper_graph`'s edge-detection was O(n_clusters²) pairwise
      set-intersection — fine on small instances, didn't finish in 5+ minutes on a ~100k-node
      trace with 10,000+ clusters; fixed to an inverted-index approach, O(total membership
      entries) instead — same result, ~1-2s. (3) Even after that fix, the largest instance per
      domain produces 14,000-63,000 Mapper clusters, nowhere near plottable — discovered that
      Sokoban's induced subgraph is fragmented enough that even a 48-node instance yields ~25
      clusters, while HP needs an 11,000+-node instance to reach a comparably-sized (~30-cluster)
      Mapper graph. That ~230x gap is itself a real, if informal, cross-domain finding (consistent
      with S1.1's disconnectivity curve and S2.1's branching-factor spectrum from a different
      angle) — not a bug, but it meant hand-picking small, legibility-tuned instances for S1.4's
      plot rather than reusing S1.1/S1.3's "largest instance per domain" convention; documented
      inline in the notebook so the plotted instances aren't mistaken for representative ones.

15. **HP connectivity pruning built as a proof of concept (`bnb.solve(..., connectivity_prune=True)`,
    default off) — sound and transferable in principle, but empirically marginal.** The idea
    (docs/DECISIONS.md #12's PRUNED-asymmetry finding, and the "what Sokoban pruning technique
    applies to HP" discussion): Sokoban's `is_dead()` is a domain-constraint deadlock check,
    independent of the heuristic; HP's only prune is the bound (search-optimality). Every future
    monomer must stay lattice-adjacent to the one before it, so the whole remaining chain has to
    fit inside the connected component of free cells reachable from the tip — if that component
    is smaller than the monomers still needed, completion is provably impossible.
    `reachable_free_capacity` (`bnb.py`) checks this via a capped BFS (early-exits once the count
    needed is reached, so cost is bounded by monomers-remaining, not total free space). Sound
    because occupied cells never free up again (unlike Sokoban's revisitable tiles), so a
    "too-small-already" verdict stays true forever — verified against the brute-force oracle on
    every existing test sequence plus a hand-built sealed-pocket fixture
    (`tests/test_bnb.py`), zero mismatches.
    - **Empirical result on real sequences (lengths 10-18, `data/synthetic_hp.fasta`): fires
      thousands of times on longer chains, but only reduces `nodes_expanded` by ~0.1-0.2%, and
      wall-clock time is a wash to slightly worse** (BFS overhead roughly cancels the saved
      nodes). `bound_pruned` outnumbers `connectivity_pruned` by 10-100x on the same instances.
    - **Why, most likely**: the existing parity-capacity bound already implicitly captures much
      of what connectivity pruning would separately catch — a sealed-off pocket generally also
      has poor parity-capacity (few of the right-parity H's nearby), so the bound often prunes
      it first anyway. This is a real structural difference from Sokoban, where Manhattan/
      Hungarian carry no deadlock information at all (a crate in a dead corner can still look
      heuristically "close"), which is exactly why Sokoban's `is_dead` check independently
      matters so much (~59% pruned) on top of the heuristic.
    - **Verdict**: the technique transfers in the sense that it's implementable, sound, and
      does fire — but its marginal value for HP is small given the bound already does most of
      that work, unlike Sokoban's genuinely complementary heuristic/deadlock split. Consistent
      with `docs/equivalence/sokoban_hp-latice_equivalence.md`'s "Level 2, weak transfer"
      framing — a real negative-ish result, not evidence of a bug or a reason to keep tuning
      this specific check. Left in as opt-in (off by default, zero cost otherwise) rather than
      pursued further as a headline technique; `bound_pruned`/`connectivity_pruned` are now on
      `BnBResult` and trace rows carry `prune_reason` if this needs revisiting later.
    - `bnb_cli.py --connectivity-prune` added (`base_h` gets a `+conn` suffix, no new D6 column
      for a proof-of-concept flag). Closed the loop with the trace pipeline directly: regenerated
      the same 18-instance slice (`data/synthetic_hp.fasta`, lengths 3-20) into a separate
      `results/traces_connectivity/` dir (kept apart from `results/traces/` so it doesn't blur
      into the main aggregate) and compared S1.3/S3.1 before/after in
      `notebooks/cross_domain_analysis.ipynb`. Result, genuinely interesting and not visible from
      the node-count benchmark alone: **the trap rate roughly halves (0.90% -> 0.37%)** even
      though `nodes_expanded` barely moves and the `expanded->pruned` transition probability is
      essentially unchanged (1.21% -> 1.41%). Reading: connectivity pruning catches some dead
      ends *earlier* (at an ancestor, via a cheap local check) rather than *fewer* dead ends
      overall — the same rejections happen, just sooner, before the search wastes several more
      expansions finding the same thing the slow way via the bound. Still doesn't move HP's
      pruned-fraction anywhere near Sokoban's ~59%, as expected.

16. **S3.4 (product/monoidal ablation) scoped, not built: neither domain's heuristic has two
    components to ablate.** Checked both implementations directly before building anything:
    `src/sokoban/heuristic.py`'s `manhattan`/`hungarian` have no player-position term at all (not
    an oversight — the cost model here counts pushes only, `g += 1` per push, and player-walking
    between pushes is free/uncounted, so remaining push-cost is structurally independent of
    player position). `bnb.py`'s `bound_tight`/`bound_weak` are entirely contact-count estimates,
    no shape/compactness term either. So in both domains there's only one component *in* the
    heuristic already — "ablation" as the doc proposes (strip a component out of an existing
    joint heuristic) doesn't apply; building `h_position_only`/`h_shape_only` would mean inventing
    an entirely new heuristic component per domain from scratch, each needing its own admissibility
    proof and brute-force verification (same bar as the original bound derivation) — materially
    bigger and riskier than "ablation" implies, and the new components would be arbitrary
    inventions rather than a natural split of something already validated. Decided (user call) to
    report this as a finding and stop rather than build components just to force the test — joins
    S2.3/`move_type`'s precedent of the doc's proposed method not fitting the engine as built.

17. **Two S1.4/S1.2 readability bugs fixed, both caught by the user actually looking at the
    plots, not by any test.** Neither was subtle in hindsight, but neither would have been
    caught by re-running the numbers either — they're specifically about what a human reading
    the figure takes away from it.
    - **S1.4 Mapper node sizing**: `node_size` scaled linearly with cluster size
      (`80 + 40*size`). Fine on Sokoban (cluster sizes 1-4) but HP's actual range is 1-2108 —
      linear scaling turned that into a ~700x marker-*area* ratio, one node swallowing the
      whole plot. Fixed to `60 + 60*log1p(size)`; suptitle updated to say so explicitly
      ("node size = log(cluster size)") so the encoding isn't silently misleading.
    - **S1.2 persistence diagrams**: `persim.plot_diagrams`'s birth-death scatter reads as
      near-empty when there are only tens of bars, which is exactly this project's regime —
      not a bug in `persim`, just a format mismatch for small feature counts. Replaced with a
      barcode as the primary view (one horizontal bar per feature, length = persistence,
      grouped and colored by H0/H1, sorted longest-first) plus a printed top-5-by-persistence
      summary per dimension; kept the scatter underneath as a secondary/reference view since
      it's still the form most of the literature uses.
    - **Correction to what I'd told the user**: an earlier claim that "beta1 is always 0 across
      tested instances" was based on smoke-testing smaller/different trace files, not the actual
      instances the notebook uses. The real notebook instances (largest per domain, `max_points`
      now 1500, was 800) show Sokoban genuinely has ~4-6 persistent H1 bars (real transposition
      loops in the `(g,h,f)` embedding); HP genuinely has 0 at this embedding and scale. Worth
      knowing before citing "no loops" as a finding — it's true for HP, was never actually
      confirmed true for Sokoban.
    - **H2 (voids) is not computed, and empirically can't be at this scale**: tried
      `ripser(X, maxdim=2)` directly on just 800 points — over 20GB RAM, 18+ CPU-minutes,
      killed before finishing. H0/H1 don't have this blowup; H2 needs enumerating 3-simplices
      of the Vietoris-Rips complex, which scales combinatorially in a way the lower dimensions
      don't. This is exactly why the design doc itself only scopes S1.2 to beta0/beta1 — now
      confirmed empirically, not just assumed, and stated explicitly in the notebook so a reader
      asking "where's H2" gets an answer instead of silence.

## Deferred

(none)

## Framing notes

- Existing Metropolis MC code is on-topic (SA is a Category-D example), not dead weight.
- `docs/equivalence/` predicts weak transfer ("Level 2, graphs fundamentally different") — a
  negative transfer result is a valid, publishable finding. Don't force a positive-transfer story.
