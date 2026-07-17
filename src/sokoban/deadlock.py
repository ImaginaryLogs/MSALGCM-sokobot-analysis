"""Static dead-square precompute: reverse-pull BFS from goals (D4).

Soundness infrastructure, not a studied technique -- identical in baseline and
optimized arms so it never contaminates the weight/heuristic ablations.
"""
from __future__ import annotations

from collections import deque

from .board import Board, Cell

_DIRECTIONS: tuple[Cell, ...] = ((1, 0), (-1, 0), (0, 1), (0, -1))


def compute_dead_squares(board: Board) -> frozenset[Cell]:
    """Cells from which no crate can ever reach a goal.

    Simulates pulling a crate backward from every goal: a crate at C can be
    pulled to predecessor C-d if both C-d (crate's new cell) and C-2d (player's
    standing cell for the corresponding forward push) are floor. Cells never
    reached this way are dead -- pushing a crate into one is unrecoverable.
    """
    live: set[Cell] = set(board.goals)
    queue: deque[Cell] = deque(board.goals)

    while queue:
        cx, cy = queue.popleft()
        for dx, dy in _DIRECTIONS:
            pred = (cx - dx, cy - dy)
            behind = (cx - 2 * dx, cy - 2 * dy)
            if pred in live:
                continue
            if not board.is_floor(pred) or not board.is_floor(behind):
                continue
            live.add(pred)
            queue.append(pred)

    all_floor = {
        (x, y)
        for y in range(board.height)
        for x in range(board.width)
        if board.is_floor((x, y))
    }
    return frozenset(all_floor - live)
