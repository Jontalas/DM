"""Private Pathfinder capture recovery; never calls a real provider."""
import base64
import copy
import io
import json
import os
import unittest
from unittest.mock import patch
import claude_dm
import legacy_director_attempt as legacy
import rule_preparation_attempt as attempts
from engine import initial_state
from firebase_store import Conflict
from test_support import TestStore


class LegacyDirectorAttemptTests(unittest.TestCase):
    def setUp(self):
        self.state=initial_state({});self.store=TestStore()
        self.prepared=legacy.prepare(self.state,'Una declaración.',[])

    def envelope(self,reply=None,stop='end_turn'):
        return json.dumps({'stop_reason':stop,'content':[{'type':'text','text':json.dumps(reply or {'narration':'Respuesta de prueba.','proposals':[]})}]}).encode()

    def run_capture(self,raw):
        def convert(current,response_observer=None):
            return claude_dm.ai_reply(self.state,'Una declaración.',[],response_observer=response_observer)
        with patch.dict(os.environ,{'ANTHROPIC_API_KEY':'fixture-never-sent'}),patch.object(claude_dm.urllib.request,'urlopen',return_value=io.BytesIO(raw)) as transport:
            result=attempts.run(self.store,'room','ana',self.prepared,converter=convert,restore=legacy.restore)
            self.assertEqual(transport.call_count,1)
            return result

    def test_cold_capture_restores_without_configuration_or_provider(self):
        expected=self.run_capture(self.envelope())
        cold=TestStore();cold.preparations=copy.deepcopy(self.store.preparations)
        with patch.dict(os.environ,{'ANTHROPIC_API_KEY':''}):
            result=attempts.run(cold,'room','ana',self.prepared,converter=lambda *a,**k:self.fail('Recovery called provider'),restore=legacy.restore)
        self.assertEqual(result,expected)

    def test_invalid_and_truncated_responses_remain_captured(self):
        for raw in (b'invalid-json',self.envelope(stop='max_tokens')):
            with self.subTest(raw=raw):
                self.store=TestStore()
                with self.assertRaises(ValueError):self.run_capture(raw)
                saved=next(iter(self.store.preparations.values()))
                payload=attempts.unpack(saved['responseData'])
                self.assertEqual(base64.b64decode(payload['value']),raw)
                with self.assertRaises(ValueError):attempts.run(self.store,'room','ana',self.prepared,converter=lambda *a,**k:self.fail('Invalid capture retried provider'),restore=legacy.restore)

    def test_style_prompt_update_recovers_original_capture_without_another_inference(self):
        import director_prompt
        expected=self.run_capture(self.envelope())
        cold=TestStore();cold.preparations=copy.deepcopy(self.store.preparations)
        with patch.object(director_prompt,'BASE',director_prompt.BASE+'\nNueva pauta de estilo.'):
            updated=legacy.prepare(self.state,'Una declaración.',[])
        self.assertEqual(updated['sha256'],self.prepared['sha256'])
        self.assertNotEqual(updated['promptSha256'],self.prepared['promptSha256'])
        with patch.dict(os.environ,{'ANTHROPIC_API_KEY':''}):
            restored=attempts.run(cold,'room','ana',updated,
                converter=lambda *a,**k:self.fail('Style update repeated a paid call'),restore=legacy.restore)
        self.assertEqual(restored,expected)

    def test_unknown_outcome_never_authorizes_another_call(self):
        with patch.dict(os.environ,{'ANTHROPIC_API_KEY':'fixture-never-sent'}):
            with self.assertRaises(OSError):attempts.run(self.store,'room','ana',self.prepared,converter=lambda *a,**k:(_ for _ in ()).throw(OSError('Interrupted')),restore=legacy.restore)
            with self.assertRaises(Conflict):attempts.run(self.store,'room','ana',self.prepared,converter=lambda *a,**k:self.fail('Unknown outcome retried'),restore=legacy.restore)

    def test_report_and_contract_validation_do_not_mutate_context(self):
        before=copy.deepcopy(self.prepared)
        payload={'kind':'report','value':{'narration':'Texto.','proposals':[]},'latencyMs':0}
        self.assertEqual(legacy.restore(self.prepared,payload,legacy.SCHEME)['narration'],'Texto.')
        payload['value']['narration']='El salÃ³n conserva su texto original.'
        self.assertEqual(legacy.restore(self.prepared,payload,legacy.SCHEME)['narration'],payload['value']['narration'])
        self.assertEqual(self.prepared,before)
        with self.assertRaises(ValueError):legacy.restore(self.prepared,payload,'director-v1')

    def test_repeated_public_turns_have_distinct_keys_after_history_window_fills(self):
        event={'kind':'dialogue','speaker':'Aria','text':'La misma pregunta.'}
        state=copy.deepcopy(self.state);state['messages']=[copy.deepcopy(event) for _ in range(30)]
        first=legacy.prepare(state,'La misma pregunta.',[])
        state['messages'].append(copy.deepcopy(event));second=legacy.prepare(state,'La misma pregunta.',[])
        self.assertEqual(first['request']['context'],second['request']['context'])
        self.assertNotEqual(first['sha256'],second['sha256'])
        state['messages'].insert(0,{'kind':'private','visibility':'private','speaker':'Aria','text':'PRIVATE-NOT-SENT'})
        private=legacy.prepare(state,'La misma pregunta.',[])
        self.assertEqual(private['sha256'],second['sha256'])
