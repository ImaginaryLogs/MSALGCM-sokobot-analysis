"""Phase-2 batch runner: Arm A (heuristic strength) + Arm B (weight tuning),
in-process over the full map suite -> one shared D6 CSV.

Locked via grill 2026-07-18 (docs/DECISIONS.md #9):
- Arm A: manhattan vs hungarian, w=1.0, scalar-ratio arm (D8).
- Arm B: manhattan only, weight grid below, Pareto arm (D8). No cross with
  hungarian -- keeps the two arms independent variables.
- The (manhattan, w=1.0) cell is shared by both arms and only run once.
- Eval budget N and its measurement: see docs/DECISIONS.md #9.

Run: uv run python scripts/run_experiments.py [--out PATH] [--eval-budget N]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from sokoban.emit import write_row  # noqa: E402
from sokoban.heuristic import hungarian, manhattan  # noqa: E402
from sokoban.loader import load_map  # noqa: E402
from sokoban.metrics import build_row  # noqa: E402
from sokoban.solver import solve  # noqa: E402
from sokoban.state import make_state  # noqa: E402

MAPS_DIR = ROOT / "src" / "sokoban" / "maps"
_HEURISTICS = {"manhattan": manhattan, "hungarian": hungarian}
WEIGHT_GRID = [1.0, 1.25, 1.5, 2.0, 3.0, 5.0]
DEFAULT_EVAL_BUDGET = 2_000_000  # locked 2026-07-18: max candidates_scored across 155-map
# suite (w=1 manhattan probe) was 975695 -- ~2x headroom. See docs/DECISIONS.md #9.
TIMEOUT_S = 90.0


def _suite_maps() -> list[Path]:
    return sorted(p for p in MAPS_DIR.rglob("*.txt") if "_all" not in p.parts)


def _configs() -> list[tuple[str, float]]:
    """(base_h, w) cells, deduped -- (manhattan, 1.0) is shared by both arms."""
    cells = {("manhattan", w) for w in WEIGHT_GRID}
    cells.add(("hungarian", 1.0))
    return sorted(cells)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "results.csv")
    parser.add_argument("--eval-budget", type=int, default=DEFAULT_EVAL_BUDGET, dest="eval_budget")
    parser.add_argument("--timeout", type=float, default=TIMEOUT_S)
    parser.add_argument("--git-sha", default=None, dest="git_sha")
    args = parser.parse_args()

    maps = _suite_maps()
    configs = _configs()
    print(f"{len(maps)} maps x {len(configs)} configs = {len(maps) * len(configs)} runs -> {args.out}")

    for map_path in maps:
        board, crates, player = load_map(map_path)
        start = make_state(board, crates, player)
        for base_h, w in configs:
            result = solve(
                board, start, w=w, heuristic=_HEURISTICS[base_h],
                eval_budget=args.eval_budget, timeout_s=args.timeout,
            )
            row = build_row(
                board=board, instance_id=map_path.stem, crate_count=len(crates),
                result=result, weight_w=w, base_h=base_h, git_sha=args.git_sha,
            )
            write_row(args.out, row)
            print(
                f"{map_path.stem} w={w} h={base_h}: {result.solved} "
                f"quality={result.solution_quality} nodes={result.nodes_expanded}"
            )


if __name__ == "__main__":
    main()
