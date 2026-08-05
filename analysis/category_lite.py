"""S3.1/S3.2 lite. Status labeling already lives in the S0 trace (`status`
column, populated live at expansion time -- src/sokoban/solver.py /
src/protein-fold/bnb.py); this builds the transition matrix from it via
parent_id joins, instead of the doc's `log_status()` call at every state
touch. Two consequences, both documented at the point the trace feature was
built (docs/DECISIONS.md #11):

  - Only 3 of the doc's 5 objects are ever observed here (EXPANDED, PRUNED,
    GOAL). There's no live FRONTIER tracking (states generated but neither
    expanded nor pruned), so the matrix's FRONTIER row/column is
    structurally absent here, not zero -- don't read a 0 as "FRONTIER never
    transitions anywhere."
  - TRAP isn't a `status` value either (src/sokoban/solver.py's docstring
    explains why: the doc's naive live TRAP check fires on almost every node
    under a consistent heuristic, so it's kept as a separate `all_pruned`
    column instead of collapsing into `status` -- see analysis/topology_lite.py's
    trap_rate for that signal).

S3.3 (heuristic as natural transformation) and S3.4 (product/monoidal
ablation) are NOT here: both need genuinely new work (a post-hoc "true
remaining cost" oracle, and new ablated heuristic variants + reruns,
respectively) beyond what a trace CSV already contains.
"""
from __future__ import annotations

import math


def transition_counts(rows: list[dict]) -> dict[tuple[str, str], int]:
    by_id = {r["node_id"]: r["status"] for r in rows}
    counts: dict[tuple[str, str], int] = {}
    for r in rows:
        pid = r["parent_id"]
        if pid is None or pid not in by_id:
            continue
        key = (by_id[pid], r["status"])
        counts[key] = counts.get(key, 0) + 1
    return counts


def transition_matrix(counts: dict[tuple[str, str], int]) -> tuple[list[str], list[list[float]]]:
    """Row-stochastic matrix over the statuses actually observed (labels are
    sorted, so two matrices are only directly comparable if they observed
    the same label set)."""
    labels = sorted({s for pair in counts for s in pair})
    idx = {s: i for i, s in enumerate(labels)}
    n = len(labels)
    mat = [[0.0] * n for _ in range(n)]
    for (a, b), c in counts.items():
        mat[idx[a]][idx[b]] += c
    for row in mat:
        total = sum(row)
        if total > 0:
            for j in range(n):
                row[j] /= total
    return labels, mat


def kl_divergence(p: list[float], q: list[float], eps: float = 1e-12) -> float:
    """KL(p || q) over one matched row pair (each should already be a
    probability distribution, i.e. one row of a transition_matrix)."""
    total = 0.0
    for pi, qi in zip(p, q):
        if pi <= 0:
            continue
        total += pi * math.log((pi + eps) / (qi + eps))
    return total


def eigen_spectrum(mat: list[list[float]]) -> list[complex]:
    """Eigenvalue spectrum of the transition matrix -- mixing-rate /
    stationary-distribution comparison target (S3.2)."""
    import numpy as np
    if not mat:
        return []
    return sorted(np.linalg.eigvals(np.array(mat)), key=lambda v: -abs(v))
