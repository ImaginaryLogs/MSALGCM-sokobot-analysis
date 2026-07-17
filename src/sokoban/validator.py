"""Pure-Python safety net (validation bar): replay validity + small-map UCS
optimality oracle. Runs on every solve.

Admissible `h` + strict `g>stored` argues the *algorithm* is optimal; it does
not prove the *implementation* is -- a `g>=stored` typo (D5) yields
valid-but-suboptimal results that a replay-only check passes blind. The
oracle below is independent of solver.py and deadlock.py by construction (it
walks the raw push graph, unpruned) so a bug in either is still caught.
"""
from __future__ import annotations

from collections import deque

from .board import Board
from .state import Push, State, is_solved, reachable_region, successors


class ValidationError(ValueError):
    pass


def replay(board: Board, start: State, push_sequence: list[Push]) -> None:
    """Apply the emitted push sequence and assert crates land on goals."""
    crates = set(start.crates)
    player = start.player
    for push in push_sequence:
        if push.crate_from not in crates:
            raise ValidationError(f"replay: no crate at {push.crate_from}")
        push_from = (
            push.crate_from[0] - push.direction[0],
            push.crate_from[1] - push.direction[1],
        )
        region = reachable_region(board, frozenset(crates), player)
        if push_from not in region:
            raise ValidationError(f"replay: player cannot reach {push_from} to push {push.crate_from}")
        if push.crate_to in crates or not board.is_floor(push.crate_to):
            raise ValidationError(f"replay: illegal destination {push.crate_to}")
        crates.discard(push.crate_from)
        crates.add(push.crate_to)
        player = push.crate_from  # player ends up where the crate was
    if frozenset(crates) != board.goals:
        raise ValidationError(f"replay: final crates {crates} != goals {board.goals}")


def optimal_push_count(board: Board, start: State) -> int | None:
    """Brute-force BFS (uniform edge cost = 1 push) over the push graph.
    Returns the optimal push count, or None if unsolvable. Small maps only."""
    if is_solved(board, start):
        return 0
    visited = {start.key()}
    queue: deque[tuple[State, int]] = deque([(start, 0)])
    while queue:
        state, g = queue.popleft()
        for new_state, _push in successors(board, state):
            nk = new_state.key()
            if nk in visited:
                continue
            visited.add(nk)
            if is_solved(board, new_state):
                return g + 1
            queue.append((new_state, g + 1))
    return None


def assert_optimal(board: Board, start: State, w1_quality: int | None) -> None:
    """Assert a w=1 solver run's quality matches BFS-optimal Q*."""
    q_star = optimal_push_count(board, start)
    if q_star is None:
        if w1_quality is not None:
            raise ValidationError("oracle: BFS found no solution but w=1 solver reported one")
        return
    if w1_quality != q_star:
        raise ValidationError(f"oracle: w=1 quality {w1_quality} != BFS optimal {q_star}")
