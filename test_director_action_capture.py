import copy
import os
import unittest
from unittest.mock import patch
import legacy_director_attempt as legacy
import rule_preparation_attempt as attempts
from engine import initial_state
from firebase_store import Conflict
from test_support import TestStore


class DirectorActionCaptureTests(unittest.TestCase):
    def setUp(self):
        self.state=initial_state({});self.store=TestStore()
        self.identity={'action':'submission-one','actor':'ana','fingerprint':'a'*64,'version':3}
        self.environment=patch.dict(os.environ,{'ANTHROPIC_API_KEY':'fixture-never-sent'});self.environment.start();self.addCleanup(self.environment.stop)

    def prepare(self,refs=None,state=None,identity=None):
        return legacy.prepare(self.state if state is None else state,'Observo el patio.',refs or [],action_identity=self.identity if identity is None else identity)

    def capture(self,prepared):
        return attempts.run(self.store,'room','ana',prepared,converter=lambda *a,**k:{'narration':'El patio conserva su aspecto.','proposals':[]},restore=legacy.restore)

    def cold(self):
        store=TestStore();store.preparations=copy.deepcopy(self.store.preparations);return store

    def test_changed_search_restores_original_input_without_provider_after_restart(self):
        first=self.prepare([{'book':'reglas','page':180,'text':'Original'}]);expected=self.capture(first)
        changed=self.prepare([{'book':'reglas','page':185,'text':'Reindexed'}])
        self.assertEqual(first['sha256'],changed['sha256'])
        seen=[]
        def restore(prepared,payload,scheme):seen.append(prepared['request']);return legacy.restore(prepared,payload,scheme)
        with patch.dict(os.environ,{'ANTHROPIC_API_KEY':''}):
            result=attempts.run(self.cold(),'room','ana',changed,converter=lambda *a,**k:self.fail('Repeated provider'),restore=restore)
        self.assertEqual(result,expected);self.assertEqual(seen,[first['captureRequest']])

    def test_unknown_result_with_changed_search_still_blocks_another_call(self):
        first=self.prepare()
        with self.assertRaises(OSError):attempts.run(self.store,'room','ana',first,converter=lambda *a,**k:(_ for _ in ()).throw(OSError('Interrupted')),restore=legacy.restore)
        changed=self.prepare([{'book':'reglas','page':180,'text':'New result'}])
        with self.assertRaises(Conflict):attempts.run(self.cold(),'room','ana',changed,converter=lambda *a,**k:self.fail('Uncertain provider repeated'),restore=legacy.restore)

    def test_reused_id_cannot_change_submission_version_or_game_facts(self):
        first=self.prepare();self.capture(first)
        for field,value in [('fingerprint','b'*64),('version',4)]:
            identity={**self.identity,field:value};changed=self.prepare(identity=identity)
            self.assertEqual(first['sha256'],changed['sha256'])
            with self.subTest(field=field),self.assertRaises(Conflict):attempts.run(self.cold(),'room','ana',changed,converter=lambda *a,**k:self.fail('Changed submission called provider'),restore=legacy.restore)
        state=copy.deepcopy(self.state);state['goal']='Different facts'
        with self.assertRaises(Conflict):attempts.run(self.cold(),'room','ana',self.prepare(state=state),converter=lambda *a,**k:self.fail('Changed facts called provider'),restore=legacy.restore)

    def test_next_action_has_distinct_key_and_legacy_mode_remains_unchanged(self):
        self.assertNotEqual(self.prepare()['sha256'],self.prepare(identity={**self.identity,'action':'submission-two'})['sha256'])
        old=legacy.prepare(self.state,'Observo el patio.',[])
        self.assertNotIn('actionIdentity',old['request']);self.assertNotEqual(old['sha256'],self.prepare()['sha256'])
        self.assertNotEqual(old['sha256'],legacy.prepare(self.state,'Observo el patio.',[{'book':'reglas','page':180,'text':'New'}])['sha256'])

    def test_invalid_identity_is_rejected_before_reservation(self):
        for identity in ({},[],{**self.identity,'version':True},{**self.identity,'action':''},{**self.identity,'fingerprint':'bad'}):
            with self.subTest(identity=identity),self.assertRaises(ValueError):self.prepare(identity=identity)
        self.assertEqual(self.store.preparations,{})
