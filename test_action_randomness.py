"""Durable stream binding and unbiased, bounded dice recovery."""
import unittest
from unittest.mock import patch
from action_randomness import ActionRandomness
from test_support import TestStore
from firebase_store import Conflict


class ActionRandomnessTests(unittest.TestCase):
    def test_explicit_pending_reservation_survives_new_http_identity_and_version(self):
        store=TestStore();reservation={'key':'pending:'+'a'*64,'fingerprint':'b'*64,'version':0}
        first=ActionRandomness(store,'campaign','http-one','actor','body-one',3,reservation=reservation)
        values=[first(sides) for sides in [6,20,6]]
        second=ActionRandomness(store,'campaign','http-two','actor','body-two',4,reservation=reservation)
        self.assertEqual(values,[second(sides) for sides in [6,20,6]])
        with self.assertRaises(Conflict):ActionRandomness(store,'campaign','http-three','actor','body-three',4,
            reservation=reservation|{'fingerprint':'c'*64})(6)
        self.assertNotIn(('campaign','http-one'),store.randomness)

    def test_pending_descriptor_is_explicit_and_bounded_before_drawing(self):
        store=TestStore();reservation={'key':'pending:'+'a'*64,'fingerprint':'b'*64,'version':0}
        for changed in [{'key':'other'},{'fingerprint':'invalid'},{'version':True},{'extra':1}]:
            with self.assertRaises(ValueError):ActionRandomness(store,'campaign','http','actor','body',3,reservation=reservation|changed)
        self.assertFalse(hasattr(store,'randomness'))

    def test_no_dice_check_does_not_create_a_seed_but_rejects_changed_existing_reservation(self):
        store=TestStore();reservation={'key':'pending:'+'a'*64,'fingerprint':'b'*64,'version':0}
        first=ActionRandomness(store,'campaign','http-one','actor','body-one',3,reservation=reservation)
        first.verify_if_unused();self.assertFalse(hasattr(store,'randomness'))
        first(6)
        changed=ActionRandomness(store,'campaign','http-two','actor','body-two',4,reservation=reservation|{'fingerprint':'c'*64})
        with self.assertRaises(Conflict):changed.verify_if_unused()

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
