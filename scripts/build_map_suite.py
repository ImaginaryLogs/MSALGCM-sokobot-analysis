"""One-off tool: filter src/sokoban/maps/_all/ down to the map suite (D2
baseline-anchor rule -- w=1 Manhattan must prove optimal on every suite map).

Run: uv run python scripts/build_map_suite.py

For each map in maps/_all (recursively): solve with w=1, base_h=manhattan,
--validate (runs the small-map UCS optimality oracle). Maps that solve AND
validate optimal move to maps/. Maps that hit the eval budget, fail to solve,
or fail the oracle stay in maps/_all and get logged to
maps/EXCLUDED.md as w=1-censored (per D2 -- never silently dropped, never
substituted with best-found-so-far).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from sokoban.heuristic import manhattan  # noqa: E402
from sokoban.loader import load_map  # noqa: E402
from sokoban.solver import solve  # noqa: E402
from sokoban.validator import ValidationError, assert_optimal  # noqa: E402

MAPS_DIR = ROOT / "src" / "sokoban" / "maps"
SOURCE_DIR = MAPS_DIR / "_all"
EVAL_BUDGET = 1_000_000
TIMEOUT_S = 60.0

# Small-map UCS oracle (validator.py) is O(full state space) -- only run it
# below this crate count, matching D7's "small-map" scoping. Larger maps that
# solve at w=1 still count as suite-eligible on the algorithm's own
# optimality argument (admissible h + g>stored, ADR 0001); they just skip the
# independent oracle cross-check.
ORACLE_CRATE_LIMIT = 6


def main() -> None:
    included: list[tuple[str, int]] = []
    excluded: list[tuple[str, str]] = []

    for map_path in sorted(SOURCE_DIR.rglob("*.txt")):
        rel = map_path.relative_to(SOURCE_DIR)
        try:
            board, crates, player = load_map(map_path)
        except Exception as exc:  # noqa: BLE001 -- report and keep going
            excluded.append((str(rel), f"parse error: {exc}"))
            continue

        from sokoban.state import make_state

        start = make_state(board, crates, player)
        result = solve(board, start, w=1.0, heuristic=manhattan,
                        eval_budget=EVAL_BUDGET, timeout_s=TIMEOUT_S)

        if result.solved == "cutoff":
            excluded.append((str(rel), f"w=1-censored (cutoff_reason={result.cutoff_reason})"))
            continue
        if result.solved == "unsolvable":
            excluded.append((str(rel), "proven unsolvable -- not a solve-quality suite map"))
            continue

        if len(crates) <= ORACLE_CRATE_LIMIT:
            try:
                assert_optimal(board, start, result.solution_quality)
            except ValidationError as exc:
                excluded.append((str(rel), f"UCS oracle disagreement: {exc}"))
                continue

        dest = MAPS_DIR / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(map_path.read_bytes())
        included.append((str(rel), len(crates)))

    report = MAPS_DIR / "EXCLUDED.md"
    lines = [
        "# Excluded maps (D2 baseline-anchor rule)",
        "",
        "Maps here failed to prove w=1 Manhattan optimal (censored, unsolvable, or",
        "parse error). NOT substituted with best-found-so-far -- see D2. Kept in",
        "`_all/` for reference; not part of the scored suite.",
        "",
    ]
    for name, reason in excluded:
        lines.append(f"- `{name}` -- {reason}")
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Included {len(included)} maps in suite (crate counts: "
          f"{sorted(c for _, c in included)})")
    print(f"Excluded {len(excluded)} maps -- see {report.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
