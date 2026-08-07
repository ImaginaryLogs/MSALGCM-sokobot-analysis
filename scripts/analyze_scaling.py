"""Scalability axis: project-proposal.md's "Scalability" supporting question --
"As the grid dimensions scale or the number of movable objects increases, how
does the memory footprint and execution time change?" Not previously answered
anywhere in docs/ or notebooks/ (checked: only the RQ1-6 topology framework in
METHODOLOGY_SYNTHESIS.md exists, which doesn't touch peak_frontier/wall_clock_ms
scaling). Answered directly from results.csv -- no trace data needed.

Axes: `grid_cells` (Sokoban board size, HP has no grid so this half is
Sokoban-only) and `instance_size` (crate count for Sokoban's "movable objects",
chain length for HP -- reported separately, not pooled, since they're not the
same unit). Outcomes: `peak_frontier` (memory proxy, per STATUS.md's
Measurement section) and `wall_clock_ms` (execution time; secondary/hang-safety
metric per docs/DECISIONS.md #4, but literally what the question asks).

Fits log-log power laws y = a * x^b per (config, x-axis, y-axis) via OLS on
logs -- b is the scaling exponent, R^2 the fit quality. Runs once per
technique config (baseline w=1 manhattan, heuristic-strength hungarian @ w=1,
weight-tuned w=5 manhattan) so exponents are directly comparable: a technique
that "reduces exploration time" should show up as a flatter (smaller b) curve
here, not just a lower intercept.

Run:
  uv run python scripts/analyze_scaling.py --results results/results.csv --out-dir results/analysis
"""
from __future__ import annotations

import argparse
import csv
import math
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


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


def select(rows: list[dict], *, domain: str, base_h: str, weight_w: float | None) -> list[dict]:
    """Deduped by instance_id (last row wins) -- results.csv contains
    duplicate re-run rows for ~155/158 Sokoban baseline instances (appended
    across separate scripts/run_experiments.py invocations, same pattern
    scripts/analyze_arms.py's arm_b_pareto already documents and dedupes for
    Arm B). Undeduped, those duplicates don't bias a log-log OLS slope (the
    repeats sit on/near the same point) but they inflate the printed/reported
    n and silently double-weight ~all of Sokoban's instances relative to
    ones that only ran once."""
    by_instance: dict[str, dict] = {}
    for r in rows:
        if r["domain"] != domain or r["base_h"] != base_h or r["solved"] != "1":
            continue
        if weight_w is not None:
            w = _num(r["weight_w"])
            if w is None or abs(w - weight_w) > 1e-9:
                continue
        by_instance[r["instance_id"]] = r
    return list(by_instance.values())


def power_law_fit(xs: list[float], ys: list[float]) -> dict | None:
    """OLS fit of log(y) = a + b*log(x). Returns None if fewer than 3 usable
    (x>0, y>0) points -- not enough to say anything about a trend."""
    pairs = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None and x > 0 and y > 0]
    if len(pairs) < 3:
        return None
    lx = np.log(np.array([p[0] for p in pairs]))
    ly = np.log(np.array([p[1] for p in pairs]))
    b, a = np.polyfit(lx, ly, 1)
    pred = a + b * lx
    ss_res = float(np.sum((ly - pred) ** 2))
    ss_tot = float(np.sum((ly - ly.mean()) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    pearson_r = float(np.corrcoef(lx, ly)[0, 1]) if len(pairs) > 1 else float("nan")
    return {"n": len(pairs), "exponent_b": float(b), "intercept_a": float(a), "r2": r2, "pearson_r_loglog": pearson_r}


def multi_power_law_fit(x1s: list[float], x2s: list[float], ys: list[float]) -> dict | None:
    """Partial log-log regression log(y) = a + b1*log(x1) + b2*log(x2) --
    grid_cells and instance_size (crate count) are correlated (bigger boards
    tend to have more crates), so the single-variable exponents above
    conflate the two. This isolates each axis's independent contribution."""
    triples = [(x1, x2, y) for x1, x2, y in zip(x1s, x2s, ys) if x1 and x2 and y and x1 > 0 and x2 > 0 and y > 0]
    if len(triples) < 4:
        return None
    lx1 = np.log(np.array([t[0] for t in triples]))
    lx2 = np.log(np.array([t[1] for t in triples]))
    ly = np.log(np.array([t[2] for t in triples]))
    design = np.column_stack([np.ones_like(lx1), lx1, lx2])
    coef, *_ = np.linalg.lstsq(design, ly, rcond=None)
    a, b1, b2 = coef
    pred = design @ coef
    ss_res = float(np.sum((ly - pred) ** 2))
    ss_tot = float(np.sum((ly - ly.mean()) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return {"n": len(triples), "exp_grid_cells": float(b1), "exp_instance_size": float(b2),
            "intercept_a": float(a), "r2": r2}


CONFIGS_SOKOBAN = [
    ("baseline (w=1, manhattan)", "manhattan", 1.0),
    ("heuristic strength (hungarian, w=1)", "hungarian", 1.0),
    ("weight-tuned (manhattan, w=5)", "manhattan", 5.0),
]
CONFIGS_HP = [
    ("baseline (weak bound)", "weak", None),
    ("heuristic strength (tight bound)", "tight", None),
]


def report_sokoban(rows: list[dict], out_dir: Path) -> list[dict]:
    print("=== Sokoban: memory (peak_frontier) & time (wall_clock_ms) vs grid_cells & instance_size ===")
    fit_rows = []
    fig, axes = plt.subplots(2, 2, figsize=(11, 8))
    colors = {"baseline (w=1, manhattan)": "tab:blue", "heuristic strength (hungarian, w=1)": "tab:orange",
              "weight-tuned (manhattan, w=5)": "tab:green"}
    for label, base_h, w in CONFIGS_SOKOBAN:
        cfg_rows = select(rows, domain="sokoban", base_h=base_h, weight_w=w)
        grid_cells = [_num(r["grid_cells"]) for r in cfg_rows]
        instance_size = [_num(r["instance_size"]) for r in cfg_rows]
        peak_frontier = [_num(r["peak_frontier"]) for r in cfg_rows]
        wall_clock = [_num(r["wall_clock_ms"]) for r in cfg_rows]
        print(f"\n  -- {label} ({len(cfg_rows)} solved instances) --")
        for x_name, xs, ax_row in [("grid_cells", grid_cells, 0), ("instance_size", instance_size, 1)]:
            for y_name, ys, ax_col in [("peak_frontier", peak_frontier, 0), ("wall_clock_ms", wall_clock, 1)]:
                fit = power_law_fit(xs, ys)
                if fit is None:
                    print(f"    {y_name} ~ {x_name}^b: no data")
                    continue
                print(f"    {y_name} ~ {x_name}^b: b={fit['exponent_b']:.3f}  R^2={fit['r2']:.3f}  "
                      f"(n={fit['n']}, log-log r={fit['pearson_r_loglog']:.3f})")
                fit_rows.append({"domain": "sokoban", "config": label, "x": x_name, "y": y_name, **fit})
                ax = axes[ax_col][ax_row]
                valid = [(x, y) for x, y in zip(xs, ys) if x and y and x > 0 and y > 0]
                if valid:
                    ax.scatter(*zip(*valid), s=10, alpha=0.4, color=colors[label], label=label)
                    lx = np.linspace(min(v[0] for v in valid), max(v[0] for v in valid), 50)
                    ax.plot(lx, np.exp(fit["intercept_a"]) * lx ** fit["exponent_b"], color=colors[label], linewidth=1.5)
                ax.set_xscale("log")
                ax.set_yscale("log")
                ax.set_xlabel(x_name)
                ax.set_ylabel(y_name)
        mfit = multi_power_law_fit(grid_cells, instance_size, peak_frontier)
        if mfit:
            print(f"    peak_frontier ~ grid_cells^b1 * instance_size^b2: "
                  f"b1={mfit['exp_grid_cells']:.3f}  b2={mfit['exp_instance_size']:.3f}  R^2={mfit['r2']:.3f}")
        mfit_t = multi_power_law_fit(grid_cells, instance_size, wall_clock)
        if mfit_t:
            print(f"    wall_clock_ms ~ grid_cells^b1 * instance_size^b2: "
                  f"b1={mfit_t['exp_grid_cells']:.3f}  b2={mfit_t['exp_instance_size']:.3f}  R^2={mfit_t['r2']:.3f}")
    for ax in axes.flat:
        ax.legend(fontsize=7)
    fig.suptitle("Sokoban: memory & time scaling vs grid size / crate count, by technique")
    fig.tight_layout()
    out_path = out_dir / "scaling_sokoban.png"
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"\n  wrote {out_path}")
    return fit_rows


def report_hp(rows: list[dict], out_dir: Path) -> list[dict]:
    print("\n=== HP-lattice: memory (peak_frontier) & time (wall_clock_ms) vs instance_size (chain length) ===")
    print("  (no grid_cells axis: HP-lattice search is unbounded, not a fixed grid -- src/protein-fold/bnb_cli.py)")
    fit_rows = []
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    colors = {"baseline (weak bound)": "tab:blue", "heuristic strength (tight bound)": "tab:orange"}
    for label, base_h, w in CONFIGS_HP:
        cfg_rows = select(rows, domain="hp_lattice", base_h=base_h, weight_w=w)
        instance_size = [_num(r["instance_size"]) for r in cfg_rows]
        peak_frontier = [_num(r["peak_frontier"]) for r in cfg_rows]
        wall_clock = [_num(r["wall_clock_ms"]) for r in cfg_rows]
        print(f"\n  -- {label} ({len(cfg_rows)} solved instances) --")
        for y_name, ys, ax in [("peak_frontier", peak_frontier, axes[0]), ("wall_clock_ms", wall_clock, axes[1])]:
            fit = power_law_fit(instance_size, ys)
            if fit is None:
                print(f"    {y_name} ~ instance_size^b: no data")
                continue
            print(f"    {y_name} ~ instance_size^b: b={fit['exponent_b']:.3f}  R^2={fit['r2']:.3f}  "
                  f"(n={fit['n']}, log-log r={fit['pearson_r_loglog']:.3f})")
            fit_rows.append({"domain": "hp_lattice", "config": label, "x": "instance_size", "y": y_name, **fit})
            valid = [(x, y) for x, y in zip(instance_size, ys) if x and y and x > 0 and y > 0]
            if valid:
                ax.scatter(*zip(*valid), s=10, alpha=0.4, color=colors[label], label=label)
                lx = np.linspace(min(v[0] for v in valid), max(v[0] for v in valid), 50)
                ax.plot(lx, np.exp(fit["intercept_a"]) * lx ** fit["exponent_b"], color=colors[label], linewidth=1.5)
            ax.set_xscale("log")
            ax.set_yscale("log")
            ax.set_xlabel("instance_size (chain length)")
            ax.set_ylabel(y_name)
    for ax in axes:
        ax.legend(fontsize=8)
    fig.suptitle("HP-lattice: memory & time scaling vs chain length, by technique")
    fig.tight_layout()
    out_path = out_dir / "scaling_hp.png"
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"\n  wrote {out_path}")
    return fit_rows


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

    fit_rows = report_sokoban(rows, args.out_dir)
    fit_rows += report_hp(rows, args.out_dir)

    fits_csv = args.out_dir / "scaling_fits.csv"
    if fit_rows:
        fieldnames = ["domain", "config", "x", "y", "n", "exponent_b", "intercept_a", "r2", "pearson_r_loglog"]
        with fits_csv.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(fit_rows)
        print(f"\nwrote {fits_csv} ({len(fit_rows)} fits)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
