"""S1.5: Forman-Ricci graph curvature on the induced expansion subgraph
(docs/equivalence/cross-domain-analysis-design.md). Forman variant (no
optimal-transport solver needed, per the doc's own prototype-scope note) via
`GraphRicciCurvature`, directly on the reconstructed graph (parent_id
edges) -- no embedding, no `f` needed, curvature comes purely from local
neighborhood overlap.

Full traces are too large to lay out/read as a plotted graph (up to ~100k
nodes) -- `sample_connected_subgraph` takes a small prefix by expansion
order (naturally connected: a child's parent is always expanded before or
around when the child is, so a timestamp_order-contiguous window rarely
straddles a broken link -- any it does miss are pulled in explicitly).
"""
from __future__ import annotations


def sample_connected_subgraph(rows: list[dict], max_nodes: int = 300) -> list[dict]:
    """First `max_nodes` visited (expanded/goal) rows by timestamp_order,
    plus the FULL ancestor chain of each (walked recursively, not just one
    hop) -- both solvers append a node's own trace row only after its
    successor loop finishes, so `timestamp_order` is not guaranteed
    monotonic along `parent_id` edges (a deep descendant can get a *smaller*
    timestamp than its own ancestor, whose row is still pending). A
    single-hop parent pull-in isn't enough to guarantee connectivity given
    that; walking the whole chain is."""
    visited = sorted(
        (r for r in rows if r["status"] in ("expanded", "goal")),
        key=lambda r: r["timestamp_order"],
    )
    sample = visited[:max_nodes]
    by_id = {r["node_id"]: r for r in rows}
    ids = {r["node_id"] for r in sample}
    extra = []
    for r in sample:
        pid = r["parent_id"]
        while pid is not None and pid not in ids:
            parent_row = by_id.get(pid)
            if parent_row is None:
                break
            extra.append(parent_row)
            ids.add(pid)
            pid = parent_row["parent_id"]
    return sample + extra


def build_graph(rows: list[dict]):
    """networkx.Graph from parent_id edges (undirected -- Ricci curvature
    packages conventionally operate on undirected graphs)."""
    import networkx as nx

    g = nx.Graph()
    for r in rows:
        g.add_node(r["node_id"])
    ids = set(g.nodes)
    for r in rows:
        if r["parent_id"] is not None and r["parent_id"] in ids:
            g.add_edge(r["parent_id"], r["node_id"])
    return g


def forman_curvature(g) -> dict[tuple, float]:
    """Per-edge Forman-Ricci curvature: {(u, v): curvature}, keyed by the
    ORIGINAL node ids in `g`. `GraphRicciCurvature`'s debug-logging path does
    unconditional `%d`-style string formatting on the node id (eager
    `%`-formatting in the call argument, so it runs regardless of logging
    level) -- a bug in that library, not here, but it crashes outright on our
    string node ids. Worked around by relabeling to plain integers before
    calling it and mapping the result back to the original ids."""
    import networkx as nx
    from GraphRicciCurvature.FormanRicci import FormanRicci

    relabeled = nx.convert_node_labels_to_integers(g, label_attribute="orig_id")
    orig_id = nx.get_node_attributes(relabeled, "orig_id")

    frc = FormanRicci(relabeled)
    frc.compute_ricci_curvature()
    return {(orig_id[u], orig_id[v]): d["formanCurvature"] for u, v, d in frc.G.edges(data=True)}


def mean_curvature(rows: list[dict], max_nodes: int = 300) -> float | None:
    """Population-level S1.5 summary: one instance's mean edge curvature over
    its `sample_connected_subgraph`. The instance-level plot (kept as-is,
    docs/DECISIONS.md) shows *where* an individual search tree is bottlenecked
    vs. well-connected; pooling this scalar across many instances is what
    shows whether that's a systematic domain property or one instance's
    idiosyncrasy."""
    sub = sample_connected_subgraph(rows, max_nodes=max_nodes)
    g = build_graph(sub)
    if g.number_of_edges() == 0:
        return None
    curv = forman_curvature(g)
    return sum(curv.values()) / len(curv)
