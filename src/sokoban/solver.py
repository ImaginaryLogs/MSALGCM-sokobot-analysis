"""Weighted A*: f = g + w*h over the push-state graph, closed-list TT (D1/D5).

Not IDA* -- Sokoban's transposition (many push orders -> same crate config)
makes a persistent closed list mandatory. Closed-list revisit predicate is the
strict `g > stored` skip (never `>=`, which would drop equal-cost optimal
paths). Stops at first solution, a shared eval budget (primary), or a
wall-clock safety cutoff (hang-safety only, never the primary stop -- D6).

Optional per-node trace (`trace=True`, docs/equivalence/cross-domain-analysis-design.md
S0): opt-in, off by default, zero cost/behavior change otherwise. When on,
appends one row per expanded node, capped at `trace_node_cap` rows (default
100k) so a run can't blow up storage regardless of `eval_budget` -- the
search itself still runs to its normal stopping condition, only the trace
stops accumulating. `node_id`/`parent_id` reuse each state's own `.key()`
(already the canonical hash) rather than a separate id scheme.

S3.1's PRUNED category is a near-free addition to this same loop, reusing a
branch that already exists rather than adding a new call site: the existing
`board.is_dead(...)` deadlock check IS a domain-constraint rejection, exactly
S3.1's PRUNED definition. Gives partial (not full) FRONTIER insight for
free; true per-node FRONTIER (states generated but neither expanded nor
pruned) would need a log call at generation regardless of outcome, which
this does not add.

S1.3/S3.1's TRAP ("index-0 critical cell", live-checked per the doc's own
suggestion as "successors' min f >= this node's f") is deliberately NOT
collapsed into a single `status` value here -- empirically (see
tests/test_sokoban.py) that naive check fires on nearly every node under a
*consistent* heuristic (Manhattan/Hungarian both are: one push changes h by
exactly +-1, so f is non-decreasing along any edge by construction -- an
ordinary A* invariant, not a search difficulty), making it noise at w=1.
Two separate, honestly-named columns instead:
  - `all_pruned`: every successor was domain-constraint-rejected (or there
    were none) -- a genuine dead end, rare, meaningful in any config.
  - `f_plateau`: the doc's naive check. Uninformative at w=1 with a
    consistent heuristic (fires almost everywhere); becomes a real signal
    for w>1 (Arm B), since w*h loses the consistency guarantee.
"""
from __future__ import annotations

import heapq
import itertools
import time
from dataclasses import dataclass

from .board import Board
from .heuristic import Heuristic, manhattan
from .state import Push, State, is_solved, successors


@dataclass
class SolveResult:
    solved: str  # "solved" | "unsolvable" | "cutoff"
    cutoff_reason: str | None  # None | "budget" | "clock"
    push_sequence: list[Push]
    solution_quality: int | None
    nodes_expanded: int
    candidates_scored: int
    peak_frontier: int
    wall_clock_ms: float
    trace_rows: list[dict] | None = None  # None unless trace=True was passed to solve()


def solve(
    board: Board,
    start: State,
    *,
    w: float = 1.0,
    heuristic: Heuristic = manhattan,
    eval_budget: int = 1_000_000,
    timeout_s: float = 300.0,
    trace: bool = False,
    trace_node_cap: int = 100_000,
) -> SolveResult:
    t0 = time.monotonic()
    counter = itertools.count()
    trace_seq = itertools.count()
    trace_rows: list[dict] | None = [] if trace else None

    g_score: dict = {start.key(): 0}
    closed: dict = {}
    came_from: dict = {}

    open_heap: list = [(w * heuristic(board, start.crates), 0, next(counter), start)]
    nodes_expanded = 0
    candidates_scored = 0
    peak_frontier = 1

    while open_heap:
        if time.monotonic() - t0 >= timeout_s:
            return _cutoff("clock", nodes_expanded, candidates_scored, peak_frontier, t0, trace_rows)

        f, g, _, state = heapq.heappop(open_heap)
        key = state.key()

        if key in closed and g > closed[key]:
            continue  # dominated stale heap entry (D5: strict g>stored)
        closed[key] = g
        nodes_expanded += 1

        goal = is_solved(board, state)
        succs = [] if goal else list(successors(board, state))
        n_pruned = 0
        min_successor_f: float | None = None

        for new_state, push in succs:
            candidates_scored += 1
            h = heuristic(board, new_state.crates)  # scored before any pruning (D5)
            if candidates_scored >= eval_budget:
                return _cutoff("budget", nodes_expanded, candidates_scored, peak_frontier, t0, trace_rows)

            if board.is_dead(push.crate_to):
                n_pruned += 1
                if trace_rows is not None and len(trace_rows) < trace_node_cap:
                    trace_rows.append({
                        "node_id": new_state.key(),
                        "parent_id": key,
                        "g": g + 1, "h": h, "f": g + 1 + w * h, "depth": g + 1,
                        "n_legal_successors": None, "n_pruned": None,
                        "status": "pruned",
                        "all_pruned": None, "f_plateau": None,
                        "timestamp_order": next(trace_seq),
                    })
                continue  # deadlock-pruned (D4), already counted+scored above

            succ_f = g + 1 + w * h
            if min_successor_f is None or succ_f < min_successor_f:
                min_successor_f = succ_f

            nk = new_state.key()
            new_g = g + 1
            if nk in closed and new_g > closed[nk]:
                continue  # dominated (D5)
            if nk not in g_score or new_g < g_score[nk]:
                g_score[nk] = new_g
                came_from[nk] = (key, push)
                heapq.heappush(open_heap, (new_g + w * h, new_g, next(counter), new_state))

        if trace_rows is not None and len(trace_rows) < trace_node_cap:
            all_pruned = (not goal) and len(succs) > 0 and n_pruned == len(succs)
            f_plateau = (not goal) and (min_successor_f is None or min_successor_f >= f)
            trace_rows.append({
                "node_id": key,
                "parent_id": came_from[key][0] if key in came_from else None,
                "g": g, "h": ((f - g) / w) if w else None, "f": f, "depth": g,
                "n_legal_successors": len(succs), "n_pruned": n_pruned,
                "status": "goal" if goal else "expanded",
                "all_pruned": all_pruned, "f_plateau": f_plateau,
                "timestamp_order": next(trace_seq),
            })

        if goal:
            return SolveResult(
                solved="solved",
                cutoff_reason=None,
                push_sequence=_reconstruct(came_from, key),
                solution_quality=g,
                nodes_expanded=nodes_expanded,
                candidates_scored=candidates_scored,
                peak_frontier=peak_frontier,
                wall_clock_ms=(time.monotonic() - t0) * 1000,
                trace_rows=trace_rows,
            )

        peak_frontier = max(peak_frontier, len(open_heap) + len(closed))

    return SolveResult(
        solved="unsolvable",
        cutoff_reason=None,
        push_sequence=[],
        solution_quality=None,
        nodes_expanded=nodes_expanded,
        candidates_scored=candidates_scored,
        peak_frontier=peak_frontier,
        wall_clock_ms=(time.monotonic() - t0) * 1000,
        trace_rows=trace_rows,
    )


def _cutoff(
    reason: str,
    nodes_expanded: int,
    candidates_scored: int,
    peak_frontier: int,
    t0: float,
    trace_rows: list[dict] | None = None,
) -> SolveResult:
    return SolveResult(
        solved="cutoff",
        cutoff_reason=reason,
        push_sequence=[],
        solution_quality=None,
        nodes_expanded=nodes_expanded,
        candidates_scored=candidates_scored,
        peak_frontier=peak_frontier,
        wall_clock_ms=(time.monotonic() - t0) * 1000,
        trace_rows=trace_rows,
    )


def _reconstruct(came_from: dict, key) -> list[Push]:
    path: list[Push] = []
    while key in came_from:
        prev_key, push = came_from[key]
        path.append(push)
        key = prev_key
    path.reverse()
    return path
