"""Shared trace-CSV loading for cross-domain analysis. Reads the S0 output
(docs/equivalence/cross-domain-analysis-design.md) produced by
src/sokoban/solver.py / src/protein-fold/bnb.py's `trace=True` and written by
src/sokoban/cli.py / src/protein-fold/bnb_cli.py's `--trace`.
"""
from __future__ import annotations

import csv
from collections.abc import Iterator
from pathlib import Path


def _to_float(v: str) -> float | None:
    if v in ("", "NA"):
        return None
    return float(v)


def _to_int(v: str) -> int | None:
    if v in ("", "NA"):
        return None
    return int(v)


def _to_bool(v: str) -> bool | None:
    if v in ("", "NA", "None"):
        return None
    return v == "True"


def read_trace(path: Path) -> Iterator[dict]:
    """Yield typed rows from one trace CSV. Streaming -- doesn't hold the
    whole file in memory (traces can run up to trace_node_cap rows, default
    100k)."""
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            yield {
                "node_id": row["node_id"],
                "parent_id": row["parent_id"] or None,
                "g": _to_float(row["g"]),
                "h": _to_float(row["h"]),
                "f": _to_float(row["f"]),
                "depth": _to_int(row["depth"]),
                "n_legal_successors": _to_int(row["n_legal_successors"]),
                "n_pruned": _to_int(row["n_pruned"]),
                "status": row["status"],
                "all_pruned": _to_bool(row["all_pruned"]),
                "discard_reason": row.get("discard_reason") or None,  # Sokoban-only column
                "timestamp_order": _to_int(row["timestamp_order"]),
            }


def instance_id_of(path: Path, domain: str) -> str:
    """Reverses the trace filename back to the `instance_id` used as the
    join key in `results/results.csv` -- mechanical, not a guess: mirrors
    exactly how `src/sokoban/cli.py`/`src/protein-fold/bnb_cli.py` name the
    file they write (`{instance_id}_w{w}_{base_h}_trace.csv` for Sokoban,
    `{instance_id}_trace.csv` for HP), the same `instance_id` each CLI passes
    to `emit.py` for the results-CSV row. Not a general-purpose parser --
    `domain_of`'s caution about not trusting filename conventions is about
    *inferring domain*; this only ever runs *after* domain is already known,
    to undo a suffix this project's own code appended."""
    stem = path.name
    if not stem.endswith("_trace.csv"):
        raise ValueError(f"{path}: doesn't end in _trace.csv")
    stem = stem[: -len("_trace.csv")]
    if domain == "sokoban":
        import re

        m = re.match(r"^(.*)_w[0-9.]+_[A-Za-z]+$", stem)
        if not m:
            raise ValueError(f"{path}: sokoban trace filename doesn't match _w<weight>_<base_h>")
        return m.group(1)
    return stem


def domain_of(path: Path) -> str:
    """Inferred from the header row, not the filename: instance labels are
    user-chosen (a FASTA header, a bare sequence-index label like "seq0", a
    map stem, ...) and can't be relied on to carry any naming convention.
    The column sets are structurally different instead: Sokoban's trace has
    `f_plateau` (src/sokoban/solver.py), HP's has `is_new_best`
    (src/protein-fold/bnb.py) -- always true regardless of what the instance
    was called."""
    with path.open(newline="", encoding="utf-8") as f:
        header = f.readline()
    if "is_new_best" in header:
        return "hp_lattice"
    if "f_plateau" in header:
        return "sokoban"
    raise ValueError(f"{path}: header has neither f_plateau nor is_new_best -- not a recognized trace CSV")
