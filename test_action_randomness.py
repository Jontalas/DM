"""Durable stream binding and unbiased, bounded dice recovery."""
import unittest
from unittest.mock import patch
from action_randomness import ActionRandomness
from test_support import TestStore
from firebase_store import Conflict


class ActionRandomnessTests(unittest.TestCase):
    def test_replay_stream_and_independent_actions(self):
        store=TestStore()
        def stream(action):return ActionRandomness(store,'campaign',action,'actor','fingerprint',3)
        first=stream('one');values=[first(sides) for sides in [6,20,100,6]]
        second=stream('one');self.assertEqual(values,[second(sides) for sides in [6,20,100,6]])
        self.assertNotEqual(first.seed,stream('two').store.action_random_seed('campaign','two','actor','fingerprint',3))
        with self.assertRaises(Conflict):ActionRandomness(store,'campaign','one','other','fingerprint',3)(6)

    def test_rejection_sampling_and_lazy_reservation(self):
        store=TestStore();draw=ActionRandomness(store,'campaign','one','actor','fingerprint',3)
        self.assertIsNone(draw.seed)
        with patch('action_randomness.hmac.digest',side_effect=[b'\xff'*32,(3).to_bytes(32,'big')]) as digest:
            self.assertEqual(draw(6),4);self.assertEqual(digest.call_count,2)
        for sides in [True,1,1000001,'6']:
            with self.assertRaises(ValueError):draw(sides)
