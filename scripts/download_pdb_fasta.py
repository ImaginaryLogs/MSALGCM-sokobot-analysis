"""Download FASTA sequences from RCSB PDB to build an HP-lattice benchmark
corpus (the HP-side analog of src/sokoban/maps/'s map suite -- see
docs/DECISIONS.md).

Rate-limit-safe by construction, not by luck:
  - Batches many PDB IDs into few HTTP requests via RCSB's comma-joined
    `/fasta/entry/{id1},{id2},...` endpoint (default 50 IDs/request) instead
    of one request per entry.
  - Sleeps `--delay` seconds between batches (default 1.0s).
  - Retries on 429/5xx with exponential backoff and honors `Retry-After`
    (urllib3 Retry, not a hand-rolled loop), instead of hammering the server
    on transient failures.
  - Sends an identifying User-Agent (basic API etiquette).

Two ways to choose which entries to fetch:
  --ids-file PATH   Reliable, always works. One PDB ID per line -- e.g. the
                     .txt file RCSB's website exports from the search-results
                     "basket" (Download IDs button). Use this if --query stops
                     matching anything (RCSB's search schema can change).
  --query TEXT      Convenience: RCSB full-text search (what the rcsb.org
                     search box does), paginated automatically.

Length filtering (`--min-len`/`--max-len`) always happens locally, after
download, by measuring the sequence actually received -- not via a
server-side numeric-range query attribute. That keeps this script correct
even if RCSB's query schema for entity length shifts.

If the batch FASTA endpoint below ever stops working, the documented
per-entry fallback is `https://files.rcsb.org/download/{ID}.fasta`.

Run:
  uv run python scripts/download_pdb_fasta.py --ids-file my_ids.txt --out data/pdb.fasta
  uv run python scripts/download_pdb_fasta.py --query "hemoglobin" \
      --min-len 10 --max-len 25 --max-entries 20 --out data/pdb.fasta
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

SEARCH_URL = "https://search.rcsb.org/rcsbsearch/v2/query"
FASTA_URL = "https://www.rcsb.org/fasta/entry/{ids}"
USER_AGENT = "MSALGCM-sokobot-analysis-fetch/0.1 (research script; HP-lattice benchmark corpus)"


def _session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    retry = Retry(
        total=5,
        backoff_factor=1.5,  # 1.5s, 3s, 6s, 12s, 24s
        status_forcelist=[429, 500, 502, 503, 504],
        respect_retry_after_header=True,
        allowed_methods=frozenset(["GET", "POST"]),
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    return session


def search_ids(session: requests.Session, query: str, max_entries: int, page_size: int = 100) -> list[str]:
    """RCSB full-text search, paginated. Returns entry IDs (e.g. "4HHB").
    Over-fetches relative to max_entries since local length-filtering may
    discard some hits -- caller should pass a generous max_entries."""
    ids: list[str] = []
    start = 0
    while len(ids) < max_entries:
        body = {
            "query": {"type": "terminal", "service": "full_text", "parameters": {"value": query}},
            "return_type": "entry",
            "request_options": {"paginate": {"start": start, "rows": page_size}},
        }
        resp = session.post(SEARCH_URL, json=body, timeout=30)
        if resp.status_code == 204:
            break  # RCSB returns 204 (no body) for a zero-result query
        resp.raise_for_status()
        hits = resp.json().get("result_set", [])
        if not hits:
            break
        ids.extend(h["identifier"] for h in hits)
        start += page_size
    return ids[:max_entries]


def fetch_fasta_batches(session: requests.Session, ids: list[str], batch_size: int, delay: float) -> str:
    """One HTTP request per `batch_size` IDs (RCSB's comma-joined endpoint),
    paced by `delay` between batches -- this is the actual rate-limit
    avoidance: fewer, spaced-out requests instead of one per ID."""
    chunks: list[str] = []
    for i in range(0, len(ids), batch_size):
        batch = ids[i : i + batch_size]
        url = FASTA_URL.format(ids=",".join(batch))
        resp = session.get(url, timeout=60)
        if resp.status_code == 404:
            print(f"  [warn] batch starting {batch[0]}: no FASTA found, skipping", file=sys.stderr)
            continue
        resp.raise_for_status()
        chunks.append(resp.text)
        print(f"  fetched {min(i + batch_size, len(ids))}/{len(ids)} IDs")
        if i + batch_size < len(ids):
            time.sleep(delay)
    return "\n".join(chunks)


def parse_fasta(text: str) -> list[tuple[str, str]]:
    records: list[tuple[str, str]] = []
    header: str | None = None
    chunks: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(">"):
            if header is not None:
                records.append((header, "".join(chunks)))
            header, chunks = line[1:], []
        else:
            chunks.append(line)
    if header is not None:
        records.append((header, "".join(chunks)))
    return records


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ids-file", type=Path, default=None, help="text file, one PDB ID per line")
    parser.add_argument("--query", default=None, help="RCSB full-text search term (fallback: --ids-file)")
    parser.add_argument("--max-entries", type=int, default=50,
                         help="cap on entries kept after length filtering")
    parser.add_argument("--min-len", type=int, default=None, help="keep sequences >= this length (residues)")
    parser.add_argument("--max-len", type=int, default=None, help="keep sequences <= this length (residues)")
    parser.add_argument("--batch-size", type=int, default=50,
                         help="PDB IDs per HTTP request to the batch FASTA endpoint")
    parser.add_argument("--delay", type=float, default=1.0, help="seconds between batch requests")
    parser.add_argument("--out", type=Path, default=Path("data/pdb.fasta"), help="output FASTA path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.ids_file and not args.query:
        print("need --ids-file or --query", file=sys.stderr)
        return 1

    session = _session()

    if args.ids_file:
        ids = [line.strip() for line in args.ids_file.read_text().splitlines() if line.strip()]
    else:
        print(f"searching RCSB for {args.query!r}...")
        try:
            # over-fetch: local length filtering below will discard some hits
            ids = search_ids(session, args.query, max_entries=args.max_entries * 3)
        except (requests.RequestException, KeyError, ValueError) as exc:
            print(f"search failed ({exc}); use --ids-file instead "
                  f"(export one from rcsb.org's search-results basket)", file=sys.stderr)
            return 1
        if not ids:
            print("no hits -- try a different --query, or use --ids-file instead", file=sys.stderr)
            return 1
        print(f"found {len(ids)} candidate entries")

    print(f"downloading {len(ids)} entries in batches of {args.batch_size} "
          f"({args.delay}s between batches)...")
    raw = fetch_fasta_batches(session, ids, args.batch_size, args.delay)
    records = parse_fasta(raw)
    print(f"parsed {len(records)} FASTA records (an entry can have multiple chains)")

    if args.min_len is not None or args.max_len is not None:
        lo = args.min_len if args.min_len is not None else 0
        hi = args.max_len if args.max_len is not None else float("inf")
        records = [(h, s) for h, s in records if lo <= len(s) <= hi]

    records = records[: args.max_entries]
    if not records:
        print("nothing left after length filtering -- widen --min-len/--max-len", file=sys.stderr)
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w") as f:
        for header, seq in records:
            f.write(f">{header}\n{seq}\n")

    lengths = sorted(len(s) for _, s in records)
    print(f"wrote {len(records)} sequences to {args.out} (lengths {lengths[0]}-{lengths[-1]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
