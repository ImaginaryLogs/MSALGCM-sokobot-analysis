"""Weighted A*: f = g + w*h over the push-state graph, closed-list TT (D1/D5).

Not IDA* -- Sokoban's transposition (many push orders -> same crate config)
makes a persistent closed list mandatory. Closed-list revisit predicate is the
strict `g > stored` skip (never `>=`, which would drop equal-cost optimal
paths). Stops at first solution, a shared eval budget (primary), or a
wall-clock safety cutoff (hang-safety only, never the primary stop -- D6).
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


def solve(
    board: Board,
    start: State,
    *,
    w: float = 1.0,
    heuristic: Heuristic = manhattan,
    eval_budget: int = 1_000_000,
    timeout_s: float = 300.0,
) -> SolveResult:
    t0 = time.monotonic()
    counter = itertools.count()

    g_score: dict = {start.key(): 0}
    closed: dict = {}
    came_from: dict = {}

    open_heap: list = [(w * heuristic(board, start.crates), 0, next(counter), start)]
    nodes_expanded = 0
    candidates_scored = 0
    peak_frontier = 1

    while open_heap:
        if time.monotonic() - t0 >= timeout_s:
            return _cutoff("clock", nodes_expanded, candidates_scored, peak_frontier, t0)

        f, g, _, state = heapq.heappop(open_heap)
        key = state.key()

        if key in closed and g > closed[key]:
            continue  # dominated stale heap entry (D5: strict g>stored)
        closed[key] = g
        nodes_expanded += 1

        if is_solved(board, state):
            return SolveResult(
                solved="solved",
                cutoff_reason=None,
                push_sequence=_reconstruct(came_from, key),
                solution_quality=g,
                nodes_expanded=nodes_expanded,
                candidates_scored=candidates_scored,
                peak_frontier=peak_frontier,
                wall_clock_ms=(time.monotonic() - t0) * 1000,
            )

        for new_state, push in successors(board, state):
            candidates_scored += 1
            h = heuristic(board, new_state.crates)  # scored before any pruning (D5)
            if candidates_scored >= eval_budget:
                return _cutoff("budget", nodes_expanded, candidates_scored, peak_frontier, t0)

            if board.is_dead(push.crate_to):
                continue  # deadlock-pruned (D4), already counted+scored above
            nk = new_state.key()
            new_g = g + 1
            if nk in closed and new_g > closed[nk]:
                continue  # dominated (D5)
            if nk not in g_score or new_g < g_score[nk]:
                g_score[nk] = new_g
                came_from[nk] = (key, push)
                heapq.heappush(open_heap, (new_g + w * h, new_g, next(counter), new_state))

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
    )


def _cutoff(reason: str, nodes_expanded: int, candidates_scored: int, peak_frontier: int, t0: float) -> SolveResult:
    return SolveResult(
        solved="cutoff",
        cutoff_reason=reason,
        push_sequence=[],
        solution_quality=None,
        nodes_expanded=nodes_expanded,
        candidates_scored=candidates_scored,
        peak_frontier=peak_frontier,
        wall_clock_ms=(time.monotonic() - t0) * 1000,
    )


def _reconstruct(came_from: dict, key) -> list[Push]:
    path: list[Push] = []
    while key in came_from:
        prev_key, push = came_from[key]
        path.append(push)
        key = prev_key
    path.reverse()
    return path
