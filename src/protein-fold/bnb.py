"""Depth-first Branch-and-Bound chain-growth solver for the HP lattice model
(ADR 0002: docs/adr/0002-hp-engine-bnb.md). Systematic, complete search --
the HP-side counterpart to Sokoban's weighted A* (src/sokoban/solver.py),
sharing the same result-counter shape so runs join cleanly on
`nodes_expanded`.

State-space / algorithm per docs/representations/hp-lattice-folding_representation.md
(Layers 1-4): monomers are grown one at a time onto a self-avoiding walk;
each node's score g(n) is the H-H contact count of the placed prefix;
children are pruned against an admissible upper bound U(n) = g(n) + h(n).

Bound h(n) -- corrected parity/checkerboard bound:
A backbone step always flips lattice checkerboard color, so sequence-index
parity IS lattice-position parity -- any future H-H contact must pair an
odd-index H with an even-index H. The representation doc's Layer 4 states
h(n) = min(unplaced_odd_H, unplaced_even_H), counting *monomers*, one unit
each, on both sides. Two bugs in that literal formula (both verified by
diffing against a brute-force oracle over small instances -- see
tests/test_bnb.py): (1) it ignores that a future contact can land between
an unplaced monomer and an *already-placed* one (e.g. closing a 4-mer "U"
onto monomer 0 -- "HHHH"'s only optimal fold was pruned away); (2) it caps
each *unplaced* monomer's contribution at 1, when a monomer can be party to
more than one simultaneous contact (up to its free lattice-neighbor count),
so a monomer later realizing 2 contacts was undercounted by 1 (e.g.
"HPHPPH": true optimum 2, literal formula found 1). Both are the same
mistake -- bounding by monomer *count* instead of contact *capacity*. The
fix sums each monomer's structural capacity (`_contact_capacity`: 2 for an
interior monomer -- 4 lattice neighbors minus 2 backbone bonds; 3 for a
chain end, which has only 1 backbone bond) instead of counting monomers,
on both the unplaced side (precomputed suffix sums) and the placed side
(`po_free`/`pe_free`, the actual current free-neighbor-cell totals for
already-placed H monomers, maintained incrementally):

    h(n) = min(unplaced_odd_capacity + po_free, unplaced_even_capacity + pe_free)

`po_free`/`pe_free` update in O(1) per placement/backtrack: placing a
monomer consumes exactly one free slot from each already-placed neighbor it
lands next to, and contributes its own (4 - occupied-neighbor-count) free
slots to its own parity's pool.

Heuristic-strength arm (`bound="tight"` vs `bound="weak"`, the HP analog of
Sokoban's manhattan-vs-hungarian Arm A): `bound_weak` uses the same
parity-capacity argument but substitutes each already-placed monomer's
*static structural* capacity (`_contact_capacity`, precomputed once as a
prefix sum, ignoring which of its lattice neighbors are actually occupied)
for `po_free`/`pe_free`'s *real-time tracked* remaining free-slot count.
Since a monomer's true remaining free-slot count can never exceed its
static structural capacity (geometry can only ever consume neighbor cells,
never grant more than 4), `bound_weak(n) >= bound_tight(n)` always -- it's a
valid, strictly looser upper bound, not a different (unsound) formula, so
both reach the same proven optimum, just at different cost. Verified against
the same brute-force oracle as the tight bound (tests/test_bnb.py). This
mirrors Sokoban's Manhattan (each crate independent, ignores inter-crate
contention) vs Hungarian (solves the assignment jointly): `bound_weak`
ignores which specific cells are already occupied by other geometry,
`bound_tight` accounts for it in real time.

Connectivity pruning (`connectivity_prune=True`, proof of concept) -- the HP
analog of Sokoban's `is_dead()` domain-constraint deadlock check
(src/sokoban/deadlock.py), not another bound refinement. Sokoban's deadlock
check is static (precomputed once, independent of game state) because board
topology is fixed; HP's occupied-cell layout changes with every placement, so
there's no equivalent *static* precompute, but the underlying principle still
transfers: every future monomer must be lattice-adjacent to the one before
it, so the entire remaining chain has to live inside the connected component
of *free* cells reachable from the current tip. If that component has fewer
free cells than monomers still needed, completion is impossible --
`reachable_free_capacity` checks this via a capped BFS (early-exits once the
count needed is reached, so cost is bounded by how many monomers remain, not
by total free space). Sound because occupied cells never become free again
(monomers don't move once placed, unlike Sokoban's revisitable tiles), so
this connected component can only shrink as the chain grows, never regrow --
a "provably too small already" verdict stays true forever. This is a genuine
domain-constraint rejection (like Sokoban's `is_dead`), logged with
`prune_reason="connectivity"` in the trace, distinct from the bound-prune's
`"bound"` -- see docs/DECISIONS.md for the proof-of-concept results
(nodes-saved vs BFS overhead, and whether it closes any of the gap between
Sokoban's ~59% pruned-fraction and HP's ~0.7% bound-only figure).

First-turn symmetry break (Layer 4, "Coordinate-Free Symmetry Eliminators"):
monomer 0 is fixed at (0,0) and monomer 1 at (1,0) (kills rotational
symmetry); at the very first branch point (placing monomer 2) the y<0
candidate is dropped, since it is the mirror image (across the x-axis) of
the y>0 candidate and an isometry can't change any contact count. This
halves the search space for free and loses no optimal solution.

Optional per-node trace (`trace=True`, docs/equivalence/cross-domain-analysis-design.md
S0), mirroring src/sokoban/solver.py's trace feature: opt-in, off by
default, zero cost/behavior change otherwise; one row per DFS node visited,
capped at `trace_node_cap` rows (default 100k) so a run can't blow up
storage regardless of `eval_budget`. `node_id`/`parent_id` reuse the fold
prefix itself (`tuple(fold)` at entry / `tuple(fold[:-1])`) as the state
hash, same substitution Sokoban makes with `state.key()` -- valid here
because HP chain-growth has no transposition (docs/equivalence/
sokoban_hp-latice_equivalence.md, Layer 5 Differences: a partial fold is
reachable via exactly one placement order).

Two deliberate asymmetries versus Sokoban's trace, both because B&B's
accept/reject structure genuinely differs from A*'s, not because of a
shortcut:
  - "pruned" here means the bound-prune fired (`bound <= best_energy`), a
    *search-optimality* rejection -- not a domain-constraint violation like
    Sokoban's `is_dead()` check (a row IS logged, one per rejected
    candidate, same as Sokoban; what differs is the reason it was
    rejected). HP's actual domain constraint (self-avoidance) is enforced
    silently at candidate generation (occupied cells are never added to
    `candidates`), so there's no event to log for *that*. Cross-domain
    PRUNED comparisons need to account for this: Sokoban's is structural,
    HP's is search-driven.
  - no `f_plateau` column. Sokoban's `f_plateau` captures "search stalls
    despite legal (non-deadlock) moves existing" as a signal distinct from
    pruning. In this DFBnB formulation there's no such distinct state: a
    candidate that isn't bound-pruned is by construction one whose bound
    already exceeds the current best, so "legal but not improving" isn't a
    state that exists here the way it does under Sokoban's separate
    dedup/deadlock gates. `all_pruned` (below) is the only trap-adjacent
    signal this engine has.
  - `all_pruned`: true when either no legal placement exists at all (a
    genuine self-avoidance dead end, the direct HP analog of Sokoban's
    all-successors-deadlocked case) or every candidate was bound-pruned (the
    search-optimality analog). Both collapse into one flag; which case fired
    is recoverable from `n_legal_successors == 0` on the same row.

`status="frontier"` is logged for every candidate that survives the
bound-prune (and connectivity-prune, if enabled), immediately before the
recursive `dfs()` call that will expand it. Unlike Sokoban's FRONTIER (which
can sit unexpanded for a long time while other, lower-f open-list entries get
popped first -- and can be discarded outright without ever being expanded;
see solver.py's `discard_reason`), HP's DFS has no open list: a frontier
candidate here is expanded on the very next line, essentially always, so this
status transitions to `expanded`/`goal` almost immediately and carries much
less signal than Sokoban's -- logged for symmetry with the 5-object model and
for S1/S3 graph reconstruction, not because it's expected to be informative
on its own. No `discard_reason`-style dominance bucket exists here: chain
growth has no transposition, so there is no "candidate whose target state is
already accounted for elsewhere" case to distinguish.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

import validation

_OFFSETS = ((1, 0), (-1, 0), (0, 1), (0, -1))


@dataclass
class BnBResult:
    solved: str  # "solved" | "unsolvable" | "cutoff"
    cutoff_reason: str | None  # None | "budget" | "clock"
    fold: list[list[int]]
    solution_quality: int | None  # best H-H contact count found (None if none found)
    nodes_expanded: int
    candidates_scored: int
    peak_frontier: int
    wall_clock_ms: float
    trace_rows: list[dict] | None = None  # None unless trace=True was passed to solve()
    bound_pruned: int = 0  # candidates rejected by the bound (search-optimality)
    connectivity_pruned: int = 0  # candidates rejected by reachable_free_capacity (domain-constraint)


def _contact_capacity(i: int, n: int) -> int:
    """Structural upper bound on monomer i's total (ever) contact degree: a
    lattice site has 4 neighbors; interior monomers spend 2 on backbone
    bonds (<=2 free), chain ends spend only 1 (<=3 free)."""
    return 3 if i == 0 or i == n - 1 else 2


def _parity_suffix_capacity(sequence: str) -> tuple[list[int], list[int]]:
    """odd_suffix[i] / even_suffix[i] = total contact CAPACITY (not just
    count) of H's at odd/even indices in sequence[i:]. A single unplaced H
    monomer can end up party to more than one future contact (up to its
    `_contact_capacity`), so summing capacity -- not counting monomers -- is
    required for the bound to stay admissible. O(n) precompute, O(1) lookup
    per node."""
    n = len(sequence)
    odd_suffix = [0] * (n + 1)
    even_suffix = [0] * (n + 1)
    for i in range(n - 1, -1, -1):
        is_h = sequence[i] == "H"
        cap = _contact_capacity(i, n) if is_h else 0
        odd_suffix[i] = odd_suffix[i + 1] + (cap if i % 2 == 1 else 0)
        even_suffix[i] = even_suffix[i + 1] + (cap if i % 2 == 0 else 0)
    return odd_suffix, even_suffix


def _parity_prefix_capacity(sequence: str) -> tuple[list[int], list[int]]:
    """odd_prefix[i] / even_prefix[i] = total structural contact CAPACITY of
    H's at odd/even indices in sequence[0:i+1] -- the *static* upper bound
    on already-placed monomers' free-slot total used by `bound_weak`, as
    opposed to `po_free`/`pe_free`'s real-time tracked (and always <=) exact
    count. O(n) precompute, O(1) lookup per node."""
    n = len(sequence)
    odd_prefix = [0] * n
    even_prefix = [0] * n
    running_odd = running_even = 0
    for i in range(n):
        is_h = sequence[i] == "H"
        cap = _contact_capacity(i, n) if is_h else 0
        running_odd += cap if i % 2 == 1 else 0
        running_even += cap if i % 2 == 0 else 0
        odd_prefix[i] = running_odd
        even_prefix[i] = running_even
    return odd_prefix, even_prefix


def bound_tight(idx: int, po_free: int, pe_free: int, ctx: dict) -> int:
    """Real-time free-slot tracking (the default, corrected-bound derivation
    above)."""
    return min(ctx["odd_suffix"][idx + 1] + po_free, ctx["even_suffix"][idx + 1] + pe_free)


def bound_weak(idx: int, po_free: int, pe_free: int, ctx: dict) -> int:
    """Heuristic-strength baseline: static structural capacity in place of
    real-time free-slot tracking (module docstring). `po_free`/`pe_free`
    aren't read here -- deliberately weaker, not a bug -- see
    docs/DECISIONS.md."""
    return min(
        ctx["odd_suffix"][idx + 1] + ctx["odd_prefix"][idx],
        ctx["even_suffix"][idx + 1] + ctx["even_prefix"][idx],
    )


_BOUNDS = {"tight": bound_tight, "weak": bound_weak}


def reachable_free_capacity(tip: tuple[int, int], pos_index: dict, cutoff: int) -> int:
    """Count of free (unoccupied) lattice cells reachable from `tip` via
    other free cells, capped at `cutoff` (early exit -- callers only need to
    know whether the reachable region is >= cutoff, not its exact size, so
    this never explores more cells than it takes to disprove a deadlock).
    `tip` itself is not counted (it's the position about to be occupied by
    the monomer being placed, already spent -- this counts capacity for the
    monomers *after* it)."""
    if cutoff <= 0:
        return 0
    seen = {tip}
    frontier = [tip]
    count = 0
    while frontier and count < cutoff:
        next_frontier = []
        for x, y in frontier:
            for dx, dy in _OFFSETS:
                npos = (x + dx, y + dy)
                if npos in seen or npos in pos_index:
                    continue
                seen.add(npos)
                count += 1
                next_frontier.append(npos)
                if count >= cutoff:
                    break
            if count >= cutoff:
                break
        frontier = next_frontier
    return count


def solve(
    sequence: str,
    *,
    eval_budget: int = 1_000_000,
    timeout_s: float = 300.0,
    bound: str = "tight",
    connectivity_prune: bool = False,
    trace: bool = False,
    trace_node_cap: int = 100_000,
) -> BnBResult:
    """Search for the max-H-H-contact SAW embedding of `sequence`, exhaustively
    subject to `eval_budget` / `timeout_s`. `solved="solved"` means the pruned
    tree was fully explored and the returned fold is proven optimal;
    `solved="cutoff"` means budget/timeout hit first (fold, if any, is the
    best incumbent found, not proven optimal).

    `bound`: "tight" (default, real-time free-slot tracking) or "weak" (the
    heuristic-strength baseline -- see `bound_weak`'s docstring). Both are
    admissible, so both prove the same optimum; "weak" just needs more nodes
    to get there, mirroring Sokoban's manhattan-vs-hungarian Arm A.

    `connectivity_prune`: opt-in, off by default, zero cost/behavior change
    otherwise (proof of concept -- see module docstring and
    `reachable_free_capacity`). A domain-constraint deadlock check, the HP
    analog of Sokoban's `is_dead()`, additional to and independent of
    `bound`."""
    if not validation.is_valid_sequence(sequence):
        raise ValueError(f"invalid HP sequence: {sequence!r}")
    if bound not in _BOUNDS:
        raise ValueError(f"bound must be one of {sorted(_BOUNDS)}, got {bound!r}")
    bound_fn = _BOUNDS[bound]

    t0 = time.monotonic()
    n = len(sequence)
    odd_suffix, even_suffix = _parity_suffix_capacity(sequence)
    odd_prefix, even_prefix = _parity_prefix_capacity(sequence)
    ctx = {"odd_suffix": odd_suffix, "even_suffix": even_suffix, "odd_prefix": odd_prefix, "even_prefix": even_prefix}

    fold: list[list[int]] = [[0, 0], [1, 0]]
    pos_index: dict[tuple[int, int], int] = {(0, 0): 0, (1, 0): 1}

    def neighbor_occupants(pos: tuple[int, int]) -> list[int]:
        x, y = pos
        occ = []
        for dx, dy in _OFFSETS:
            j = pos_index.get((x + dx, y + dy))
            if j is not None:
                occ.append(j)
        return occ

    # free-slot pools for already-placed H monomers, seeded for the two
    # fixed starting monomers (see module docstring bound derivation)
    po_free = 0  # sum of free lattice-neighbor cells over placed odd-H monomers
    pe_free = 0  # ... over placed even-H monomers
    if sequence[0] == "H":
        pe_free += 4  # monomer0: no neighbors placed yet
    if sequence[1] == "H":
        po_free += 3  # monomer1: one neighbor (monomer0) already occupied
    if sequence[0] == "H":
        pe_free -= 1  # monomer0 just lost the slot monomer1 occupies

    best_fold: list[list[int]] | None = None
    best_energy: int | None = None

    counters = {
        "nodes_expanded": 0, "candidates_scored": 0, "peak_frontier": 2, "trace_seq": 0,
        "bound_pruned": 0, "connectivity_pruned": 0,
    }
    cutoff: dict[str, str | None] = {"reason": None}
    trace_rows: list[dict] | None = [] if trace else None

    def node_hash(depth: int) -> tuple:
        return tuple(map(tuple, fold[: depth + 1]))

    def dfs(idx: int, g: int, po_free: int, pe_free: int) -> None:
        nonlocal best_fold, best_energy
        if cutoff["reason"] is not None:
            return
        if time.monotonic() - t0 >= timeout_s:
            cutoff["reason"] = "clock"
            return

        counters["nodes_expanded"] += 1
        counters["peak_frontier"] = max(counters["peak_frontier"], idx + 1)

        h = bound_fn(idx, po_free, pe_free, ctx)
        node_id = node_hash(idx)
        parent_id = node_hash(idx - 1) if idx > 1 else None

        if idx == n - 1:
            is_new_best = best_energy is None or g > best_energy
            if is_new_best:
                best_energy = g
                best_fold = [list(p) for p in fold]
            if trace_rows is not None and len(trace_rows) < trace_node_cap:
                trace_rows.append({
                    "node_id": node_id, "parent_id": parent_id,
                    "g": g, "h": h, "f": g + h, "depth": idx,
                    "n_legal_successors": None, "n_pruned": None,
                    "status": "goal", "all_pruned": None, "is_new_best": is_new_best,
                    "prune_reason": None,
                    "timestamp_order": counters["trace_seq"],
                })
                counters["trace_seq"] += 1
            return

        new_idx = idx + 1
        prev = fold[idx]
        candidates = []
        for dx, dy in _OFFSETS:
            cand = (prev[0] + dx, prev[1] + dy)
            if cand in pos_index:
                continue
            if idx == 1 and cand[1] < 0:
                continue  # first-turn mirror symmetry break
            occ = neighbor_occupants(cand)  # always includes `idx` (backbone predecessor)
            contacts = sum(1 for m in occ if m != idx and sequence[m] == "H")
            candidates.append((contacts, cand, occ))

        # greedy child order: try highest-immediate-contact placements first
        # (Layer 3) so a strong incumbent is found early, tightening the
        # bound for everything explored after it
        candidates.sort(key=lambda c: -c[0])
        n_pruned = 0

        for contacts, cand, occ in candidates:
            counters["candidates_scored"] += 1
            if counters["candidates_scored"] >= eval_budget:
                cutoff["reason"] = "budget"
                return

            new_g = g + (contacts if sequence[new_idx] == "H" else 0)
            own_free = 4 - len(occ)

            hyp_po_free, hyp_pe_free = po_free, pe_free
            if sequence[new_idx] == "H":
                if new_idx % 2:
                    hyp_po_free += own_free
                else:
                    hyp_pe_free += own_free
            for m in occ:
                if sequence[m] != "H":
                    continue
                if m % 2:
                    hyp_po_free -= 1
                else:
                    hyp_pe_free -= 1

            bound_val = new_g + bound_fn(new_idx, hyp_po_free, hyp_pe_free, ctx)
            if best_energy is not None and bound_val <= best_energy:
                n_pruned += 1
                counters["bound_pruned"] += 1
                if trace_rows is not None and len(trace_rows) < trace_node_cap:
                    trace_rows.append({
                        "node_id": node_id + (tuple(cand),), "parent_id": node_id,
                        "g": new_g, "h": bound_val - new_g, "f": bound_val, "depth": new_idx,
                        "n_legal_successors": None, "n_pruned": None,
                        "status": "pruned", "all_pruned": None, "is_new_best": None,
                        "prune_reason": "bound",
                        "timestamp_order": counters["trace_seq"],
                    })
                    counters["trace_seq"] += 1
                continue  # parity/free-slot bound prune

            if connectivity_prune:
                remaining_after = n - 1 - new_idx
                if remaining_after > 0 and reachable_free_capacity(cand, pos_index, remaining_after) < remaining_after:
                    n_pruned += 1
                    counters["connectivity_pruned"] += 1
                    if trace_rows is not None and len(trace_rows) < trace_node_cap:
                        trace_rows.append({
                            "node_id": node_id + (tuple(cand),), "parent_id": node_id,
                            "g": new_g, "h": bound_val - new_g, "f": bound_val, "depth": new_idx,
                            "n_legal_successors": None, "n_pruned": None,
                            "status": "pruned", "all_pruned": None, "is_new_best": None,
                            "prune_reason": "connectivity",
                            "timestamp_order": counters["trace_seq"],
                        })
                        counters["trace_seq"] += 1
                    continue  # domain-constraint deadlock: not enough reachable free cells left

            if trace_rows is not None and len(trace_rows) < trace_node_cap:
                trace_rows.append({
                    "node_id": node_id + (tuple(cand),), "parent_id": node_id,
                    "g": new_g, "h": bound_val - new_g, "f": bound_val, "depth": new_idx,
                    "n_legal_successors": None, "n_pruned": None,
                    "status": "frontier", "all_pruned": None, "is_new_best": None,
                    "prune_reason": None,
                    "timestamp_order": counters["trace_seq"],
                })
                counters["trace_seq"] += 1

            fold.append(list(cand))
            pos_index[cand] = new_idx
            dfs(new_idx, new_g, hyp_po_free, hyp_pe_free)
            del pos_index[cand]
            fold.pop()

            if cutoff["reason"] is not None:
                return

        if trace_rows is not None and len(trace_rows) < trace_node_cap:
            n_legal = len(candidates)
            all_pruned = n_legal == 0 or n_pruned == n_legal
            trace_rows.append({
                "node_id": node_id, "parent_id": parent_id,
                "g": g, "h": h, "f": g + h, "depth": idx,
                "n_legal_successors": n_legal, "n_pruned": n_pruned,
                "status": "expanded", "all_pruned": all_pruned, "is_new_best": None,
                "prune_reason": None,
                "timestamp_order": counters["trace_seq"],
            })
            counters["trace_seq"] += 1

    dfs(1, 0, po_free, pe_free)
    wall_clock_ms = (time.monotonic() - t0) * 1000

    if cutoff["reason"] is not None:
        return BnBResult(
            solved="cutoff",
            cutoff_reason=cutoff["reason"],
            fold=best_fold if best_fold is not None else [],
            solution_quality=best_energy,
            nodes_expanded=counters["nodes_expanded"],
            candidates_scored=counters["candidates_scored"],
            peak_frontier=counters["peak_frontier"],
            wall_clock_ms=wall_clock_ms,
            trace_rows=trace_rows,
            bound_pruned=counters["bound_pruned"],
            connectivity_pruned=counters["connectivity_pruned"],
        )

    if best_fold is None:
        return BnBResult(
            solved="unsolvable",
            cutoff_reason=None,
            fold=[],
            solution_quality=None,
            nodes_expanded=counters["nodes_expanded"],
            candidates_scored=counters["candidates_scored"],
            peak_frontier=counters["peak_frontier"],
            wall_clock_ms=wall_clock_ms,
            trace_rows=trace_rows,
            bound_pruned=counters["bound_pruned"],
            connectivity_pruned=counters["connectivity_pruned"],
        )

    return BnBResult(
        solved="solved",
        cutoff_reason=None,
        fold=best_fold,
        solution_quality=best_energy,
        nodes_expanded=counters["nodes_expanded"],
        candidates_scored=counters["candidates_scored"],
        peak_frontier=counters["peak_frontier"],
        wall_clock_ms=wall_clock_ms,
        trace_rows=trace_rows,
        bound_pruned=counters["bound_pruned"],
        connectivity_pruned=counters["connectivity_pruned"],
    )
