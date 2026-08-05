Both CLIs accept multiple instances in one call — no batch script needed, just shell globbing:

# Sokoban: every eligible map in the suite, with trace on
PYTHONPATH=src uv run python -m sokoban.cli src/sokoban/maps/*.txt src/sokoban/maps/*/*.txt \
  --out results/results.csv --trace --trace-dir results/traces

Given the earlier "pilot, not full suite" scope we agreed on for --trace (millions of rows per instance, capped at 100k each but still 155× that adds up fast), I'd pick a handful spanning the crate-count range rather than all 155 — e.g. one map from base*.txt (small), a few from sokoban-info/, one from generated/. src/sokoban/maps/EXCLUDED.md and the file layout give you the size spread if you want to pick deliberately rather than by hand.

Downloading real proteins of varying sizes

Two standard, stable sources, both FASTA-native:

- UniProt (https://www.uniprot.org/) — search, filter by the "Length" facet in the sidebar to get a specific size range, download selected entries as FASTA. Best general-purpose source.
- RCSB PDB (https://www.rcsb.org/) — Advanced Search has a sequence-length filter too; each structure page has a "Download Files → FASTA Sequence" link. Slightly more relevant here since these are proteins with solved 3D structures, closer in spirit to what a lattice folding model is approximating.

One practical thing worth knowing before you download: the HP-lattice B&B is exponential and short chains already get expensive — the earlier 20-mer stress test didn't finish within a 5M-eval budget. So "varying sizes" for this project probably means roughly 10–25 residues, not full-length proteins (which run 100s–1000s of residues) — filter for short peptides/fragments, not whole proteins, or you'll mostly generate cutoff rows.

Once downloaded, no manual conversion step needed — I just wired utils.convert_to_hp() (the code already in this repo, previously only used by the old Metropolis engine) into bnb_cli.py:

uv run python src/protein-fold/bnb_cli.py --fasta downloaded.fasta \
  --out results/results.csv --trace --trace-dir results/traces

It auto-detects whether each sequence is already HP or standard 20-aa, converts if needed, uses the FASTA header as the instance name, and skips (with a warning, not a crash) any sequence containing a code convert_to_hp doesn't recognize (ambiguous codes like X/B/Z/U — real downloads sometimes have these).


# Reliable path: paste in a list of PDB IDs (e.g. from RCSB's own "Download IDs" basket button)
uv run python scripts/download_pdb_fasta.py --ids-file my_ids.txt --out data/pdb.fasta

# Search path: RCSB full-text search, size-filtered locally after download
uv run python scripts/download_pdb_fasta.py --query "lysozyme" \
  --min-len 10 --max-len 25 --max-entries 20 --out data/pdb.fasta

Then feed straight into the B&B solver — bnb_cli.py's --fasta flag from earlier reads this exact file:

uv run python src/protein-fold/bnb_cli.py --fasta data/pdb.fasta --out results/results.csv

How it avoids rate-limiting, concretely, not just in name:
- Fewer requests, not just slower ones — uses RCSB's batch endpoint (/fasta/entry/{id1},{id2},...}), so 50 IDs cost one HTTP request, not 50.
- Paced — --delay (default 1s) between batches, not between individual entries.
- Backs off automatically on 429/5xx — urllib3.Retry with exponential backoff and Retry-After header respect, rather than a naive retry loop.
- Identifies itself — sends a real User-Agent, standard API courtesy.

One honesty note, since I said I'd flag this rather than paper over it: I'm confident about the batch FASTA endpoint (www.rcsb.org/fasta/entry/...) and the search API's base shape — both verified live above, working exactly as designed. The one thing I was less certain of going in was the exact JSON field names in the search response (result_set/identifier), which is why --ids-file exists as the always-reliable fallback with a clear error message pointing to it if --query ever stops matching (RCSB does evolve their schema over time). Both paths are now verified working today, but if --query breaks in the future, that's the escape hatch.

All well-mixed H/P compositions — none degenerate. Here's a curated set, verified live and previewed through the actual conversion:

Recommended set

┌────────────────┬───────┬────────┬─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│    Protein     │ PDB   │ Length │                                                               Why                                                               │
│                │  ID   │        │                                                                                                                                 │
├────────────────┼───────┼────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Trp-cage       │ 1L2Y  │ 20     │ The canonical "smallest fast-folding protein" benchmark in computational biology — designed specifically to be minimal and      │
│                │       │        │ tractable. Ideal fit for this project.                                                                                          │
├────────────────┼───────┼────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Insulin A      │ 4INS  │ 21     │ Real, famous, and both chains come from one download.                                                                           │
│ chain          │       │        │                                                                                                                                 │
├────────────────┼───────┼────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Insulin B      │ 4INS  │ 30     │ Same entry, second chain — free size variety.                                                                                   │
│ chain          │       │        │                                                                                                                                 │
├────────────────┼───────┼────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Villin         │ 1VII  │ 36     │ Another classic small fast-folder benchmark, next size class up.                                                                │
│ headpiece      │       │        │                                                                                                                                 │
├────────────────┼───────┼────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Crambin        │ 1CRN  │ 46     │ Extremely famous small protein (first ultra-high-res crystal structure) — already verified earlier. Good stress-test size.      │
└────────────────┴───────┴────────┴─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

That spread (20/21/30/36/46) gives you a real scaling curve. Fair warning based on what we saw last time: the 20-mer synthetic sequence already hit the eval-budget cutoff at 5M evals, so expect Villin and Crambin to come back cutoff, not solved — that's not a failure, it's the actual data point (search-cost-vs-chain-length is exactly what you want to characterize).

Commands

printf "1L2Y\n4INS\n1VII\n1CRN\n" > data/pdb_ids.txt

uv run python scripts/download_pdb_fasta.py --ids-file data/pdb_ids.txt --out data/pdb.fasta

uv run python src/protein-fold/bnb_cli.py --fasta data/pdb.fasta \
  --out results/results.csv --eval-budget 5000000 \
  --trace --trace-dir results/traces

If you want more variety without hand-picking IDs, the --query path works too, e.g. --query "designed miniprotein" --min-len 15 --max-len 40 --max-entries 10 — but given the small set above already spans the useful size range and I've hand-verified each one, I'd start with this list rather than a broader unverified search.

scripts/generate_hp_sequences.py

uv run python scripts/generate_hp_sequences.py --min-len 3 --max-len 20 --out data/synthetic_hp.fasta

uv run python src/protein-fold/bnb_cli.py --fasta data/synthetic_hp.fasta \
  --out results/results.csv --eval-budget 2000000 --trace --trace-dir results/traces

Key flags:
- --seed 42 (default) — deterministic, verified byte-for-byte identical across two runs with the same seed, and different for a different seed.
- --min-len/--max-len — inclusive size range; min-len floors at 3 (the solver's own validity floor).
- --per-length N — how many random draws per length (default 1). Use this if you want statistical spread at each size rather than one sample per length.
- --p-h — probability a residue is H (default 0.5). Real proteins run roughly 40–50% hydrophobic, so 0.5 is a reasonable default; push it toward 0.3 or 0.7 if you specifically want sparse-contact or dense-contact instances.
- Output is FASTA, so it goes straight into bnb_cli.py --fasta unchanged — no conversion step, since these are already H/P.

Ran it end-to-end for lengths 3–12 (2 per length, seed 42): all 20 solved to proven optimality, and nodes_expanded climbs cleanly from single digits at length 3 up to ~30k at length 12 — a real scaling curve, exactly what you'd want for the cross-domain size-vs-cost comparison against Sokoban's crate-count axis.

One thing worth deciding before you generate a big batch: --per-length sequences at the same length are randomly independent, so they won't isolate "does difficulty depend on composition, not just length" as cleanly as varying --p-h deliberately would. If that distinction matters for your analysis, generate a few separate files at different --p-h values rather than relying on per-length randomness alone.