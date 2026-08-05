"""Generate random HP sequences with a fixed seed, spanning a size range --
a synthetic complement to real downloaded proteins
(scripts/download_pdb_fasta.py) for exercising the B&B solver
(src/protein-fold/bnb.py) at small, controlled sizes below what's practical
to source as real PDB entries (structures below ~20 residues rarely have a
stable-enough fold to crystallize/NMR, so they're uncommon and unreliable to
pick by ID).

Deterministic: the same --seed always produces the same file byte-for-byte,
regardless of call order -- uses a dedicated random.Random(seed) instance,
never the global `random` module state.

Run:
  uv run python scripts/generate_hp_sequences.py --min-len 3 --max-len 20 --out data/synthetic_hp.fasta
  uv run python scripts/generate_hp_sequences.py --min-len 3 --max-len 15 --per-length 5 --p-h 0.5 --seed 7 --out data/synthetic_hp.fasta
"""
from __future__ import annotations

import argparse
import random
from pathlib import Path


def generate_sequences(
    min_len: int, max_len: int, per_length: int, p_h: float, seed: int,
) -> list[tuple[str, str]]:
    """[(label, sequence), ...], fully determined by
    (min_len, max_len, per_length, p_h, seed)."""
    if min_len < 3:
        raise ValueError("min_len must be >= 3 (validation.is_valid_sequence's floor)")
    if min_len > max_len:
        raise ValueError("min_len must be <= max_len")

    rng = random.Random(seed)
    records: list[tuple[str, str]] = []
    for length in range(min_len, max_len + 1):
        for i in range(per_length):
            seq = "".join("H" if rng.random() < p_h else "P" for _ in range(length))
            records.append((f"hp_len{length}_{i}_seed{seed}", seq))
    return records


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--min-len", type=int, default=3, help="smallest chain length (residues), >=3")
    parser.add_argument("--max-len", type=int, default=20, help="largest chain length (residues)")
    parser.add_argument("--per-length", type=int, default=1, help="random sequences to generate per length")
    parser.add_argument("--p-h", type=float, default=0.5, help="probability a residue is H (default 0.5)")
    parser.add_argument("--seed", type=int, default=42, help="RNG seed -- fixed, for reproducibility")
    parser.add_argument("--out", type=Path, default=Path("data/synthetic_hp.fasta"), help="output FASTA path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    records = generate_sequences(args.min_len, args.max_len, args.per_length, args.p_h, args.seed)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w") as f:
        for label, seq in records:
            f.write(f">{label}\n{seq}\n")

    print(f"wrote {len(records)} sequences (lengths {args.min_len}-{args.max_len}, "
          f"{args.per_length}/length, p_h={args.p_h}, seed={args.seed}) to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
