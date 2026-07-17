"""Push-state: crates + normalized player region, canonical key, legal-push successors (D3).

State = crate config + player's reachable region, normalized to that region's
canonical (min) cell so two states differing only by which floor tile the
player stands on collapse to one node. Successors are legal crate pushes only;
`g` = push count. Dead-square filtering is NOT applied here -- it happens in
solver.py, after the successor is scored, so `candidates_scored` (D5) counts
deadlock-pruned pushes rather than silently dropping them.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from .board import Board, Cell

_DIRECTIONS: tuple[Cell, ...] = ((1, 0), (-1, 0), (0, 1), (0, -1))


@dataclass(frozen=True)
class State:
    crates: frozenset[Cell]
    player: Cell  # normalized: canonical min-index cell of player's reachable region

    def key(self) -> tuple[tuple[Cell, ...], Cell]:
        """Sorted crate-cell tuple + normalized player cell (D5 serial identity)."""
        return (tuple(sorted(self.crates)), self.player)


@dataclass(frozen=True)
class Push:
    crate_from: Cell
    crate_to: Cell
    direction: Cell


def reachable_region(board: Board, crates: frozenset[Cell], start: Cell) -> frozenset[Cell]:
    """Flood-fill of cells the player can walk to without disturbing crates."""
    seen = {start}
    queue: deque[Cell] = deque([start])
    while queue:
        cx, cy = queue.popleft()
        for dx, dy in _DIRECTIONS:
            nxt = (cx + dx, cy + dy)
            if nxt in seen or nxt in crates or not board.is_floor(nxt):
                continue
            seen.add(nxt)
            queue.append(nxt)
    return frozenset(seen)


def normalize_player(board: Board, crates: frozenset[Cell], player: Cell) -> Cell:
    region = reachable_region(board, crates, player)
    return min(region)


def make_state(board: Board, crates: frozenset[Cell], player: Cell) -> State:
    return State(crates=crates, player=normalize_player(board, crates, player))


def successors(board: Board, state: State) -> list[tuple[State, Push]]:
    """Every legal crate push from `state`, paired with the resulting state.

    "Legal" = destination is floor and unoccupied, and the player can reach the
    push-from cell. Dead-square destinations are still included -- solver.py
    scores them (D5: candidates_scored counts deadlock-pruned successors) then
    prunes them from the open list.
    """
    region = reachable_region(board, state.crates, state.player)
    results: list[tuple[State, Push]] = []
    for crate in state.crates:
        cx, cy = crate
        for dx, dy in _DIRECTIONS:
            dest = (cx + dx, cy + dy)
            push_from = (cx - dx, cy - dy)
            if dest in state.crates or not board.is_floor(dest):
                continue
            if push_from not in region:
                continue
            new_crates = frozenset((state.crates - {crate}) | {dest})
            new_state = make_state(board, new_crates, crate)
            results.append((new_state, Push(crate_from=crate, crate_to=dest, direction=(dx, dy))))
    return results


def is_solved(board: Board, state: State) -> bool:
    return state.crates == board.goals
