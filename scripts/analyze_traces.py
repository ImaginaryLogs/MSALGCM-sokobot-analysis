"""Cross-domain trace analysis: the S1(-lite)/S2/S3(-lite) pieces buildable
without new heavy dependencies (ripser/giotto-tda/kmapper/GraphRicciCurvature
-- not installed; S1.1's full branching-tree/S1.2/S1.4/S1.5 stay deferred) or
new solver instrumentation beyond the S0 trace
(docs/equivalence/cross-domain-analysis-design.md). See analysis/topology_lite.py,
analysis/shared_characteristics.py, analysis/category_lite.py module
docstrings for exactly what each piece computes and what it deliberately
does NOT (S2.3 move_type, S3.3 naturality slack, S3.4 ablation factorization
all need genuinely new work, not just more trace data).

Aggregates over every *_trace.csv under --trace-dir, split by domain
(filename `hp_*` = HP, else Sokoban). S2 / S1.3-trap-rate / S3.1-transitions
run over every row in every file (cheap, single streaming pass each). S1.1's
disconnectivity curve is per-instance and heavier (union-find over up to
trace_node_cap rows), so it only runs on --disconnectivity-sample instances
per domain (the largest, by row count) rather than the whole corpus.

Run:
  uv run python scripts/analyze_traces.py --trace-dir results/traces --out-dir results/analysis
"""
from __future__ import annotations

import argparse
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root: `analysis` package

from analysis.category_lite import eigen_spectrum, kl_divergence, transition_counts, transition_matrix  # noqa: E402
from analysis.shared_characteristics import (  # noqa: E402
    branching_factors, feasibility_ratios, plateau_run_lengths,
)
from analysis.topology_lite import disconnectivity_curve, trap_rate  # noqa: E402
from analysis.trace_io import domain_of, read_trace  # noqa: E402


def _summary(values: list[float]) -> dict:
    if not values:
        return {"n": 0}
    return {
        "n": len(values), "mean": round(statistics.mean(values), 4),
        "median": round(statistics.median(values), 4), "min": min(values), "max": max(values),
    }


def _fmt_complex(v: complex) -> str:
    return f"{v.real:.3f}" if abs(v.imag) < 1e-9 else f"{v.real:.3f}{v.imag:+.3f}j"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--trace-dir", type=Path, default=Path("results/traces"))
    parser.add_argument("--out-dir", type=Path, default=Path("results/analysis"))
    parser.add_argument("--disconnectivity-sample", type=int, default=2,
                         help="largest N instances per domain to run the S1.1-lite disconnectivity curve on")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    files = sorted(args.trace_dir.glob("*_trace.csv"))
    if not files:
        print(f"no *_trace.csv files under {args.trace_dir}", file=sys.stderr)
        return 1

    by_domain: dict[str, list[Path]] = {"sokoban": [], "hp_lattice": []}
    for f in files:
        by_domain[domain_of(f)].append(f)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    domain_matrices: dict[str, tuple[list[str], list[list[float]]]] = {}

    for domain, paths in by_domain.items():
        if not paths:
            continue
        print(f"=== {domain} ({len(paths)} instances) ===")

        all_branching: list[int] = []
        all_feasibility: list[float] = []
        all_plateau: list[int] = []
        trap_expanded = trap_hits = 0
        counts: dict[tuple[str, str], int] = {}
        sizes: list[tuple[int, Path]] = []

        for path in paths:
            rows = list(read_trace(path))
            sizes.append((len(rows), path))
            all_branching.extend(branching_factors(rows))
            all_feasibility.extend(feasibility_ratios(rows))
            all_plateau.extend(plateau_run_lengths(rows))
            t = trap_rate(rows)
            trap_expanded += t["n_expanded"]
            trap_hits += t["n_trap"]
            for k, v in transition_counts(rows).items():
                counts[k] = counts.get(k, 0) + v

        print("  S2.1 branching factor:      ", _summary(all_branching))
        print("  S2.2 feasibility ratio:     ", _summary(all_feasibility))
        print("  S2.4 plateau run length:    ", _summary(all_plateau))
        if trap_expanded:
            print(f"  S1.3 trap rate:              {trap_hits}/{trap_expanded} expanded nodes "
                  f"({trap_hits / trap_expanded:.4f})")
        else:
            print("  S1.3 trap rate:               no data")

        labels, mat = transition_matrix(counts)
        domain_matrices[domain] = (labels, mat)
        print(f"  S3.1 status transition matrix (labels={labels}):")
        for label, row in zip(labels, mat):
            print(f"    {label:>10}: " + " ".join(f"{v:.3f}" for v in row))

        sizes.sort(reverse=True)
        for _, path in sizes[: args.disconnectivity_sample]:
            rows = list(read_trace(path))
            curve = disconnectivity_curve(rows)
            out_csv = args.out_dir / f"{path.stem}_disconnectivity.csv"
            with out_csv.open("w") as f:
                f.write("tau,n_components\n")
                for tau, n in curve:
                    f.write(f"{tau},{n}\n")
            print(f"  S1.1-lite disconnectivity curve for {path.name} -> {out_csv}")

    if len(domain_matrices) == 2:
        (label_a, (labels_a, mat_a)), (label_b, (labels_b, mat_b)) = domain_matrices.items()
        print(f"=== S3.2: {label_a} vs {label_b} transition-matrix comparison ===")
        if labels_a == labels_b:
            for i, label in enumerate(labels_a):
                # a status with no outgoing transitions in EITHER domain (terminal
                # states -- goal/pruned are always leaves, never a parent) has an
                # all-zero row on both sides: "no data vs no data" is trivially 0
                # by kl_divergence's convention, but printing a bare 0.0000 reads
                # exactly like "identical distributions" -- flag it as vacuous
                # instead so it isn't mistaken for a real (non-)finding.
                if sum(mat_a[i]) == 0 and sum(mat_b[i]) == 0:
                    print(f"  KL({label_a}[{label}] || {label_b}[{label}]) = N/A "
                          f"(no outgoing transitions from '{label}' in either domain -- vacuous, not a finding)")
                    continue
                kl = kl_divergence(mat_a[i], mat_b[i])
                print(f"  KL({label_a}[{label}] || {label_b}[{label}]) = {kl:.4f}")
            print(f"  {label_a} eigen-spectrum:  " + ", ".join(_fmt_complex(v) for v in eigen_spectrum(mat_a)))
            print(f"  {label_b} eigen-spectrum:  " + ", ".join(_fmt_complex(v) for v in eigen_spectrum(mat_b)))
        else:
            print(f"  skipped: domains observed different status sets ({labels_a} vs {labels_b}), "
                  f"matrices aren't directly comparable")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
