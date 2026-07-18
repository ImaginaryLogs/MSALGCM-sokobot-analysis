"""TDD fixtures for the Sokoban port (D7). Own solved/unsolvable maps -- NOT
Java solutions. Run: py -m unittest discover -s src/sokoban/tests -t src"""
import unittest
from pathlib import Path

from sokoban.deadlock import compute_dead_squares
from sokoban.emit import write_row
from sokoban.heuristic import hungarian, manhattan
from sokoban.loader import load_map
from sokoban.metrics import build_row
from sokoban.solver import solve
from sokoban.state import make_state
from sokoban.validator import ValidationError, assert_optimal, optimal_push_count, replay

FIXTURES = Path(__file__).parent / "fixtures"


class LoaderTests(unittest.TestCase):
    def test_parses_walls_goal_crate_player(self):
        board, crates, player = load_map(FIXTURES / "solved_2push.txt")
        self.assertEqual((board.width, board.height), (7, 4))
        self.assertEqual(board.goals, frozenset({(1, 1)}))
        self.assertEqual(crates, frozenset({(3, 1)}))
        self.assertEqual(player, (2, 1))

    def test_crate_goal_mismatch_raises(self):
        bad = FIXTURES / "_bad_mismatch.txt"
        bad.write_text("#####\n#@$.#\n#  .#\n#####\n")
        try:
            with self.assertRaises(Exception):
                load_map(bad)
        finally:
            bad.unlink()


class DeadlockTests(unittest.TestCase):
    def test_dead_squares_match_hand_computed_set(self):
        board, _crates, _player = load_map(FIXTURES / "deadzone_room.txt")
        dead = compute_dead_squares(board)
        self.assertEqual(dead, frozenset({(1, 3), (2, 3), (3, 1), (3, 2), (3, 3)}))


class SolverTests(unittest.TestCase):
    def test_solves_optimally_and_matches_oracle(self):
        board, crates, player = load_map(FIXTURES / "solved_2push.txt")
        start = make_state(board, crates, player)
        result = solve(board, start, w=1.0, eval_budget=10_000, timeout_s=5.0)
        self.assertEqual(result.solved, "solved")
        self.assertEqual(result.solution_quality, 2)
        assert_optimal(board, start, result.solution_quality)  # raises on mismatch

    def test_replay_confirms_solution(self):
        board, crates, player = load_map(FIXTURES / "solved_2push.txt")
        start = make_state(board, crates, player)
        result = solve(board, start, w=1.0, eval_budget=10_000, timeout_s=5.0)
        replay(board, start, result.push_sequence)  # raises on mismatch

    def test_replay_rejects_truncated_sequence(self):
        board, crates, player = load_map(FIXTURES / "solved_2push.txt")
        start = make_state(board, crates, player)
        result = solve(board, start, w=1.0, eval_budget=10_000, timeout_s=5.0)
        with self.assertRaises(ValidationError):
            replay(board, start, result.push_sequence[:1])  # one push short of goal

    def test_detects_unsolvable(self):
        board, crates, player = load_map(FIXTURES / "unsolvable_walled.txt")
        start = make_state(board, crates, player)
        result = solve(board, start, w=1.0, eval_budget=10_000, timeout_s=5.0)
        self.assertEqual(result.solved, "unsolvable")
        self.assertIsNone(optimal_push_count(board, start))

    def test_multi_crate_solves_optimally(self):
        # exercises crates-as-obstacles in reachable_region, player renormalization
        # after a push, and greedy-Manhattan admissibility under goal contention
        board, crates, player = load_map(FIXTURES / "two_crates.txt")
        start = make_state(board, crates, player)
        result = solve(board, start, w=1.0, eval_budget=100_000, timeout_s=10.0)
        self.assertEqual(result.solved, "solved")
        assert_optimal(board, start, result.solution_quality)  # raises on mismatch
        replay(board, start, result.push_sequence)  # raises on mismatch

    def test_weighted_search_still_yields_valid_solution(self):
        # w>1 trades optimality for speed (D8) -- must still be a legal solution
        board, crates, player = load_map(FIXTURES / "two_crates.txt")
        start = make_state(board, crates, player)
        result = solve(board, start, w=2.0, eval_budget=100_000, timeout_s=10.0)
        self.assertEqual(result.solved, "solved")
        replay(board, start, result.push_sequence)  # raises on mismatch

    def test_deadlock_prune_still_scores_candidates(self):
        # every successor from the start state pushes into a dead square (D5:
        # candidates_scored must count them, not silently drop them)
        board, crates, player = load_map(FIXTURES / "unsolvable_walled.txt")
        start = make_state(board, crates, player)
        result = solve(board, start, w=1.0, eval_budget=10_000, timeout_s=5.0)
        self.assertGreater(result.candidates_scored, 0)


class HungarianHeuristicTests(unittest.TestCase):
    def test_at_least_as_tight_as_manhattan(self):
        # Hungarian forbids two crates claiming the same goal, so it's never a
        # looser bound than per-crate nearest-goal (D2).
        board, crates, _player = load_map(FIXTURES / "two_crates.txt")
        self.assertGreaterEqual(hungarian(board, crates), manhattan(board, crates))

    def test_stays_admissible_never_exceeds_optimal(self):
        board, crates, player = load_map(FIXTURES / "two_crates.txt")
        start = make_state(board, crates, player)
        optimal = optimal_push_count(board, start)
        self.assertIsNotNone(optimal)
        self.assertLessEqual(hungarian(board, crates), optimal)

    def test_solves_optimally_same_as_manhattan(self):
        board, crates, player = load_map(FIXTURES / "two_crates.txt")
        start = make_state(board, crates, player)
        result = solve(board, start, w=1.0, heuristic=hungarian, eval_budget=100_000, timeout_s=10.0)
        self.assertEqual(result.solved, "solved")
        assert_optimal(board, start, result.solution_quality)  # raises on mismatch
        replay(board, start, result.push_sequence)  # raises on mismatch


class EmitTests(unittest.TestCase):
    def test_row_round_trips_through_csv(self):
        board, crates, player = load_map(FIXTURES / "solved_2push.txt")
        start = make_state(board, crates, player)
        result = solve(board, start, w=1.0, eval_budget=10_000, timeout_s=5.0)
        row = build_row(
            board=board, instance_id="solved_2push", crate_count=len(crates),
            result=result, weight_w=1.0, base_h="manhattan",
        )
        out_csv = FIXTURES / "_scratch_emit.csv"
        try:
            write_row(out_csv, row)
            content = out_csv.read_text()
            self.assertIn("solved_2push", content)
            self.assertIn("wastar", content)
        finally:
            out_csv.unlink()


if __name__ == "__main__":
    unittest.main()
