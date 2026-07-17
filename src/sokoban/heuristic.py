"""Base heuristic seam (D2). Manhattan ships week 1; Hungarian is a same-signature
Phase-2 build -- the strong-h half of the optimality-preserving arm (D8)."""
from __future__ import annotations

from typing import Callable

from .board import Board, Cell

Heuristic = Callable[[Board, "frozenset[Cell]"], float]


def manhattan(board: Board, crates: frozenset[Cell]) -> float:
    """Each crate to its nearest goal, summed. Ignores walls/collisions; admissible."""
    total = 0
    for cx, cy in crates:
        total += min(abs(cx - gx) + abs(cy - gy) for gx, gy in board.goals)
    return total
