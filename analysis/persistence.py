"""S1.2: persistent homology on the expanded-node point cloud
(docs/equivalence/cross-domain-analysis-design.md). Feature-embedding variant
(a) only: points = (g, h, f) per visited node, Euclidean distance,
Vietoris-Rips filtration via `ripser`. The intrinsic-embedding variant (b)
(shortest-path distance in the induced subgraph) is not implemented -- the
doc itself scopes it as a follow-up on a handful of instances, after (a).

Subsampled for tractability: Vietoris-Rips on a full ~100k-node trace isn't
practical (the distance matrix alone is O(n^2)).
"""
from __future__ import annotations

import random


def point_cloud(rows: list[dict], max_points: int = 1500, seed: int = 0) -> list[tuple[float, float, float]]:
    """(g, h, f) per expanded/goal node -- pruned rows are rejected
    candidates, not visited states, so excluded here. Randomly subsampled
    (fixed seed) to `max_points` if larger."""
    points = [
        (r["g"], r["h"], r["f"]) for r in rows
        if r["status"] in ("expanded", "goal") and r["g"] is not None and r["h"] is not None and r["f"] is not None
    ]
    if len(points) <= max_points:
        return points
    rng = random.Random(seed)
    return rng.sample(points, max_points)


def persistence_diagrams(points: list[tuple[float, float, float]]):
    """Vietoris-Rips persistence diagrams via ripser: returns [beta0_diagram,
    beta1_diagram], each an (n_bars, 2) array of (birth, death) pairs."""
    import numpy as np
    from ripser import ripser

    X = np.array(points, dtype=float)
    result = ripser(X, maxdim=1)
    return result["dgms"]


def diagram_summary(dgms) -> dict[int, dict]:
    """Per-dimension scalar summary of one instance's persistence diagram:
    bar count and total persistence (sum of lifetimes). Population-level
    statistical TDA (docs/DECISIONS.md) works off these scalars rather than
    full persistence landscapes/images -- simpler and more robust to get
    right under time pressure than getting an unfamiliar landscape API
    correct (this project has been burned twice already by trusting a
    library API without checking it first), while still supporting a real
    two-sample test (e.g. Mann-Whitney U) across a population of instances,
    which is the actual point.

    The one infinite-death bar every H0 diagram has (the component that
    never merges away) is capped at the diagram's own max *finite* value
    before summing -- the standard convention for giving an infinite bar a
    finite, comparable contribution."""
    import numpy as np

    finite_vals = [v for dgm in dgms for pair in dgm for v in pair if np.isfinite(v)]
    cap = max(finite_vals) if finite_vals else 0.0

    summary = {}
    for dim, dgm in enumerate(dgms):
        lifetimes = [(cap if not np.isfinite(death) else death) - birth for birth, death in dgm]
        summary[dim] = {"n_bars": len(dgm), "total_persistence": float(sum(lifetimes))}
    return summary
