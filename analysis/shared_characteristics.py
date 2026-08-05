"""S2: shared-characteristic analysis without reduction
(docs/equivalence/cross-domain-analysis-design.md). Reads only
n_legal_successors, n_pruned, f, status, timestamp_order from the S0 trace
(analysis/trace_io.py) -- no additional instrumentation beyond what's
already logged.

S2.3 (local vs. global move classification) is NOT here: it needs a
`move_type` column that neither solver logs (flagged when the trace feature
was built -- src/protein-fold/bnb.py's module docstring explains why the
doc's HP move vocabulary, corner-flip/pivot, doesn't match the B&B
chain-growth engine that was actually built).
"""
from __future__ import annotations

from collections.abc import Iterable


def branching_factors(rows: Iterable[dict]) -> list[int]:
    """S2.1: n_legal_successors per node that generated any (leaf/pruned
    rows log None -- not applicable, not zero)."""
    return [r["n_legal_successors"] for r in rows if r["n_legal_successors"] is not None]


def feasibility_ratios(rows: Iterable[dict]) -> list[float]:
    """S2.2: n_legal_successors / (n_legal_successors + n_pruned) per node."""
    out: list[float] = []
    for r in rows:
        legal, pruned = r["n_legal_successors"], r["n_pruned"]
        if legal is None or pruned is None:
            continue
        denom = legal + pruned
        if denom > 0:
            out.append(legal / denom)
    return out


def plateau_run_lengths(rows: list[dict], epsilon: float = 1e-9) -> list[int]:
    """S2.4: lengths of maximal runs, along the expansion sequence (status in
    {expanded, goal}, ordered by timestamp_order), where f is non-decreasing
    beyond epsilon. A run of length 1 means f dropped immediately after that
    node -- not a plateau."""
    seq = sorted(
        (r for r in rows if r["status"] in ("expanded", "goal") and r["f"] is not None),
        key=lambda r: r["timestamp_order"],
    )
    if not seq:
        return []
    lengths: list[int] = []
    run = 1
    for prev, cur in zip(seq, seq[1:]):
        if cur["f"] >= prev["f"] - epsilon:
            run += 1
        else:
            lengths.append(run)
            run = 1
    lengths.append(run)
    return lengths
