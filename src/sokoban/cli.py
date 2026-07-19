"""CLI: run one or many maps through the weighted A* solver, emit D6 CSV rows."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .emit import write_row
from .heuristic import hungarian, manhattan
from .loader import load_map
from .metrics import build_row
from .solver import solve
from .state import make_state
from .validator import ValidationError, assert_optimal, replay

_HEURISTICS = {"manhattan": manhattan, "hungarian": hungarian}


def _resolve_heuristic(name: str):
    return _HEURISTICS[name]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Sokoban weighted A* solver over one or more maps.")
    parser.add_argument("maps", nargs="+", type=Path, help="path(s) to maps/<name>.txt")
    parser.add_argument("--w", type=float, default=1.0, help="weight for f=g+w*h (default 1.0 = optimal)")
    parser.add_argument("--base-h", choices=["manhattan", "hungarian"], default="manhattan", dest="base_h")
    parser.add_argument("--eval-budget", type=int, default=1_000_000, dest="eval_budget",
                         help="primary stop: candidates_scored cap, shared across the suite (D6)")
    parser.add_argument("--timeout", type=float, default=300.0,
                         help="wall-clock safety cutoff in seconds (hang-safety only, never primary -- D6)")
    parser.add_argument("--seed", type=int, default=None, help="RNG seed (NA for deterministic wastar)")
    parser.add_argument("--out", type=Path, default=Path("results/results.csv"), help="CSV output path (D6 schema)")
    parser.add_argument("--validate", action="store_true",
                         help="run validator.py replay, plus the small-map optimality oracle when --w=1")
    parser.add_argument("--git-sha", default=None, dest="git_sha")
    return parser


def run(args: argparse.Namespace) -> int:
    heuristic = _resolve_heuristic(args.base_h)
    exit_code = 0
    for map_path in args.maps:
        board, crates, player = load_map(map_path)
        start = make_state(board, crates, player)
        result = solve(
            board, start,
            w=args.w, heuristic=heuristic,
            eval_budget=args.eval_budget, timeout_s=args.timeout,
        )

        # replay runs on every solve (validation bar, not opt-in) -- cheap,
        # O(solution length), catches silent solver bugs. The UCS optimality
        # oracle is O(full state space) so it stays behind --validate.
        if result.solved == "solved":
            try:
                replay(board, start, result.push_sequence)
            except ValidationError as exc:
                print(f"VALIDATION FAILED [{map_path.stem}]: {exc}", file=sys.stderr)
                exit_code = 1

        if args.validate and args.w == 1.0 and result.solved != "cutoff":
            try:
                quality = result.solution_quality if result.solved == "solved" else None
                assert_optimal(board, start, quality)
            except ValidationError as exc:
                print(f"VALIDATION FAILED [{map_path.stem}]: {exc}", file=sys.stderr)
                exit_code = 1

        row = build_row(
            board=board, instance_id=map_path.stem, crate_count=len(crates),
            result=result, weight_w=args.w, base_h=args.base_h,
            seed=args.seed, git_sha=args.git_sha,
        )
        write_row(args.out, row)
        print(
            f"{map_path.stem}: {result.solved} quality={result.solution_quality} "
            f"nodes={result.nodes_expanded} candidates={result.candidates_scored}"
        )
    return exit_code


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
