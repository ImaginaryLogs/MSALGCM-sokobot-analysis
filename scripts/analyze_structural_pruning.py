"""project-proposal.md's "Assumptions" supporting question -- "What
structural features must a graph search space possess for state-pruning,
precomputing, and heuristic weight-tuning to effectively reduce exploration
time?" Not previously answered anywhere in docs/ or notebooks/ (the RQ1-6
topology framework in METHODOLOGY_SYNTHESIS.md characterizes each domain's
topology and each technique's efficiency ratio *separately*; nothing there
correlates a per-instance structural feature against a per-instance
pruning-effectiveness number). Built here by joining the two:

  - Pruning effectiveness, per instance, from results.csv (same shape as
    scripts/analyze_arms.py's Arm A/B, computed independently here since we
    need it merged against structural features rather than plotted alone):
      * Arm A ratio (heuristic strength, optimality-preserving): evals(weak
        heuristic) / evals(tight heuristic) at equal (optimal) quality.
      * Arm B ratio (weight tuning, quality-trading): evals(w=1) / evals(w=5),
        both manhattan, Sokoban only -- reported alongside the solution-quality
        cost, since CONTEXT.md is explicit that this arm trades quality for
        speed rather than getting it for free.
  - Structural features, per instance, computed from that instance's baseline
    trace (w=1 manhattan for Sokoban, tight bound for HP -- the only bound
    traced, src/protein-fold/bnb_cli.py's --bound default) via the existing
    analysis/ modules (S1/S2 pieces, docs/equivalence/cross-domain-analysis-design.md):
    branching factor, feasibility ratio, trap rate, disconnectivity AUC,
    mean Forman-Ricci curvature.

Correlates each feature against each effectiveness metric (Pearson + Spearman,
per domain) -- Spearman because n is modest here (limited to instances with
BOTH a results.csv ratio and a trace file) and a couple of large-map outliers
can otherwise dominate a Pearson r.

Run:
  uv run python scripts/analyze_structural_pruning.py --results results/results.csv \
      --trace-dir results/traces --out-dir results/analysis
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
import numpy as np
from scipy import stats as sstats

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root: `analysis` package

from analysis.curvature import mean_curvature  # noqa: E402
from analysis.shared_characteristics import branching_factors, feasibility_ratios  # noqa: E402
from analysis.topology_lite import disconnectivity_curve_normalized, trap_rate  # noqa: E402
from analysis.trace_io import domain_of, instance_id_of, read_trace  # noqa: E402


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


def heuristic_strength_ratio(rows: list[dict], *, domain: str, weak_h: str, tight_h: str) -> dict[str, dict]:
    """Same shape as scripts/analyze_arms.py's function of the same name,
    duplicated locally (rather than imported) since it's a 15-line pure
    function and importing across scripts/ would create a script-to-script
    dependency this repo doesn't otherwise have."""
    by_instance: dict[str, dict[str, dict]] = defaultdict(dict)
    for r in rows:
        if r["domain"] != domain:
            continue
        w = _num(r["weight_w"])
        if w is not None and w != 1.0:
            continue
        by_instance[r["instance_id"]][r["base_h"]] = r

    out = {}
    for instance_id, by_h in by_instance.items():
        weak, tight = by_h.get(weak_h), by_h.get(tight_h)
        if weak is None or tight is None or weak["solved"] != "1" or tight["solved"] != "1":
            continue
        weak_evals, tight_evals = _num(weak["candidate_states_evaluated"]), _num(tight["candidate_states_evaluated"])
        if not weak_evals or not tight_evals:
            continue
        out[instance_id] = {"ratio": weak_evals / tight_evals, "instance_size": _num(weak["instance_size"])}
    return out


def weight_tuning_ratio(rows: list[dict], *, w_lo: float, w_hi: float) -> dict[str, dict]:
    """Arm B pruning effectiveness: evals(w_lo)/evals(w_hi) at manhattan,
    Sokoban only (weight_w is a real knob only there). Also carries the
    quality cost (push-count increase), since a bigger eval reduction paired
    with a much worse solution isn't the same finding as one paired with an
    unchanged solution -- CONTEXT.md's quality-trading framing for this arm."""
    by_instance: dict[str, dict[float, dict]] = defaultdict(dict)
    for r in rows:
        if r["domain"] != "sokoban" or r["base_h"] != "manhattan" or r["solved"] != "1":
            continue
        w = _num(r["weight_w"])
        if w in (w_lo, w_hi):
            by_instance[r["instance_id"]][w] = r

    out = {}
    for instance_id, by_w in by_instance.items():
        lo, hi = by_w.get(w_lo), by_w.get(w_hi)
        if lo is None or hi is None:
            continue
        lo_evals, hi_evals = _num(lo["candidate_states_evaluated"]), _num(hi["candidate_states_evaluated"])
        lo_q, hi_q = _num(lo["solution_quality"]), _num(hi["solution_quality"])
        if not lo_evals or not hi_evals:
            continue
        out[instance_id] = {
            "ratio": lo_evals / hi_evals, "instance_size": _num(lo["instance_size"]),
            "quality_cost": (hi_q - lo_q) / lo_q if lo_q else None,
        }
    return out


def structural_features(rows: list[dict]) -> dict:
    bf = branching_factors(rows)
    fr = feasibility_ratios(rows)
    tr = trap_rate(rows)
    curve = disconnectivity_curve_normalized(rows)
    disc_auc = float(np.trapezoid([n for _, n in curve], [t for t, _ in curve])) if curve else None
    curv = mean_curvature(rows)
    return {
        "branching_factor_mean": statistics.mean(bf) if bf else None,
        "feasibility_ratio_mean": statistics.mean(fr) if fr else None,
        "trap_rate": tr["rate"],
        "disconnectivity_auc": disc_auc,
        "mean_curvature": curv,
    }


FEATURES = ["branching_factor_mean", "feasibility_ratio_mean", "trap_rate", "disconnectivity_auc", "mean_curvature"]


def load_structural_features(trace_dir: Path, domain: str) -> dict[str, dict]:
    out = {}
    for path in sorted(trace_dir.glob("*_trace.csv")):
        if domain_of(path) != domain:
            continue
        instance_id = instance_id_of(path, domain)
        trace_rows = list(read_trace(path))
        out[instance_id] = structural_features(trace_rows)
    return out


def correlate(effectiveness: dict[str, dict], features: dict[str, dict], *, metric_key: str) -> list[dict]:
    joined = {iid: {**features[iid], metric_key: eff[metric_key]}
              for iid, eff in effectiveness.items() if iid in features}
    out = []
    for feat in FEATURES:
        pairs = [(row[feat], row[metric_key]) for row in joined.values()
                 if row[feat] is not None and row[metric_key] is not None]
        if len(pairs) < 4:
            out.append({"feature": feat, "n": len(pairs), "pearson_r": None, "spearman_rho": None, "spearman_p": None})
            continue
        xs, ys = zip(*pairs)
        pear = sstats.pearsonr(xs, ys)
        spear = sstats.spearmanr(xs, ys)
        out.append({"feature": feat, "n": len(pairs), "pearson_r": round(float(pear.statistic), 3),
                     "pearson_p": round(float(pear.pvalue), 4), "spearman_rho": round(float(spear.statistic), 3),
                     "spearman_p": round(float(spear.pvalue), 4)})
    return out, joined


def print_and_plot(label: str, corr_rows: list[dict], joined: dict, metric_key: str, out_dir: Path, file_stem: str) -> None:
    print(f"\n  -- {label} --")
    ranked = sorted(corr_rows, key=lambda r: -abs(r["spearman_rho"] or 0))
    for r in ranked:
        if r["pearson_r"] is None:
            print(f"    {r['feature']:<24} n={r['n']}  not enough data")
            continue
        print(f"    {r['feature']:<24} n={r['n']}  pearson_r={r['pearson_r']:+.3f} (p={r['pearson_p']:.3f})  "
              f"spearman_rho={r['spearman_rho']:+.3f} (p={r['spearman_p']:.3f})")
    strongest = next((r for r in ranked if r["pearson_r"] is not None), None)
    if strongest is None or len(joined) < 4:
        return
    feat = strongest["feature"]
    xs = [row[feat] for row in joined.values() if row[feat] is not None and row[metric_key] is not None]
    ys = [row[metric_key] for row in joined.values() if row[feat] is not None and row[metric_key] is not None]
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.scatter(xs, ys, alpha=0.6)
    ax.axhline(1.0, color="gray", linestyle="--", linewidth=1)
    ax.set_xlabel(feat)
    ax.set_ylabel(metric_key)
    ax.set_title(f"{label}\nstrongest structural correlate: {feat} (spearman rho={strongest['spearman_rho']:+.3f})")
    fig.tight_layout()
    out_path = out_dir / f"{file_stem}_{feat}.png"
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"    wrote {out_path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--results", type=Path, default=Path("results/results.csv"))
    parser.add_argument("--trace-dir", type=Path, default=Path("results/traces"))
    parser.add_argument("--out-dir", type=Path, default=Path("results/analysis"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.results.exists():
        print(f"{args.results} does not exist -- run the solvers first", file=sys.stderr)
        return 1
    rows = load_rows(args.results)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    print("=== Structural features vs. pruning/weight-tuning effectiveness ===")
    print("(domain-level qualitative feature, not correlated numerically below: Sokoban's deadlock")
    print(" rejection is DECOUPLED from the heuristic -- ~59% of candidate pushes pruned regardless")
    print(" of h; HP's bound-prune is FUSED with the heuristic. docs/specs/rq_1.md. This asymmetry is")
    print(" why the two domains' feature/effectiveness correlations below aren't expected to match.)")

    all_summary_rows = []

    print("\n--- Sokoban structural features (from w=1 manhattan baseline traces) ---")
    sok_features = load_structural_features(args.trace_dir, "sokoban")
    print(f"  {len(sok_features)} instances with a baseline trace")

    arm_a_sok = heuristic_strength_ratio(rows, domain="sokoban", weak_h="manhattan", tight_h="hungarian")
    print(f"\nArm A (heuristic strength, manhattan/hungarian ratio): {len(arm_a_sok)} instances in results.csv")
    corr, joined = correlate(arm_a_sok, sok_features, metric_key="ratio")
    print_and_plot("Sokoban Arm A: structural features vs heuristic-strength ratio", corr, joined, "ratio",
                    args.out_dir, "struct_sokoban_arm_a")
    all_summary_rows += [{"domain": "sokoban", "arm": "A_heuristic_strength", **c} for c in corr]

    arm_b = weight_tuning_ratio(rows, w_lo=1.0, w_hi=5.0)
    print(f"\nArm B (weight tuning, w=1/w=5 ratio): {len(arm_b)} instances in results.csv")
    if arm_b:
        costs = [v["quality_cost"] for v in arm_b.values() if v["quality_cost"] is not None]
        if costs:
            print(f"  median solution-quality cost of that ratio: {statistics.median(costs):+.1%} more pushes")
    corr, joined = correlate(arm_b, sok_features, metric_key="ratio")
    print_and_plot("Sokoban Arm B: structural features vs weight-tuning ratio", corr, joined, "ratio",
                    args.out_dir, "struct_sokoban_arm_b")
    all_summary_rows += [{"domain": "sokoban", "arm": "B_weight_tuning", **c} for c in corr]

    print("\n--- HP-lattice structural features (from tight-bound baseline traces) ---")
    hp_features = load_structural_features(args.trace_dir, "hp_lattice")
    print(f"  {len(hp_features)} instances with a baseline trace")
    arm_a_hp = heuristic_strength_ratio(rows, domain="hp_lattice", weak_h="weak", tight_h="tight")
    print(f"\nArm A (heuristic strength, weak/tight ratio): {len(arm_a_hp)} instances in results.csv")
    corr, joined = correlate(arm_a_hp, hp_features, metric_key="ratio")
    print_and_plot("HP Arm A: structural features vs heuristic-strength ratio", corr, joined, "ratio",
                    args.out_dir, "struct_hp_arm_a")
    all_summary_rows += [{"domain": "hp_lattice", "arm": "A_heuristic_strength", **c} for c in corr]

    summary_csv = args.out_dir / "structural_pruning_correlations.csv"
    with summary_csv.open("w", newline="") as f:
        fieldnames = ["domain", "arm", "feature", "n", "pearson_r", "pearson_p", "spearman_rho", "spearman_p"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in all_summary_rows:
            writer.writerow({k: row.get(k) for k in fieldnames})
    print(f"\nwrote {summary_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
