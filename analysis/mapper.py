"""S1.4: Mapper on the induced expansion subgraph
(docs/equivalence/cross-domain-analysis-design.md). Filter function = f;
cover range(f) with overlapping intervals; cluster nodes within each
preimage by GRAPH ADJACENCY (parent_id edges) rather than Euclidean
distance -- the doc calls for adjacency clustering specifically ("reuse the
induced subgraph here"), which isn't `kmapper`'s default Euclidean
clusterer, so this reuses the same union-find as S1.1's disconnectivity
curve (`analysis.topology_lite._UnionFind`) directly instead of fighting
kmapper's clustering assumptions.
"""
from __future__ import annotations

from analysis.topology_lite import _UnionFind


def mapper_graph(rows: list[dict], n_intervals: int = 15, overlap: float = 0.3):
    """Returns (nodes, edges): `nodes` is a list of {members, filter_mean,
    size} dicts (one per Mapper cluster); `edges` is a list of (i, j) index
    pairs between clusters sharing at least one underlying node."""
    visited = [r for r in rows if r["status"] in ("expanded", "goal") and r["f"] is not None]
    if not visited:
        return [], []
    by_id = {r["node_id"]: r for r in visited}
    f_values = [r["f"] for r in visited]
    lo, hi = min(f_values), max(f_values)
    if hi == lo:
        hi = lo + 1.0
    width = (hi - lo) / n_intervals
    step = width * (1 - overlap) if overlap < 1 else width

    intervals = []
    start = lo
    while start < hi:
        intervals.append((start, start + width))
        start += step

    clusters: list[set] = []
    for a, b in intervals:
        members = {r["node_id"] for r in visited if a <= r["f"] <= b}
        if not members:
            continue
        uf = _UnionFind()
        for nid in members:
            uf.find(nid)
        for nid in members:
            pid = by_id[nid]["parent_id"]
            if pid in members:
                uf.union(nid, pid)
        groups: dict[str, set] = {}
        for nid in members:
            groups.setdefault(uf.find(nid), set()).add(nid)
        clusters.extend(groups.values())

    nodes = [
        {"members": members, "filter_mean": sum(by_id[m]["f"] for m in members) / len(members), "size": len(members)}
        for members in clusters
    ]

    # edges: connect clusters sharing >=1 underlying node. Overlapping
    # intervals mean cluster counts (and total membership) scale with
    # n_intervals * instance size -- a naive all-pairs set-intersection scan
    # is O(n_clusters^2) and doesn't finish on a ~100k-node instance with
    # thousands of clusters. An inverted index (node_id -> cluster indices)
    # makes this O(total membership entries) instead.
    owners: dict[str, list[int]] = {}
    for i, cluster in enumerate(nodes):
        for m in cluster["members"]:
            owners.setdefault(m, []).append(i)
    edge_set: set[tuple[int, int]] = set()
    for cluster_ids in owners.values():
        for a in range(len(cluster_ids)):
            for b in range(a + 1, len(cluster_ids)):
                i, j = cluster_ids[a], cluster_ids[b]
                edge_set.add((i, j) if i < j else (j, i))
    return nodes, sorted(edge_set)


def fragmentation_ratio(rows: list[dict], n_intervals: int = 15, overlap: float = 0.3) -> float | None:
    """Population-level S1.4 summary: clusters per visited node. A single
    Mapper graph is only ever a picture of one instance (docs/DECISIONS.md
    #14's ~230x Sokoban-vs-HP gap was exactly this problem -- one pair of
    instances, chosen for plot legibility, not representativeness); this
    scalar is what actually generalizes across a population. `n_intervals`
    is fixed across every instance and both domains (not tuned per instance
    the way the single-instance plot's parameters were) so the ratio means
    the same thing everywhere it's computed."""
    nodes, _edges = mapper_graph(rows, n_intervals=n_intervals, overlap=overlap)
    n_visited = len({m for n in nodes for m in n["members"]})
    if n_visited == 0:
        return None
    return len(nodes) / n_visited
