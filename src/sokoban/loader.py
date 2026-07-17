"""Parse a single maps/<name>.txt into a Board + initial crate/player layout.

Char set (from Java FileReader/SokoBot, fact not decision): `#` wall, `.` goal,
`$` crate, `@` player, `*` crate+goal, `+` player+goal, ` ` floor. Ragged lines
are padded to the widest row with floor, matching the Java Scanner reader this
format is ported from.
"""
from __future__ import annotations

from pathlib import Path

from .board import Board, Cell
from .deadlock import compute_dead_squares

WALL = "#"
GOAL = "."
CRATE = "$"
PLAYER = "@"
CRATE_ON_GOAL = "*"
PLAYER_ON_GOAL = "+"
FLOOR = " "

GOAL_CHARS = frozenset({GOAL, CRATE_ON_GOAL, PLAYER_ON_GOAL})
CRATE_CHARS = frozenset({CRATE, CRATE_ON_GOAL})
PLAYER_CHARS = frozenset({PLAYER, PLAYER_ON_GOAL})
VALID_CHARS = frozenset({WALL, FLOOR}) | GOAL_CHARS | CRATE_CHARS | PLAYER_CHARS


class MapParseError(ValueError):
    pass


def load_map(path: str | Path) -> tuple[Board, frozenset[Cell], Cell]:
    """Returns (board with dead_squares populated, initial crates, initial player cell)."""
    text = Path(path).read_text(encoding="utf-8")
    lines = text.splitlines()
    while lines and lines[-1].strip() == "":
        lines.pop()
    if not lines:
        raise MapParseError(f"empty map: {path}")

    height = len(lines)
    width = max(len(line) for line in lines)

    walls: set[Cell] = set()
    goals: set[Cell] = set()
    crates: set[Cell] = set()
    player: Cell | None = None

    for y, line in enumerate(lines):
        for x in range(width):
            ch = line[x] if x < len(line) else FLOOR
            if ch not in VALID_CHARS:
                raise MapParseError(f"unrecognized tile {ch!r} at ({x},{y}) in {path}")
            cell = (x, y)
            if ch == WALL:
                walls.add(cell)
            if ch in GOAL_CHARS:
                goals.add(cell)
            if ch in CRATE_CHARS:
                crates.add(cell)
            if ch in PLAYER_CHARS:
                if player is not None:
                    raise MapParseError(f"multiple player starts in {path}")
                player = cell

    if player is None:
        raise MapParseError(f"no player start in {path}")
    if len(crates) != len(goals):
        raise MapParseError(
            f"crate/goal count mismatch in {path}: {len(crates)} crates, {len(goals)} goals"
        )

    board = Board(width=width, height=height, walls=frozenset(walls), goals=frozenset(goals))
    board = board.with_dead_squares(compute_dead_squares(board))
    return board, frozenset(crates), player
