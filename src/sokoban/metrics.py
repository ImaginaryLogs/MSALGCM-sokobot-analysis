"""D6 CSV schema: build one shared-schema row per run from a solve result.

`candidate_states_evaluated` is the cross-domain join key (PROVISIONAL, D5/D6)
-- defaults to `candidates_scored` pending Roan's HP-engine sign-off. Both raw
Sokoban counters are always logged alongside it so no re-run is needed if the
signed schema ends up picking `nodes_expanded` instead.
"""
from __future__ import annotations

import uuid

from .board import Board
from .solver import SolveResult

CSV_COLUMNS = [
    "run_id", "domain", "instance_id", "instance_size", "grid_cells",
    "algorithm", "weight_w", "base_h", "seed",
    "candidate_states_evaluated", "nodes_expanded", "candidates_scored",
    "solved", "cutoff_reason", "solution_quality", "quality_target",
    "wall_clock_ms", "peak_frontier", "git_sha",
]

_SOLVED_CODE = {"solved": 1, "unsolvable": 0, "cutoff": "cutoff"}


def build_row(
    *,
    board: Board,
    instance_id: str,
    crate_count: int,
    result: SolveResult,
    weight_w: float,
    base_h: str,
    algorithm: str = "wastar",
    seed: int | None = None,
    quality_target: int | float | None = None,
    git_sha: str | None = None,
    join_key_counter: str = "candidates_scored",
) -> dict:
    """Assemble one D6 row. `join_key_counter` picks which raw counter feeds
    `candidate_states_evaluated` -- must be "nodes_expanded" or "candidates_scored"."""
    counters = {"nodes_expanded": result.nodes_expanded, "candidates_scored": result.candidates_scored}
    free_cells = board.width * board.height - len(board.walls)
    return {
        "run_id": str(uuid.uuid4()),
        "domain": "sokoban",
        "instance_id": instance_id,
        "instance_size": crate_count,
        "grid_cells": free_cells,
        "algorithm": algorithm,
        "weight_w": weight_w,
        "base_h": base_h,
        "seed": seed if seed is not None else "NA",
        "candidate_states_evaluated": counters[join_key_counter],
        "nodes_expanded": result.nodes_expanded,
        "candidates_scored": result.candidates_scored,
        "solved": _SOLVED_CODE[result.solved],
        "cutoff_reason": result.cutoff_reason if result.cutoff_reason is not None else "NA",
        "solution_quality": result.solution_quality if result.solution_quality is not None else "NA",
        "quality_target": quality_target if quality_target is not None else "NA",
        "wall_clock_ms": result.wall_clock_ms,
        "peak_frontier": result.peak_frontier,
        "git_sha": git_sha if git_sha is not None else "NA",
    }
