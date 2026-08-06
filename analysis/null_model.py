"""S1 null-model control (docs/equivalence/cross-domain-analysis-design.md
Section 1's closing "Null-model check" note, never built until now --
docs/DECISIONS.md 2026-08-06). For each method in S1, that note calls for
also running it on "a random induced subgraph of the same size drawn from
the full domain state graph (not search-selected)" -- the control that lets
a topological finding (disconnectivity shape, mean curvature, ...) be
attributed to the heuristic/pruning the real solver applies, rather than
just being a generic property of a grid-/lattice-like combinatorial graph.

`random_priority_search` is that control, made domain-generic: a best-first
search whose priority is i.i.d. uniform random (NOT f = g + w*h) and which
accepts every domain-legal successor `neighbors_fn` offers -- no is_dead
deadlock filtering for Sokoban, no bound-prune for HP, since deciding what
to reject is itself part of what's under test, not a domain given. `h` is
still computed and logged (via `score_fn`, the real heuristic/bound
function) purely for the `f` column, so `disconnectivity_curve` -- which
sweeps thresholds over `f` -- stays directly comparable to the real
search's curve; it is never used to choose what to expand next.

Domain-specific wiring (successor generation, heuristic scoring) lives in
the notebook, not here -- this module stays domain-neutral like the rest of
`analysis/`, only consuming/producing the same row shape
`analysis.trace_io.read_trace` yields.
"""
from __future__ import annotations

import heapq
import itertools
import random
from collections.abc import Callable, Hashable, Iterable
from typing import TypeVar

State = TypeVar("State")


def random_priority_search(
    start: State,
    neighbors_fn: Callable[[State], Iterable[tuple[State, float]]],
    key_fn: Callable[[State], Hashable],
    *,
    target_expanded: int,
    seed: int,
    score_fn: Callable[[State], float] | None = None,
) -> list[dict]:
    """Best-first search over `neighbors_fn`, random priority, dedup via
    `key_fn` (a strict `g > stored` skip, mirroring both real solvers'
    closed-list predicate -- D5/bnb.py). Stops after `target_expanded` pops
    or when the frontier empties, whichever comes first (a small/sparse
    instance can run dry before reaching the target -- not an error).

    `neighbors_fn(state) -> [(new_state, step_cost), ...]`: every
    domain-legal successor, paired with its g-increment (1 per push for
    Sokoban; H-H contacts gained for HP, matching each domain's own g
    definition so `f` stays on the same scale as the real trace).

    Returns rows shaped like `analysis.trace_io.read_trace`'s output
    (`node_id`, `parent_id`, `g`, `h`, `f`, `depth`, `status`,
    `all_pruned`, `timestamp_order` -- `n_legal_successors`/`n_pruned` are
    always `None`, not tracked here) so every existing S1 function
    (`disconnectivity_curve*`, `analysis.curvature.*`) runs unmodified.
    """
    rng = random.Random(seed)
    counter = itertools.count()
    g_score: dict[Hashable, float] = {}
    depth_score: dict[Hashable, int] = {}  # hop count -- tracked separately from g,
    # since g is a domain cost (pushes for Sokoban, contacts for HP) that
    # doesn't equal hop count once step_cost != 1 (true for every HP edge
    # onto a P monomer, or an H with zero new contacts)
    came_from: dict[Hashable, Hashable | None] = {}

    start_key = key_fn(start)
    g_score[start_key] = 0.0
    depth_score[start_key] = 0
    came_from[start_key] = None
    open_heap: list[tuple[float, float, int, State]] = [(rng.random(), 0.0, next(counter), start)]

    closed: dict[Hashable, float] = {}
    rows: list[dict] = []
    expanded = 0

    while open_heap and expanded < target_expanded:
        _, g, _, state = heapq.heappop(open_heap)
        key = key_fn(state)
        if key in closed and g > closed[key]:
            continue  # dominated stale heap entry
        closed[key] = g

        h = score_fn(state) if score_fn is not None else None
        rows.append({
            "node_id": key, "parent_id": came_from[key],
            "g": g, "h": h, "f": (g + h) if h is not None else g,
            "depth": depth_score[key], "n_legal_successors": None, "n_pruned": None,
            "status": "expanded", "all_pruned": None,
            "timestamp_order": expanded,
        })
        expanded += 1

        for new_state, step_cost in neighbors_fn(state):
            nk = key_fn(new_state)
            ng = g + step_cost
            if nk in g_score and ng >= g_score[nk]:
                continue
            g_score[nk] = ng
            depth_score[nk] = depth_score[key] + 1
            came_from[nk] = key
            heapq.heappush(open_heap, (rng.random(), ng, next(counter), new_state))

    return rows


def truncate_to_size(rows: list[dict], n: int) -> list[dict]:
    """Size-match a real trace to the null model's `target_expanded`: first
    `n` expanded/goal rows by `timestamp_order`. Comparing graphs of very
    different sizes would confound "shape differs because of guidance" with
    "shape differs because one graph is bigger" -- both sides of every S1
    null-model comparison here use exactly `n` nodes."""
    visited = sorted(
        (r for r in rows if r["status"] in ("expanded", "goal")),
        key=lambda r: r["timestamp_order"],
    )
    return visited[:n]
