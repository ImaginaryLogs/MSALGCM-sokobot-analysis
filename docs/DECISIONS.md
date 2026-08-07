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

## 2026-08-06

18. **S1 null-model control built (`analysis/null_model.py`) and an Arm B x topology
    extension added to `notebooks/cross_domain_analysis.ipynb`** -- both raised in
    session discussion of whether the S1/S2/S3 domain comparison and the Arm A/B
    technique comparison needed to be crossed, rather than staying two isolated
    notebooks.
    - **Null model**: `random_priority_search` -- a domain-generic best-first
      search (i.i.d. uniform random priority, not `f=g+w*h`) that accepts every
      domain-legal successor with no deadlock/bound filtering, since deciding
      what to reject is itself part of what's under test, not a domain given.
      `h` is still computed (real heuristic/bound, never used to guide) so `f`
      stays comparable to the real trace. Fills the design doc's Section 1
      closing "Null-model check" note, never built until now -- every S1 finding
      up to this point (disconnectivity shape, `β1` bars, curvature, Mapper
      fragmentation) was unfalsifiable against "that's just what a same-size
      chunk of this domain's raw graph looks like", not necessarily attributable
      to heuristic guidance or pruning.
    - **Size-matched, not corpus-matched**: `truncate_to_size` takes the real
      trace's first `NULL_TARGET=20_000` expanded/goal rows by
      `timestamp_order`; the null search stops at the same count. Comparing
      differently-sized graphs would confound "shape differs from guidance"
      with "shape differs because one graph is bigger".
    - Run on the same single largest-trace-file-per-domain already used for
      S1.5's instance plot (`original3` Sokoban, downloaded CRAMBIN HP
      sequence), one seed -- directional, not confirmatory, matching this
      notebook's existing single-instance caveat.
    - **Result: Sokoban's S1.1 disconnectivity AUC is ~1.0 for both real and
      null -- expected, not a finding.** At `w=1`, Manhattan is consistent (one
      push changes `h` by exactly ±1), which forces `f=g+h` non-decreasing along
      every search-tree edge, so any `f<=tau` sublevel-set subgraph is
      tree-connected by construction at every threshold, independent of
      expansion order. **HP shows a real, non-degenerate gap on both AUC and
      S1.5 mean curvature** -- HP's `f` has no such monotonicity guarantee
      (`g` = accumulated contacts, `h` = a *shrinking* upper bound), so its
      bound-guided expansion order visits a measurably more bottlenecked region
      of the state space than a same-size random walk. The asymmetry itself is
      informative: the null model is only structurally guaranteed to be vacuous
      for Sokoban, not for HP.
    - **Arm B x topology sweep** (3 instances with a full 6-point weight-grid
      Pareto series already in `results.csv`, re-traced with `trace=True` per
      weight): motivated directly by the Sokoban degeneracy above, since
      consistency is `w=1`-only (`f=g+w*h` loses it for `w>1`, the same fact
      already used to explain `f_plateau` becoming a real signal at `w>1`,
      decision #11). **Confirmed empirically**: disconnectivity AUC jumps off
      the 1.0 floor at `w=1.25` for all three instances, before any other
      topology metric shows a clear pattern. **No single monotonic
      "higher w = smoother topology" trend past that** -- `53-44`'s mean
      curvature gets steadily more negative as `w` rises, tracking its own
      non-monotonic node-count/quality jump at `w=2.0` (higher `w` finds a
      *worse* solution *and* explores more nodes there); `2-11` and `52-13`
      don't show that reversal. Three instances, reported as "topology-warping
      is real and instance-dependent", not a population claim.
    - Both additions are outside `docs/equivalence/cross-domain-analysis-design.md`'s
      original S0-S3 scope -- extensions, not gap-filling against that doc.

19. **`notebooks/cross_domain_analysis.ipynb` reorganized into S1/S2/S3 +
    Extensions document order, and one real bug found and fixed while
    rechecking it** (not just cosmetic -- flagged when asked to review the
    notebook's organization).
    - **Reorder**: sections previously appeared in *build* order (S2 and S1.3
      first, since both reuse the one-streaming-pass aggregate and needed no
      new deps; S1.1/S1.2/S1.4/S1.5 added later once `ripser`/`networkx`/
      `GraphRicciCurvature` were installed), which read as S2 -> S1.3 ->
      S1.1/1.2/1.4 -> S1.5 -> S3 -> connectivity-pruning -> null-model ->
      weight-sweep -- internally consistent but not the order a reader
      following "S1.1 through S1.5" would expect. Reordered to Setup -> S1
      (1.1/1.2/1.3/1.4/1.5, in order) -> S2 -> S3 -> a new "Extensions beyond
      the design doc's scope" umbrella (connectivity-pruning, S1 null-model
      control, Arm B x topology sweep) -> closing. No cell content/logic
      moved except heading levels (former top-level `##` section headers
      that are now subsections under S1 or Extensions demoted to `###`) --
      verified every reordered cell's data dependency (`agg_by_domain`,
      `pop_data`, imports) only requires running after the shared Setup
      cells, not after any specific S-numbered section, so the reorder is
      execution-safe.
    - **Real bug found**: the S3.2 KL-divergence cell asserted
      `labels_a == labels_b` (Sokoban's and HP's transition-matrix label sets
      match) -- true before #18 (both domains had exactly `{expanded, goal,
      pruned}`), but Sokoban now also logs `discarded` (the
      transposition-dominance cases, HP has no analog), so the label sets
      diverge (5 vs 4) and the assert would crash the very next execution.
      Fixed to compare over the shared-label intersection only, printing
      which labels are domain-specific rather than either crashing or
      silently comparing mismatched rows.
    - **Also found and reverted**: a stray `assert labels_a[1:] == labels_b` /
      `enumerate(labels_a[1:])` had appeared in that same cell's *source* at
      some point this session without an identified cause (not present in
      the pre-session backup, not something any known edit in this session's
      history touched deliberately) -- would have silently misaligned matrix
      rows against labels if it had ever executed (comparing `mat_a[i]` at
      the *sliced* label's position against the *unsliced* `mat_b[i]`).
      Replaced by the shared-label-intersection fix above rather than
      restored, since the intersection version is correct for both the old
      (matching labels) and new (diverging labels) cases. Flagged here as an
      unresolved provenance question, not swept under the rug.
    - **S3's status-vocabulary description updated** to match #18: FRONTIER
      is now observed in both domains (was 3-of-5 doc objects, now 4-of-5),
      DISCARDED is a Sokoban-only addition outside the doc's 5-object
      vocabulary, and the "terminal/vacuous" note (previously just
      goal/pruned) now covers frontier/pruned/discarded/goal -- only
      `expanded` ever has real outgoing transitions.
    - **Superseded**: the corpus finished regenerating (217 trace files, 158
      sokoban/59 hp_lattice, `trace_node_cap=500_000`) and the notebook was
      re-executed against it the same session -- the label-set fix above ran
      for real (would have crashed on the old hard assert) and every number
      in the notebook is now current. See #20 for what that re-execution
      found.

20. **HP's `frontier` row in the S3.1/S3.2 transition matrix is a
    `trace_node_cap` artifact, not real search behavior -- found only by
    actually rechecking #19's reorganized notebook against the fresh 500k-cap
    corpus** (invisible on the smaller pre-#18 traces, where nothing hit the
    cap deep enough to matter).
    - **Mechanism**: `bnb.py`'s DFS logs a node's own `expanded`/`goal` row
      *after* recursing into all its children (post-order) -- a node's
      `frontier` row is written by its parent, before the recursive call that
      will eventually overwrite it in any post-hoc `by_id` lookup. But
      `trace_node_cap` stops row *logging* without stopping the *search*, so
      once a trace hits the cap, any node already mid-recursion (frontier row
      written, already recursed into, some children's rows already written)
      never gets the overwriting `expanded`/`goal` row appended -- that
      append was scheduled for *after* its subtree, exactly when the cap
      silently swallowed it. Net effect: some fraction of nodes that were
      genuinely fully expanded by the real search are stuck showing
      `status=frontier` in the trace, and their already-logged children now
      read as "frontier -> expanded/frontier/goal" transitions.
    - **Sokoban's `frontier` row stays correctly all-zero** despite hitting
      the same cap on plenty of files (19+): its solver logs a node's own row
      immediately after popping it, strictly before any of its children are
      even generated -- there's no "children logged, parent not yet" window
      for the cap to land inside. The asymmetry is a genuine structural
      consequence of iterative pop-then-log (Sokoban) vs recursive
      post-order-log (HP), not a bug in either.
    - **Confirmed structural, not incidental**: 22 of the 59 HP trace files
      hit the cap exactly (`wc -l == 500001`), and the identical pattern
      (0.30/0.68/0.01/0.00-ish) shows up independently in the
      connectivity-pruning section's transition matrices too, on a completely
      different 18-instance slice, nearly identically for both the
      bound-only and bound+connectivity variants -- which also confirms it
      isn't a connectivity-pruning effect.
    - **Not fixed**: this is a real limitation of building `status` sets
      post-hoc from a capped, per-node trace rather than the design doc's
      proposed live `status_transitions` log (§3.1) -- fixing it properly
      would mean logging a node's own status *before* recursing, then a
      separate transition event when it's later confirmed goal/complete,
      which is a bigger change than this session's scope. Documented in the
      notebook (new cell after S3.2's KL output, plus a note on the
      connectivity-pruning interpretation) so the numbers aren't
      misread as a domain-structural finding about HP's search.

21. **RQ6 (instance-specific correspondence, `docs/specs/METHODOLOGY_SYNTHESIS.md`) scoped out for
    this data collection — checked both of its proposed paths directly rather than assuming either
    was open.**
    - **General multi-pair test: blocked, confirmed by reading the source doc.**
      `docs/equivalence/sokoban_hp-latice_equivalence.md`'s Layer 5 mapping is a category-level
      prose analogy (e.g. "Box Locations → Monomer Coordinates"), not a runnable
      board-to-sequence (or sequence-to-board) construction; its Layer 6 is literally "To Be filled
      later."
    - **The single-pair shortcut the synthesis doc called "cheapest available step, requiring no
      new formal work" (`original3`/CRAMBIN, reused from #18's null-model control) is also blocked
      — by two independent, verified data problems, not by the missing mapping:**
      1. Neither instance has a proven-optimal solve on both heuristic arms, so RQ4's
         equal-quality ratio can't be computed. `results.csv`: `original3` has only one Sokoban run
         (manhattan, `w=1`), `solved=cutoff`/`cutoff_reason=budget`/`solution_quality=NA` at the
         2M-eval cap, no Hungarian run at all (same true of `original1`/`original2`). CRAMBIN has
         both `tight` and `weak` bound runs, but both also hit the 2M-eval cap with
         `solution_quality=8` as an unproven incumbent, not a certified optimum.
      2. RQ1's taxonomy extension is real on the Sokoban side and empty on the HP side of this
         specific pair. `original3`'s trace: 106,855/180,549 expanded-or-pruned nodes pruned =
         **59.18%**, matching the ~59% population figure (#15) almost exactly — a genuine
         instance-level confirmation. CRAMBIN's 500,000-row capped trace has **zero**
         `status=pruned` rows. Checked whether this is CRAMBIN-specific: no — 3 of the other 20 HP
         trace files that also hit `trace_node_cap` show zero pruned rows too, alongside others
         showing anywhere from a handful to several thousand. Same root cause as #20's frontier-row
         artifact: bound-pruning only becomes frequent once the B&B incumbent has tightened, and on
         these instances that point falls past the 500,000-row capture window — not evidence HP
         doesn't prune on chains this size (#15 already shows thousands of prune events at
         comparable lengths), evidence this particular capped trace hasn't reached that region yet.
    - **Resolution**: RQ6 stays out of scope for this data collection. RQ2–RQ5's population-level
      findings are a proxy for equivalence, not a direct test of it — state that plainly wherever
      they're reported. If RQ6 is reopened later, the fix is not the mapping construction: either
      re-run `original3` with Hungarian to convergence and pick an HP instance/cap that actually
      shows pruning, or choose a different matched pair both engines already solved to proven
      optimality on both heuristic variants.

22. **Real bug fixed in `analysis/topology_lite.py::disconnectivity_curve`: a
    stale-revisit `f` value was silently corrupting Sokoban's S1.1
    disconnectivity AUC by 1-2 orders of magnitude at population scale —
    found while building Track D's RQ5 cross-reference figure
    (`docs/specs/METHODOLOGY_SYNTHESIS.md`), not by any test.**
    - **Mechanism**: `by_id = {r["node_id"]: r for r in rows}` kept whichever
      trace row for a given state came *last* in the file. Sokoban logs a
      `discarded` row every time a transposition revisits an already-expanded
      state via a worse path (#12/#19) — that row carries the *same*
      `node_id` but a *worse* (higher) `f` than the state's real, earlier
      `expanded` entry. A plain dict comprehension let the later, worse
      `discarded` row silently overwrite the real one, so many nodes'
      `f`-value used for the threshold sweep was wrong — often high enough to
      exclude that node from every low-tau bucket it should have belonged to,
      inflating `n_components` and therefore the AUC computed by
      `disconnectivity_curve_normalized`.
    - **Why it stayed hidden**: the one place this number gets stated as a
      finding — the S1 null-model control (#18, `original3`/CRAMBIN) — feeds
      `null_model.truncate_to_size`-filtered rows (`status in
      ("expanded","goal")` only) into the curve function, which incidentally
      filters out every `discarded` row and sidesteps the bug entirely. That
      cell's `1.0000` was always genuinely correct. The **population-level
      S1.1 fan chart** (cells 7-9) hands the curve function *raw, unfiltered*
      trace rows and has no printed numeric summary (plot only) — so nothing
      surfaced the corruption until Track D's new combined-figure cell
      printed raw `disc_auc` values of 97/58/34 for a `w=1` Sokoban instance
      that should have been exactly `1.0`.
    - **Fix**: `disconnectivity_curve` now restricts both `by_id` and the
      threshold range's `f_values` to `status in ("expanded", "goal")` rows
      only, mirroring `truncate_to_size`'s already-correct notion of
      "visited." Verified on `original3`'s full trace and the `2-11` weight
      sweep: AUC now reads exactly `1.0` at `w=1`, matching the algebraic
      argument, before and after.
    - **Population-level re-verification (28 valid Sokoban curves, same
      `POP_SAMPLE_SIZE=30`/`POP_SEED=0` sample as cells 6-9)**: every single
      one now reads AUC `1.0000` exactly — the "AUC=1.0 floor at `w=1`" claim
      is now an exactly-verified population result, not an assumption resting
      on one spot-checked instance. HP is unaffected by this bug (no
      transpositions, so no `discarded` status to collide on) and keeps its
      wide, expected population spread (0.61-3727, median ~11).
    - **No other callers affected differently**: `scripts/analyze_traces.py`
      is the only other caller of `disconnectivity_curve` and gets the same
      fix automatically; its `*_disconnectivity.csv` outputs (already stale
      and removed from `results/analysis/` this session) would need
      regenerating if reused.
    - Added a numeric confirmation cell (mean/median/min/max per domain)
      directly after the S1.1 fan chart plot in `notebooks/cross_domain_analysis.ipynb`,
      since the plot alone had no printed number for anyone to check against.

## 2026-08-07

23. **Track E (scaling-axis retrofit) built and verified against real data —
    `docs/specs/METHODOLOGY_SYNTHESIS.md`'s "missing axis" section.**
    - **Checklist items 1 and 3 were already satisfied, not new work**:
      `results/results.csv`'s `instance_size` column has 0/136 `NA` HP rows
      (range 3-46) — no emission fix needed; `notebooks/analysis.ipynb`
      cells 3 and 7 already plot Arm A's ratio against `instance_size` on
      the x-axis for both domains.
    - **Item 2 (the actual new work)**: added `instance_id_of()`
      (`analysis/trace_io.py`) to reverse a trace filename back to the
      `instance_id` key `results.csv` already has `instance_size` for —
      mechanical, mirrors `src/sokoban/cli.py`/`src/protein-fold/bnb_cli.py`'s
      own file-naming, verified against all 217 real trace files (0 misses).
      Added `size_of()`/`scatter_by_size()` helpers and one per-instance
      scatter cell per S1/S2 metric to `notebooks/cross_domain_analysis.ipynb`
      (disconnectivity AUC, β1 bar count, fragmentation ratio, mean
      curvature, branching factor, feasibility ratio) — the last two needed
      a new per-instance mean computed over `pop_by_domain`'s 30-instance
      sample, since `agg_by_domain` only pools at node level across the
      whole corpus. Notebook re-executed end-to-end (`.venv/bin/jupyter
      nbconvert --execute`), 0 errors.
    - **Findings, on the `POP_SAMPLE_SIZE=30`/`POP_SEED=0` sample (directional,
      not a scaling law)**, correlations computed both as Pearson (linear) and
      Spearman (rank, robust to outliers) against normalized instance size:
      - Sokoban's disconnectivity AUC stays flat at exactly `1.0` across its
        whole sampled size range, as expected from the `w=1` consistency
        argument (#22). HP's AUC has a moderate positive rank correlation
        with size (Spearman ρ=0.61 on n=27; Pearson r=0.10, weak — pulled
        around by a few very-high-AUC outliers).
      - HP's β1 bar count is **exactly 0 for all 30 sampled instances at every
        chain length 3-36** — a domain-structural fact (chain-growth has no
        transpositions to create the revisit-loops β1 is presumably
        detecting), not a size effect. Sokoban's β1 has real variance (0-111
        bars) but no clean size trend (Spearman ρ=-0.22).
      - Neither domain's Mapper fragmentation ratio trends with size (Sokoban
        ρ=0.40, HP ρ=-0.04, both weak).
      - Sokoban's mean Forman curvature has a strong negative size trend
        (Pearson r=-0.85, Spearman ρ=-0.84 — bigger instances' search graphs
        get more tree-like/hyperbolic). HP's signal is weak and internally
        inconsistent (Pearson r=-0.48 vs Spearman ρ=+0.23 — sign disagreement,
        likely outlier-driven on n=30) — no confident trend.
      - Sokoban's mean branching factor rises with size (Pearson r=0.69,
        Spearman ρ=0.68 — structural, more simultaneously-pushable crates).
        HP's stays pinned near its lattice ceiling (≤3) across the whole
        3-36 chain-length range (Pearson/Spearman disagree in sign there too)
        — no real size trend.
      - Feasibility ratio is only weakly size-associated in both domains
        (Sokoban ρ=0.21, HP ρ=0.21), with HP's mean (0.95) sitting well above
        Sokoban's (0.82) at every size sampled — consistent with #22's
        module-docstring point that HP's real filtering happens elsewhere
        (silent self-avoidance at generation time), not in this ratio.
    - **Read as a cross-domain asymmetry, not a single verdict**: Sokoban's
      topology genuinely reshapes with instance size for curvature and
      branching factor; HP's largely doesn't, with disconnectivity AUC as the
      one metric where HP shows a real (if noisy) size trend. Every markdown
      cell above the six new scatters was written as neutral, un-presumptive
      placeholder text *before* the notebook was re-executed, then replaced
      with the numbers above only after real output existed — avoiding the
      same fabrication risk #19/#22 already had to correct for.

24. **Track C (RQ4 additions) built and verified against real data —
    `docs/specs/METHODOLOGY_SYNTHESIS.md`'s RQ4 section, `notebooks/analysis.ipynb`.**
    - **HP outlier table**: added an H/P-sequence join to `analysis.ipynb` so
      each of `hp_ratios`' 46 instances gets a `hp_density` (fraction of `H`
      residues) alongside its existing `instance_size`. The 54 synthetic
      instances read straight from `data/synthetic_hp_seed{42,67,420}.fasta`
      (already H/P letters); the 5 real PDB proteins are converted via
      `utils.convert_to_hp` after reproducing `bnb_cli.py`'s own label
      transform (`re.sub(r"[^A-Za-z0-9_.-]+", "_", header)[:60]`) to match
      `results.csv`'s `instance_id` exactly. **Finding: HP's largest ratios
      correlate with chain length (Spearman ρ=0.76, Pearson r=0.61), not
      hydrophobic density (ρ=-0.36, r=-0.23)** — the opposite structural story
      from Sokoban's outliers, which read as goal-contention-driven. HP's
      tail looks like "the tight bound's advantage compounds over a longer
      chain," independent of H-richness.
    - **HP's Arm A exclusion count**: of 59 distinct attempted HP instances
      (54 synthetic + 5 real PDB proteins), all 59 had both `weak` and
      `tight` base_h rows present — no partial-arm gaps — but only **46/59
      (78%)** reached equal-quality solves under both bounds. The other 13
      were excluded for one single, consistent reason: `cutoff_reason=budget`
      on *both* bounds, never just one. Those 13 are the 4 longest synthetic
      chains (length 17-20) plus **all 5 real PDB proteins in the dataset**
      (`1CRN`/CRAMBIN, `1L2Y`/TC5b, `1VII`/VILLIN, both `4INS` insulin
      chains) — every real protein this study tracks falls outside the
      eligible RQ4 sample entirely, unlike Sokoban's clean 155/155. This is a
      real scope caveat for RQ4, not a rounding footnote: the ratio result is
      synthetic-sequence-dominated.
    - **Synthesis rewrite**: `analysis.ipynb`'s "Does heuristic strength
      transfer?" cell and its Summary cell now state the mean/median/max
      numbers explicitly (Sokoban 155/155: mean 1.899, median 1.086, max
      18.098; HP 46/59: mean 1.103, median 1.022, max 1.567) and frame the
      tail asymmetry via RQ1's coupled-vs-decoupled deadlock-detection
      mechanism (#1/#12/#15/#19) instead of "comparable order of magnitude" —
      matching the framing this design doc already argued for in its RQ4
      section, now actually written into the notebook instead of only the
      doc. Re-executed end-to-end (`.venv/bin/jupyter nbconvert --execute`,
      18 cells), 0 errors; printed numbers match a standalone verification
      script run against `results/results.csv` directly, computed
      independently of the notebook.
    - **Process note**: `jupyter`/`jupyter-nbconvert` on `$PATH` resolve to a
      broken global install with no `nbconvert` module at all (`jupyter
      nbconvert` fails with "command not found", silently swallowed by a
      `| tee` pipeline's exit code). The project's own `.venv/bin/jupyter` is
      the one that actually has `nbconvert` installed (`pyproject.toml`'s
      `nbconvert>=7.16` dependency) — use it explicitly for any future
      notebook re-execution in this repo, not bare `jupyter`.

25. **Track F reopened: RQ6's single-pair shortcut, blocked by `original3`/CRAMBIN in
    decision #21, now computed against a different matched pair from the existing
    corpus — `25-30_Sokoban-Microban-30` (3 crates) / `hp_len11_0_seed42`
    (chain length 11).**
    - **Why not `original3`/CRAMBIN after all**: a real attempt to re-run `original3`
      with Hungarian to convergence (per #21's stated fix) at a 50M-eval budget
      crashed on the hardware it was run on before completing. Rather than debug
      that crash, took #21's own documented fallback instead: pick a different pair
      already solved to proven optimality on both heuristic arms, from data already
      in this repo — no new runs needed.
    - **Selection**: filtered `results/results.csv` to instances with `solved=1` on
      both arms at equal quality, then to the smallest such instances per domain with
      an uncapped trace, preferring an HP candidate with a non-zero `pruned` row
      count (avoiding CRAMBIN's `trace_node_cap` zero-pruned artifact, #20) and a
      Sokoban candidate whose pruned rate landed close to the ~59% population figure
      already cited elsewhere, for a cleaner side-by-side.
    - **RQ4 ratio, now computable for this pair**: Sokoban manhattan=20 evals,
      hungarian=16 evals, both solve to `solution_quality=5` — ratio=1.25. HP
      weak=3,238 evals, tight=2,817 evals, both solve to `solution_quality=2` —
      ratio≈1.149. Both close to their domain's overall median (#24), consistent
      with picking an unremarkable instance rather than a tail outlier.
    - **RQ1 taxonomy extension, now real on both sides**: Sokoban's trace — 28 of 48
      expanded-or-pruned nodes pruned, 58.33% (consistent with `original3`'s 59.18%
      and the ~59% population figure). HP's trace — 352 of 3,169 expanded-or-pruned
      nodes pruned, 11.11% — a real, non-degenerate number, unlike CRAMBIN's zero.
      The two percentages aren't expected to match each other (RQ1's taxonomy
      already establishes the domains reject candidates through different
      mechanisms); the point is that both sides now have a real number at all.
    - **Scope, unchanged**: this reopens only the single-pair shortcut. The general
      multi-pair correspondence test stays out of scope — nothing about
      `docs/equivalence/sokoban_hp-latice_equivalence.md`'s unwritten Layer 6
      changed.
    - **RQ2–RQ5 scope note**: added a shared paragraph immediately before RQ2 in
      `docs/specs/METHODOLOGY_SYNTHESIS.md` stating plainly that every RQ2–RQ5
      finding is a population/aggregate proxy for equivalence, not a direct test of
      it, rather than leaving that caveat implicit or only inside RQ6's own section.

## Framing notes

- Existing Metropolis MC code is on-topic (SA is a Category-D example), not dead weight.
- `docs/equivalence/` predicts weak transfer ("Level 2, graphs fundamentally different") — a
  negative transfer result is a valid, publishable finding. Don't force a positive-transfer story.
