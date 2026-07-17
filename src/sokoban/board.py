"""Static Sokoban map: walls, goals, passability, dead-square storage."""
from __future__ import annotations

from dataclasses import dataclass, field

Cell = tuple[int, int]


@dataclass(frozen=True)
class Board:
    width: int
    height: int
    walls: frozenset[Cell]
    goals: frozenset[Cell]
    dead_squares: frozenset[Cell] = field(default_factory=frozenset)

    def in_bounds(self, cell: Cell) -> bool:
        x, y = cell
        return 0 <= x < self.width and 0 <= y < self.height

    def is_wall(self, cell: Cell) -> bool:
        return (not self.in_bounds(cell)) or cell in self.walls

    def is_floor(self, cell: Cell) -> bool:
        return self.in_bounds(cell) and cell not in self.walls

    def is_dead(self, cell: Cell) -> bool:
        return cell in self.dead_squares

    def with_dead_squares(self, dead_squares: frozenset[Cell]) -> "Board":
        return Board(self.width, self.height, self.walls, self.goals, dead_squares)
