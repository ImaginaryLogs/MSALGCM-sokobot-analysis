"""TDD fixtures for the B&B chain-growth solver (ADR 0002). Optimality is
cross-checked two ways, mirroring Sokoban's D2 small-instance oracle pattern
(src/sokoban/tests/test_sokoban.py): a hand-verified fixture, and an
un-pruned brute-force enumerator for tiny sequences.

Run: py -m unittest discover -s src/protein-fold/tests -t src/protein-fold
"""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import bnb  # noqa: E402
import protein  # noqa: E402
import validation  # noqa: E402

_OFFSETS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def _brute_force_best(sequence: str) -> int:
    """Exhaustive, unpruned max-H-H-contact search. No symmetry break either
    -- an independent oracle for tiny sequences, used only in tests."""
    n = len(sequence)
    fold = [(0, 0), (1, 0)]
    pos_index = {(0, 0): 0, (1, 0): 1}
    best = 0

    def contacts_formed(pos, idx):
        if sequence[idx] != "H":
            return 0
        x, y = pos
        count = 0
        for dx, dy in _OFFSETS:
            j = pos_index.get((x + dx, y + dy))
            if j is not None and j != idx - 1 and j != idx + 1 and sequence[j] == "H":
                count += 1
        return count

    def dfs(idx, g):
        nonlocal best
        if idx == n - 1:
            best = max(best, g)
            return
        prev = fold[idx]
        for dx, dy in _OFFSETS:
            cand = (prev[0] + dx, prev[1] + dy)
            if cand in pos_index:
                continue
            fold.append(cand)
            pos_index[cand] = idx + 1
            dfs(idx + 1, g + contacts_formed(cand, idx + 1))
            del pos_index[cand]
            fold.pop()

    dfs(1, 0)
    return best


def _energy_via_protein(fold, sequence) -> float:
    """Independent cross-check via the existing Protein/energy model
    (src/protein-fold/protein.py), reused rather than re-derived."""
    fake_config = SimpleNamespace(sequence=sequence, use_struct=True, fold=fold)
    return protein.Protein(fake_config).get_energy()


class TestBnBSolver(unittest.TestCase):
    def test_hhhh_optimal_is_one_contact(self):
        result = bnb.solve("HHHH")
        self.assertEqual(result.solved, "solved")
        self.assertEqual(result.solution_quality, 1)
        self.assertEqual(len(result.fold), 4)

    def test_all_polar_has_zero_contacts(self):
        result = bnb.solve("PPPP")
        self.assertEqual(result.solved, "solved")
        self.assertEqual(result.solution_quality, 0)

    def test_fold_is_valid_saw(self):
        result = bnb.solve("HPHPPHHPH")
        self.assertTrue(validation.is_valid_fold(result.fold))
        self.assertEqual(len(result.fold), len("HPHPPHHPH"))

    def test_energy_matches_protein_model(self):
        sequence = "HPHPPHHPH"
        result = bnb.solve(sequence)
        energy = _energy_via_protein(result.fold, sequence)
        self.assertEqual(energy, -result.solution_quality)

    def test_matches_brute_force_oracle(self):
        # includes "HPHPPH" (true optimum 2) and "HHHH" (true optimum 1),
        # both of which an earlier, unsound bound formula undercounted --
        # see bnb.py's module docstring
        sequences = [
            "HHH", "HPH", "HHPH", "HHHHH", "HPHPH", "HHPPH", "PHPHPHP",
            "HPHPPH", "HPHPPHH", "HPHPPHHP", "HPHPPHHPH", "HPHPPHHPHP",
        ]
        for sequence in sequences:
            for bound in ("tight", "weak"):
                with self.subTest(sequence=sequence, bound=bound):
                    expected = _brute_force_best(sequence)
                    result = bnb.solve(sequence, bound=bound)
                    self.assertEqual(result.solved, "solved")
                    self.assertEqual(result.solution_quality, expected)

    def test_matches_brute_force_oracle_random(self):
        import random

        rng = random.Random(42)
        for _ in range(25):
            length = rng.randint(4, 10)
            sequence = "".join(rng.choice("HP") for _ in range(length))
            for bound in ("tight", "weak"):
                with self.subTest(sequence=sequence, bound=bound):
                    expected = _brute_force_best(sequence)
                    result = bnb.solve(sequence, bound=bound)
                    self.assertEqual(result.solved, "solved")
                    self.assertEqual(result.solution_quality, expected)

    def test_connectivity_prune_matches_brute_force_oracle(self):
        # proof-of-concept domain-constraint prune (docs/DECISIONS.md) --
        # same soundness bar as the bound: must never change the found optimum
        sequences = [
            "HHH", "HPH", "HHPH", "HHHHH", "HPHPH", "HHPPH", "PHPHPHP",
            "HPHPPH", "HPHPPHH", "HPHPPHHP", "HPHPPHHPH", "HPHPPHHPHP",
        ]
        for sequence in sequences:
            for bound in ("tight", "weak"):
                with self.subTest(sequence=sequence, bound=bound):
                    expected = _brute_force_best(sequence)
                    result = bnb.solve(sequence, bound=bound, connectivity_prune=True)
                    self.assertEqual(result.solved, "solved")
                    self.assertEqual(result.solution_quality, expected)

    def test_connectivity_prune_fires_on_realistic_sequences(self):
        # sanity check that the feature isn't vacuously never triggering --
        # a soundness test that never exercises the new code path proves nothing
        rng_sequences = [
            "HPHHPPHHHH", "PHPPPPPHHHPP", "HHHPHHPHPH", "PHPPPHPPPHHP", "HPHHPPPHH",
        ]
        total_fired = sum(
            bnb.solve(seq, connectivity_prune=True, eval_budget=2_000_000, timeout_s=30).connectivity_pruned
            for seq in rng_sequences
        )
        self.assertGreater(total_fired, 0)

    def test_reachable_free_capacity_detects_sealed_pocket(self):
        # tip boxed in on 3 sides, with the 4th leading to a single free cell
        # that is itself fully walled off -- reachable region size is exactly 1
        tip = (0, 0)
        pos_index = {
            (1, 0): 0, (0, 1): 1, (-1, 0): 2,   # 3 of tip's 4 neighbors occupied
            (1, -1): 3, (0, -2): 4, (-1, -1): 5,  # wall off the pocket at (0,-1)
        }
        self.assertEqual(bnb.reachable_free_capacity(tip, pos_index, cutoff=5), 1)
        # a chain needing >1 more monomer can never fit through a 1-cell pocket
        self.assertLess(bnb.reachable_free_capacity(tip, pos_index, cutoff=3), 3)

    def test_reachable_free_capacity_open_area_not_flagged(self):
        tip = (0, 0)
        pos_index = {(1, 0): 0}  # only the backbone predecessor occupied
        # plenty of open space in every other direction -- never a false deadlock
        self.assertGreaterEqual(bnb.reachable_free_capacity(tip, pos_index, cutoff=20), 20)

    def test_weak_bound_is_admissible_but_costs_more(self):
        # bound_weak(n) >= bound_tight(n) always (module docstring proof) --
        # same proven optimum, but exploring strictly more (or equal) nodes,
        # not fewer. If weak ever wins, the "weaker" framing is just wrong.
        for sequence in ("HPHPPHHPHPPHPHHPPHPH", "HHPPHHPHPPHHPHHPPHH"):
            with self.subTest(sequence=sequence):
                tight = bnb.solve(sequence, bound="tight", eval_budget=2_000_000, timeout_s=30)
                weak = bnb.solve(sequence, bound="weak", eval_budget=2_000_000, timeout_s=30)
                if tight.solved == "solved" and weak.solved == "solved":
                    self.assertEqual(tight.solution_quality, weak.solution_quality)
                self.assertGreaterEqual(weak.nodes_expanded, tight.nodes_expanded)

    def test_rejects_invalid_bound_name(self):
        with self.assertRaises(ValueError):
            bnb.solve("HPHPPHHPH", bound="hungarian")

    def test_eval_budget_triggers_cutoff(self):
        result = bnb.solve("HPHPPHHPHPPHPHHPPHPH", eval_budget=10)
        self.assertEqual(result.solved, "cutoff")
        self.assertEqual(result.cutoff_reason, "budget")
        self.assertLessEqual(result.candidates_scored, 10 + 4)  # loop exits mid-batch

    def test_timeout_triggers_cutoff(self):
        result = bnb.solve("HPHPPHHPHPPHPHHPPHPH", timeout_s=0.0)
        self.assertEqual(result.solved, "cutoff")
        self.assertEqual(result.cutoff_reason, "clock")

    def test_rejects_invalid_sequence(self):
        with self.assertRaises(ValueError):
            bnb.solve("HX")


class TraceTests(unittest.TestCase):
    def test_off_by_default(self):
        result = bnb.solve("HPHPPHHPH")
        self.assertIsNone(result.trace_rows)

    def test_produces_one_row_per_visited_node_plus_pruned(self):
        result = bnb.solve("HPHPPHHPH", trace=True)
        self.assertIsNotNone(result.trace_rows)
        visited = [r for r in result.trace_rows if r["status"] in ("expanded", "goal")]
        self.assertEqual(len(visited), result.nodes_expanded)
        statuses = {row["status"] for row in result.trace_rows}
        self.assertLessEqual(statuses, {"expanded", "goal", "pruned"})
        self.assertGreaterEqual(sum(1 for r in result.trace_rows if r["status"] == "goal"), 1)
        self.assertGreaterEqual(sum(1 for r in result.trace_rows if r["status"] == "pruned"), 1)
        # incumbent improves at least once on the way to the proven optimum
        self.assertGreaterEqual(sum(1 for r in result.trace_rows if r["is_new_best"]), 1)

    def test_node_cap_enforced_without_truncating_the_search(self):
        result = bnb.solve(
            "HPHPPHHPHPPHPHHPPHPH", trace=True, trace_node_cap=200,
            eval_budget=5_000_000, timeout_s=10,
        )
        self.assertLessEqual(len(result.trace_rows), 200)
        self.assertGreater(result.nodes_expanded, 200)  # search wasn't shortened by the cap

    def test_all_pruned_flag_only_on_expanded_rows(self):
        result = bnb.solve("HPHPPHHPH", trace=True)
        expanded_rows = [r for r in result.trace_rows if r["status"] == "expanded"]
        goal_rows = [r for r in result.trace_rows if r["status"] == "goal"]
        self.assertTrue(all(r["all_pruned"] in (True, False) for r in expanded_rows))
        self.assertTrue(all(r["all_pruned"] is None for r in goal_rows))


if __name__ == "__main__":
    unittest.main()
