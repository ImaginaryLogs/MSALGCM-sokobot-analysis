"""Base heuristic seam (D2). Manhattan ships week 1; Hungarian is a same-signature
Phase-2 build -- the strong-h half of the optimality-preserving arm (D8)."""
from __future__ import annotations

from typing import Callable

from scipy.optimize import linear_sum_assignment

from .board import Board, Cell

Heuristic = Callable[[Board, "frozenset[Cell]"], float]


def manhattan(board: Board, crates: frozenset[Cell]) -> float:
    """Each crate to its nearest goal, summed. Ignores walls/collisions; admissible."""
    total = 0
    for cx, cy in crates:
        total += min(abs(cx - gx) + abs(cy - gy) for gx, gy in board.goals)
    return total


def hungarian(board: Board, crates: frozenset[Cell]) -> float:
    """Min-cost one-to-one crate-to-goal matching (Manhattan cost), via scipy's
    Hungarian algorithm. Tighter than per-crate nearest-goal (forbids two crates
    claiming the same goal) while staying admissible: the true solution's
    crate-goal pairing is one of the feasible assignments minimized over."""
    crate_list = list(crates)
    goal_list = list(board.goals)
    cost = [
        [abs(cx - gx) + abs(cy - gy) for gx, gy in goal_list]
        for cx, cy in crate_list
    ]
    row_ind, col_ind = linear_sum_assignment(cost)
    return float(sum(cost[r][c] for r, c in zip(row_ind, col_ind)))
