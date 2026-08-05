"""S1.1 (disconnectivity) and S1.3 (trap rate). S1.2/1.4/1.5 live in
analysis/persistence.py, analysis/mapper.py, analysis/curvature.py
respectively (docs/DECISIONS.md #14). Both pieces here use only the induced
subgraph (parent_id edges) and f already in the S0 trace
(docs/equivalence/cross-domain-analysis-design.md).
"""
from __future__ import annotations

from collections.abc import Iterable


class _UnionFind:
    def __init__(self) -> None:
        self._parent: dict[str, str] = {}

    def find(self, x: str) -> str:
        self._parent.setdefault(x, x)
        while self._parent[x] != x:
            self._parent[x] = self._parent[self._parent[x]]
            x = self._parent[x]
        return x

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self._parent[ra] = rb


def disconnectivity_curve(rows: list[dict], n_thresholds: int = 20) -> list[tuple[float, int]]:
    """S1.1, lite version: sweep tau over f, union-find connected components
    of the sublevel-set subgraph {n : f(n) <= tau} using parent_id edges.
    Returns (tau, n_components) -- a component-count *drop* as tau rises
    marks a merge event. This is the curve, not the full branching-tree
    diagram (which needs the merge history, i.e. which components merged and
    when -- not built here)."""
    by_id = {r["node_id"]: r for r in rows}
    f_values = sorted({r["f"] for r in rows if r["f"] is not None})
    if not f_values:
        return []
    lo, hi = f_values[0], f_values[-1]
    step = (hi - lo) / max(n_thresholds - 1, 1) if hi > lo else 1.0
    thresholds = [lo + i * step for i in range(n_thresholds)] if hi > lo else [lo]

    curve: list[tuple[float, int]] = []
    for tau in thresholds:
        uf = _UnionFind()
        included = {nid for nid, r in by_id.items() if r["f"] is not None and r["f"] <= tau}
        for nid in included:
            pid = by_id[nid]["parent_id"]
            if pid in included:
                uf.union(nid, pid)
        n_components = len({uf.find(nid) for nid in included}) if included else 0
        curve.append((tau, n_components))
    return curve


def disconnectivity_curve_normalized(rows: list[dict], n_thresholds: int = 20) -> list[tuple[float, float]]:
    """S1.1, population variant: `disconnectivity_curve` with both axes
    normalized to [0, 1] -- tau by this instance's own f-range, n_components
    by the count at tau=min (the largest it'll ever be) -- so curves from
    differently-scaled instances become directly comparable (same start
    point (0,1), same shape question: how fast does it collapse toward one
    component?) instead of living on incomparable absolute scales."""
    curve = disconnectivity_curve(rows, n_thresholds)
    # disconnectivity_curve degenerates to a single point when f is constant
    # across the whole trace (e.g. a very short/trivial instance) -- not
    # enough to normalize or to compare shape against a real curve, and
    # population callers need every accepted curve to have the same length
    # (n_thresholds) to aggregate elementwise, so exclude it here rather
    # than returning a length-1 "curve".
    if len(curve) < 2:
        return []
    taus = [t for t, _ in curve]
    lo, hi = taus[0], taus[-1]
    span = hi - lo if hi > lo else 1.0
    n0 = curve[0][1] if curve[0][1] > 0 else 1
    return [((t - lo) / span, n / n0) for t, n in curve]


def trap_rate(rows: Iterable[dict]) -> dict:
    """S1.3 lite: rate of index-0 critical cells (`all_pruned`), already
    computed live in the S0 trace (docs/DECISIONS.md #11) -- this just
    aggregates what's already there."""
    expanded = [r for r in rows if r["status"] == "expanded" and r["all_pruned"] is not None]
    if not expanded:
        return {"n_expanded": 0, "n_trap": 0, "rate": None}
    n_trap = sum(1 for r in expanded if r["all_pruned"])
    return {"n_expanded": len(expanded), "n_trap": n_trap, "rate": n_trap / len(expanded)}
