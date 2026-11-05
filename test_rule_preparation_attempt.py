import copy
import base64
import io
import json
import os
import unittest
from unittest.mock import patch
import rule_preparation_attempt as attempts
import rule_pack_authoring as authoring
import rule_pack_campaign as campaign
from firebase_store import Conflict,Unavailable,FirestoreStore
from test_support import TestStore,make_store
import test_rule_pack_authoring as fixture


def output(prepared):
    return json.dumps({'stop_reason':'end_turn','content':[{'type':'text','text':json.dumps(fixture.reply(prepared))}],
        'usage':{'input_tokens':123,'output_tokens':456}}).encode()


class PreparationAttemptTests(unittest.TestCase):
    def setUp(self):
        self.store=TestStore();self.prepared=authoring.prepare_input(fixture.request());self.cid='private-room';self.actor='ana'
        self.environment=patch.dict(os.environ,{'ANTHROPIC_API_KEY':'fake-never-persisted'});self.environment.start();self.addCleanup(self.environment.stop)

    def cold(self):
        other=TestStore();other.preparations=copy.deepcopy(self.store.preparations);return other

    def test_captured_response_recovers_after_restart_without_key_or_inference(self):
        with patch.object(authoring.urllib.request,'urlopen',return_value=io.BytesIO(output(self.prepared))) as provider:
            first=attempts.run(self.store,self.cid,self.actor,self.prepared);self.assertEqual(provider.call_count,1)
        self.assertNotIn('fake-never-persisted',repr(self.store.preparations))
        with patch.dict(os.environ,{'ANTHROPIC_API_KEY':''}),patch.object(authoring,'propose',side_effect=AssertionError('Recovery called provider')):
            self.assertEqual(attempts.run(self.cold(),self.cid,self.actor,self.prepared),first)

    def test_failed_response_write_reuses_memory_and_then_becomes_durable(self):
        with patch.object(self.store,'save_rule_preparation_response',side_effect=OSError('Firestore unavailable')),patch.object(authoring.urllib.request,'urlopen',return_value=io.BytesIO(output(self.prepared))) as provider:
            with self.assertRaises(Unavailable):attempts.run(self.store,self.cid,self.actor,self.prepared)
            self.assertEqual(provider.call_count,1)
        with patch.object(authoring,'propose',side_effect=AssertionError('Saved memory called provider')):
            recovered=attempts.run(self.store,self.cid,self.actor,self.prepared)
            self.assertEqual(attempts.run(self.cold(),self.cid,self.actor,self.prepared),recovered)

    def test_unknown_outcome_and_invalid_capture_never_repeat_a_call(self):
        with patch.object(authoring.urllib.request,'urlopen',side_effect=OSError('Interrupted transport')):
            with self.assertRaises(ValueError):attempts.run(self.store,self.cid,self.actor,self.prepared)
        with patch.object(authoring,'propose',side_effect=AssertionError('Unknown outcome retried')):
            with self.assertRaises(Conflict):attempts.run(self.cold(),self.cid,self.actor,self.prepared)
        other=authoring.prepare_input(fixture.request()|{'scope':'Different explicit scope'})
        with patch.object(authoring.urllib.request,'urlopen',return_value=io.BytesIO(b'invalid JSON')):
            with self.assertRaises(ValueError):attempts.run(self.store,self.cid,self.actor,other)
        with patch.object(authoring,'propose',side_effect=AssertionError('Invalid capture retried')):
            with self.assertRaises(ValueError):attempts.run(self.cold(),self.cid,self.actor,other)

    def test_missing_configuration_does_not_reserve_a_paid_attempt(self):
        with patch.dict(os.environ,{'ANTHROPIC_API_KEY':''}),patch.object(authoring,'propose',side_effect=AssertionError('Missing key called provider')):
            with self.assertRaises(ValueError):attempts.run(self.store,self.cid,self.actor,self.prepared)
        self.assertFalse(self.store.preparations)

    def test_actor_binding_and_memory_are_scoped_and_bounded(self):
        for n in range(12):attempts._remember(self.store,'room-'+str(n),'key',{'kind':'report','value':{},'latencyMs':0})
        self.assertLessEqual(len(attempts._memory[self.store]),8)
        self.assertIsNone(attempts._recall(self.store,'unrelated-room','key'))
        identifier=attempts.key(self.actor,self.prepared['sha256'])
        self.store.begin_rule_preparation(self.cid,identifier,self.actor,self.prepared)
        self.store.preparations[self.cid,identifier]['actor']='foreign'
        with patch.object(authoring,'propose',side_effect=AssertionError('Foreign attempt called provider')):
            with self.assertRaises(Conflict):attempts.run(self.store,self.cid,self.actor,self.prepared)


@unittest.skipUnless(os.environ.get('FIRESTORE_EMULATOR_HOST'),'Requiere emulador oficial; no usa Firebase real')
class PreparationAttemptEmulatorTests(unittest.TestCase):
    def setUp(self):
        self.store=make_store();self.token=self.store.create('Preparation recovery',campaign.initial_state({}),'Ana')
        self.me=self.store.identity(self.token);self.cid=self.me['campaign'];self.prepared=authoring.prepare_input(fixture.request())

    def test_reservation_is_unique_and_captured_response_survives_cold_client(self):
        actor=self.me['id'];identifier=attempts.key(actor,self.prepared['sha256'])
        first=self.store.begin_rule_preparation(self.cid,identifier,actor,self.prepared)
        second=self.store.begin_rule_preparation(self.cid,identifier,actor,self.prepared)
        self.assertTrue(first['fresh']);self.assertFalse(second['fresh'])
        payload={'kind':'raw','value':base64.b64encode(output(self.prepared)).decode(),'latencyMs':99}
        self.store.save_rule_preparation_response(self.cid,identifier,actor,self.prepared['sha256'],attempts.pack(payload))
        cold=FirestoreStore.from_environment();cold.prefix=self.store.prefix
        with patch.dict(os.environ,{'ANTHROPIC_API_KEY':''}),patch.object(authoring,'propose',side_effect=AssertionError('Cold client called provider')):
            record=attempts.run(cold,self.cid,actor,self.prepared)
        self.assertEqual(record['report']['usage']['latencyMs'],99)
        self.assertEqual(record['report']['usage']['outputTokens'],456)
        with self.assertRaises(ValueError):cold.begin_rule_preparation(self.cid,identifier,'other-actor',self.prepared)
