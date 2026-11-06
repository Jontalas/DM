import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import Mock,patch
import game_randomness
import engine


class GameRandomnessTests(unittest.TestCase):
    def test_physical_values_do_not_consume_source_and_tie_is_bounded(self):
        source=Mock(return_value=7)
        with game_randomness.using_random_source(source):
            self.assertEqual(engine.dice([20],[12]),[12]);source.assert_not_called()
            self.assertEqual(engine.dice([20,20]),[7,7]);self.assertEqual(game_randomness.initiative_tie(),6)
        self.assertEqual(source.call_args.args,(65536,))

    def test_scope_restores_after_nested_execution_and_exception(self):
        with patch('game_randomness.secrets.randbelow',return_value=2):
            self.assertEqual(engine.dice([20]),[3])
            with game_randomness.using_random_source(lambda sides:4):
                self.assertEqual(engine.dice([20]),[4])
                with self.assertRaises(RuntimeError):
                    with game_randomness.using_random_source(lambda sides:5):
                        self.assertEqual(engine.dice([20]),[5]);raise RuntimeError('Interrupted')
                self.assertEqual(engine.dice([20]),[4])
            self.assertEqual(engine.dice([20]),[3])

    def test_simultaneous_threads_never_share_players_streams(self):
        barrier=Barrier(2)
        def worker(value):
            with game_randomness.using_random_source(lambda sides:value):
                barrier.wait();return engine.dice([20]*8)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(worker,[3,17]))
        self.assertEqual(results,[[3]*8,[17]*8])

    def test_invalid_values_fail_before_they_can_be_used_as_dice(self):
        for value in (True,0,21,'5'):
            with game_randomness.using_random_source(lambda sides:value):
                with self.assertRaises(ValueError):engine.dice([20])
