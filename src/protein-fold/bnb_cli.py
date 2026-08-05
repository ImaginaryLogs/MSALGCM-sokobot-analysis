"""CLI: run one or many HP sequences through the B&B solver, emit D6 CSV rows
using the schema shared with Sokoban (`sokoban.metrics.CSV_COLUMNS`) so the
two domains join on one CSV per docs/DECISIONS.md #4/#8 -- `algorithm="bnb"`
per ADR 0002 (docs/adr/0002-hp-engine-bnb.md).

Accepts either raw HP sequences or standard 20-amino-acid sequences (FASTA
one-letter codes), positionally or via --fasta -- auto-converted through
`utils.convert_to_hp`, the same fallback `protein.py`'s `Protein` class
already used for the Metropolis engine (previously not wired into this
engine at all: a downloaded FASTA sequence would have just raised
ValueError out of `bnb.solve`).

Run: uv run python src/protein-fold/bnb_cli.py HHPHPPHH [MORE...] --out results/results.csv
     uv run python src/protein-fold/bnb_cli.py --fasta downloaded.fasta --out results/results.csv
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
import uuid
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))  # flat-import siblings: bnb, utils, validation
sys.path.insert(0, str(_HERE.parent))  # src/: sokoban package (shared CSV schema)

import bnb  # noqa: E402
import utils  # noqa: E402
import validation  # noqa: E402
from sokoban.emit import write_row  # noqa: E402
from sokoban.metrics import CSV_COLUMNS  # noqa: E402

_SOLVED_CODE = {"solved": 1, "unsolvable": 0, "cutoff": "cutoff"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the HP-lattice B&B solver over one or more sequences.")
    parser.add_argument("sequences", nargs="*",
                         help="HP or standard-20-aa sequence(s), e.g. HPHPPHHPH or MKTAYIAKQR...")
    parser.add_argument("--fasta", type=Path, default=None,
                         help="read additional sequence(s) from a (possibly multi-record) FASTA file")
    parser.add_argument("--bound", choices=["tight", "weak"], default="tight",
                         help="heuristic-strength arm (bnb.py module docstring): 'tight' (default, "
                              "real-time free-slot tracking) or 'weak' (static-capacity baseline, "
                              "the HP analog of Sokoban's manhattan)")
    parser.add_argument("--connectivity-prune", action="store_true", dest="connectivity_prune",
                         help="opt-in domain-constraint deadlock prune (bnb.py module docstring, "
                              "docs/DECISIONS.md #15) -- proof of concept, off by default")
    parser.add_argument("--eval-budget", type=int, default=2_000_000, dest="eval_budget",
                         help="primary stop: candidates_scored cap, matches Sokoban's locked N (D6/#9)")
    parser.add_argument("--timeout", type=float, default=300.0,
                         help="wall-clock safety cutoff in seconds (hang-safety only, never primary)")
    parser.add_argument("--out", type=Path, default=Path("results/results.csv"), help="CSV output path (D6 schema)")
    parser.add_argument("--git-sha", default=None, dest="git_sha")
    parser.add_argument("--trace", action="store_true",
                         help="opt-in per-node trace (docs/equivalence/cross-domain-analysis-design.md S0); "
                              "one CSV per sequence under --trace-dir, capped at --trace-node-cap rows")
    parser.add_argument("--trace-node-cap", type=int, default=100_000, dest="trace_node_cap")
    parser.add_argument("--trace-dir", type=Path, default=Path("results/traces"), dest="trace_dir")
    return parser


def _read_fasta(path: Path) -> list[tuple[str, str]]:
    """[(header, sequence), ...] from a (possibly multi-record) FASTA file."""
    records: list[tuple[str, str]] = []
    header: str | None = None
    chunks: list[str] = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(">"):
            if header is not None:
                records.append((header, "".join(chunks)))
            header, chunks = line[1:].strip(), []
        else:
            chunks.append(line)
    if header is not None:
        records.append((header, "".join(chunks)))
    return records


def to_hp_sequence(sequence: str) -> str:
    """Accept either an already-HP sequence or a standard 20-aa sequence,
    auto-converting the latter via `utils.convert_to_hp` -- the same
    fallback `protein.py`'s `Protein` class uses for the Metropolis engine."""
    seq = sequence.strip().upper()
    if validation.is_valid_sequence(seq):
        return seq
    return utils.convert_to_hp(seq)


def _write_trace_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def build_row(*, instance_id: str, sequence: str, result: bnb.BnBResult, bound: str, git_sha: str | None) -> dict:
    return {
        "run_id": str(uuid.uuid4()),
        "domain": "hp_lattice",
        "instance_id": instance_id,
        "instance_size": len(sequence),
        "grid_cells": "NA",  # HP lattice is unbounded, unlike Sokoban's fixed board
        "algorithm": "bnb",
        "weight_w": "NA",  # no weight knob on this engine (unlike Sokoban's w)
        "base_h": bound,  # "tight" | "weak" -- heuristic-strength arm, bnb.py module docstring
        "seed": "NA",  # deterministic search, no RNG
        "candidate_states_evaluated": result.nodes_expanded,  # locked join key, ADR 0002
        "nodes_expanded": result.nodes_expanded,
        "candidates_scored": result.candidates_scored,
        "solved": _SOLVED_CODE[result.solved],
        "cutoff_reason": result.cutoff_reason if result.cutoff_reason is not None else "NA",
        "solution_quality": result.solution_quality if result.solution_quality is not None else "NA",
        "quality_target": "NA",
        "wall_clock_ms": result.wall_clock_ms,
        "peak_frontier": result.peak_frontier,
        "git_sha": git_sha if git_sha is not None else "NA",
    }


def run(args: argparse.Namespace) -> int:
    instances = [(f"seq{i}", s) for i, s in enumerate(args.sequences)]
    if args.fasta:
        for j, (header, seq) in enumerate(_read_fasta(args.fasta)):
            label = re.sub(r"[^A-Za-z0-9_.-]+", "_", header)[:60] or f"fasta{j}"
            instances.append((label, seq))
    if not instances:
        print("no sequences given: pass sequence(s) positionally or via --fasta", file=sys.stderr)
        return 1

    for instance_id, raw_sequence in instances:
        try:
            hp_sequence = to_hp_sequence(raw_sequence)
        except ValueError as exc:
            print(f"{instance_id}: SKIPPED, could not convert to HP ({exc})", file=sys.stderr)
            continue

        result = bnb.solve(
            hp_sequence, eval_budget=args.eval_budget, timeout_s=args.timeout, bound=args.bound,
            connectivity_prune=args.connectivity_prune,
            trace=args.trace, trace_node_cap=args.trace_node_cap,
        )
        # no new D6 column for a proof-of-concept flag -- self-documenting via base_h suffix instead
        base_h_label = args.bound + ("+conn" if args.connectivity_prune else "")
        row = build_row(
            instance_id=instance_id, sequence=hp_sequence, result=result, bound=base_h_label, git_sha=args.git_sha,
        )
        assert set(row) == set(CSV_COLUMNS), "bnb row schema drifted from shared D6 CSV_COLUMNS"
        write_row(args.out, row)
        converted_note = "" if raw_sequence.upper() == hp_sequence else f" (converted from {raw_sequence})"
        prune_note = f" bound_pruned={result.bound_pruned}" if args.connectivity_prune else ""
        if args.connectivity_prune:
            prune_note += f" connectivity_pruned={result.connectivity_pruned}"
        print(
            f"{instance_id}: {hp_sequence}{converted_note}: {result.solved} "
            f"quality={result.solution_quality} nodes={result.nodes_expanded} "
            f"candidates={result.candidates_scored}{prune_note}"
        )
        if args.trace and result.trace_rows:
            trace_path = args.trace_dir / f"{instance_id}_trace.csv"
            _write_trace_csv(trace_path, result.trace_rows)
            print(f"  trace: {len(result.trace_rows)} rows -> {trace_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
