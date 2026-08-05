"""Arm A (heuristic strength, scalar efficiency ratio) and Arm B (heuristic
weight tuning, Pareto curve) analysis from results.csv (D6 schema, see
src/sokoban/metrics.py / docs/DECISIONS.md #9, #12, #13).

Arm A now runs for BOTH domains: Sokoban's manhattan (weak) vs hungarian
(tight) @ w=1, and HP's `bound="weak"` vs `bound="tight"` (docs/DECISIONS.md
#13, src/protein-fold/bnb.py) -- the same equal-quality scalar-ratio shape,
different concrete heuristics per domain.

Arm B (weight tuning, Pareto curve) stays Sokoban-only: src/protein-fold/bnb.py
is an exhaustive optimality-proving search with no weight-w knob at all --
`weight_w` is always "NA" for hp_lattice rows. STATUS.md's original task list
framed Arm B as both-domain ("CJ Sokoban / Roan HP"); the engine that was
actually built doesn't have the mechanism for a bounded-suboptimal weighting
scheme (see the "should we add weight-w to HP" discussion -- deliberately not
done: it would mean trading away the completeness/optimality-proof B&B was
chosen for, with no equally-established literature technique to anchor it,
unlike Sokoban's Weighted A*).

Needs results.csv to actually contain the comparison configs -- both
heuristics at w=1 for Sokoban's Arm A, both bounds for HP's Arm A, the weight
grid for Arm B. A results.csv containing only a default single-run baseline
has none of these; every arm prints "no data" with the exact command to
populate it, rather than a misleading empty plot.

Run:
  uv run python scripts/analyze_arms.py --results results/results.csv --out-dir results/analysis
"""
from __future__ import annotations

import argparse
import csv
import statistics
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

_REGEN_HINT_SOKOBAN = "  run: uv run python scripts/run_experiments.py --out <same --results path>"
_REGEN_HINT_HP = ("  run: uv run python src/protein-fold/bnb_cli.py --fasta <sequences> --bound tight ...\n"
                   "       uv run python src/protein-fold/bnb_cli.py --fasta <sequences> --bound weak  ...\n"
                   "       (same --out both times)")


def load_rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _num(v: str | None) -> float | None:
    if v in (None, "", "NA"):
        return None
    try:
        return float(v)
    except ValueError:
        return None


def heuristic_strength_ratio(rows: list[dict], *, domain: str, weak_h: str, tight_h: str) -> list[dict]:
    """Arm A, generic over domain: weak_h vs tight_h, equal-quality scalar
    ratio = evals(weak) / evals(tight) (CONTEXT.md's 'Efficiency ratio' --
    only defensible when both reach the same, optimal, quality). Restricted
    to weight_w==1.0 where a domain has a weight knob at all (Sokoban);
    HP's weight_w is always "NA", so the filter is a no-op there."""
    by_instance: dict[str, dict[str, dict]] = defaultdict(dict)
    for r in rows:
        if r["domain"] != domain:
            continue
        w = _num(r["weight_w"])
        if w is not None and w != 1.0:
            continue
        by_instance[r["instance_id"]][r["base_h"]] = r

    out = []
    for instance_id, by_h in by_instance.items():
        weak, tight = by_h.get(weak_h), by_h.get(tight_h)
        if weak is None or tight is None:
            continue
        if weak["solved"] != "1" or tight["solved"] != "1":
            continue  # ratio only defensible at equal (optimal) quality
        weak_evals = _num(weak["candidate_states_evaluated"])
        tight_evals = _num(tight["candidate_states_evaluated"])
        if not weak_evals or not tight_evals:
            continue
        out.append({
            "instance_id": instance_id,
            "instance_size": weak["instance_size"],
            "weak_evals": weak_evals,
            "tight_evals": tight_evals,
            "ratio": weak_evals / tight_evals,
        })
    return out


def arm_b_pareto(rows: list[dict]) -> dict[str, list[dict]]:
    """manhattan, weight grid, Sokoban only -- evals vs solution_quality per
    instance, one Pareto series per map (quality-trading arm, no scalar
    ratio -- CONTEXT.md). Keyed and deduped by weight_w: a CSV built by
    appending across separate CLI runs (src/sokoban/cli.py, src/sokoban/emit.py)
    can easily contain more than one row for the same (instance, w) --
    re-runs, not new grid points -- so row *count* alone isn't "a curve";
    what matters is the count of DISTINCT weights. Last row wins per weight."""
    by_instance: dict[str, dict[float, dict]] = defaultdict(dict)
    for r in rows:
        if r["domain"] != "sokoban" or r["base_h"] != "manhattan" or r["solved"] != "1":
            continue
        w, evals, quality = _num(r["weight_w"]), _num(r["candidate_states_evaluated"]), _num(r["solution_quality"])
        if w is None or evals is None or quality is None:
            continue
        by_instance[r["instance_id"]][w] = {"w": w, "evals": evals, "quality": quality}

    out = {}
    for instance_id, by_w in by_instance.items():
        if len(by_w) > 1:  # need >1 DISTINCT weight to be a "curve"
            out[instance_id] = sorted(by_w.values(), key=lambda p: p["w"])
    return out


def plot_ratio(ratios: list[dict], out_path: Path, *, title: str, weak_label: str, tight_label: str) -> None:
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.scatter([r["instance_size"] for r in ratios], [r["ratio"] for r in ratios], alpha=0.6)
    ax.axhline(1.0, color="gray", linestyle="--", linewidth=1, label="no improvement")
    ax.set_xlabel("instance_size")
    ax.set_ylabel(f"efficiency ratio ({weak_label} evals / {tight_label} evals)")
    ax.set_title(title)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_arm_b(series_by_instance: dict[str, list[dict]], out_path: Path, max_series: int = 20) -> None:
    fig, ax = plt.subplots(figsize=(6, 4))
    for instance_id, series in list(series_by_instance.items())[:max_series]:
        ax.plot([p["evals"] for p in series], [p["quality"] for p in series],
                marker="o", alpha=0.5, linewidth=1, label=instance_id)
    ax.set_xlabel("evals (candidate_states_evaluated)")
    ax.set_ylabel("solution_quality (push count)")
    ax.set_title(f"Arm B: weight-tuning Pareto curves "
                 f"({min(len(series_by_instance), max_series)} of {len(series_by_instance)} instances shown)")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def _report_ratio_arm(
    rows: list[dict], *, domain: str, weak_h: str, tight_h: str,
    label: str, out_dir: Path, file_stem: str, regen_hint: str,
) -> None:
    print(f"=== Arm A: heuristic strength -- {label} ({weak_h} vs {tight_h}) ===")
    ratios = heuristic_strength_ratio(rows, domain=domain, weak_h=weak_h, tight_h=tight_h)
    if not ratios:
        print(f"  no data: results.csv has no ({weak_h}, {tight_h}) pair solved to equal quality for any instance.")
        print(regen_hint)
        return
    vals = [r["ratio"] for r in ratios]
    print(f"  {len(ratios)} instances with both heuristics solved to equal quality")
    print(f"  mean={statistics.mean(vals):.3f}  median={statistics.median(vals):.3f}  "
          f"min={min(vals):.3f}  max={max(vals):.3f}")
    ratios_csv = out_dir / f"{file_stem}_ratios.csv"
    with ratios_csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(ratios[0]))
        writer.writeheader()
        writer.writerows(ratios)
    plot_path = out_dir / f"{file_stem}_ratio.png"
    plot_ratio(ratios, plot_path, title=f"Arm A: {label} heuristic-strength efficiency ratio",
               weak_label=weak_h, tight_label=tight_h)
    print(f"  wrote {ratios_csv} and {plot_path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--results", type=Path, default=Path("results/results.csv"))
    parser.add_argument("--out-dir", type=Path, default=Path("results/analysis"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.results.exists():
        print(f"{args.results} does not exist -- run the solvers first", file=sys.stderr)
        return 1
    rows = load_rows(args.results)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    _report_ratio_arm(
        rows, domain="sokoban", weak_h="manhattan", tight_h="hungarian", label="Sokoban",
        out_dir=args.out_dir, file_stem="arm_a_sokoban", regen_hint=_REGEN_HINT_SOKOBAN,
    )
    _report_ratio_arm(
        rows, domain="hp_lattice", weak_h="weak", tight_h="tight", label="HP",
        out_dir=args.out_dir, file_stem="arm_a_hp", regen_hint=_REGEN_HINT_HP,
    )

    print("=== Arm B: heuristic weight tuning (manhattan, weight grid, Sokoban only -- see module docstring) ===")
    series = arm_b_pareto(rows)
    if not series:
        print("  no data: results.csv has no instance with >1 manhattan weight solved.")
        print(_REGEN_HINT_SOKOBAN)
    else:
        grid_sizes = sorted({len(s) for s in series.values()})
        print(f"  {len(series)} instances with a multi-point weight series; series lengths seen: {grid_sizes}")
        plot_arm_b(series, args.out_dir / "arm_b_pareto.png")
        print(f"  wrote {args.out_dir / 'arm_b_pareto.png'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
