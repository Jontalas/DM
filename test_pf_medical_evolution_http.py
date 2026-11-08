import copy
import io
import json
import secrets
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch
import server
import pf_recovery
import pf_rest
from firebase_store import FirestoreStore,Unavailable
import test_pf_night_rest_http as transport
from test_character_builder import choices


class MedicalEvolutionHTTPTests(unittest.TestCase):
    setUpClass=classmethod(transport.NightRestHTTPTests.setUpClass.__func__)
    tearDownClass=classmethod(transport.NightRestHTTPTests.tearDownClass.__func__)
    setUp=transport.NightRestHTTPTests.setUp
    request=transport.NightRestHTTPTests.request
    state=transport.NightRestHTTPTests.state
    action=transport.NightRestHTTPTests.action

    def prepare_proof_copy(self):
        self.action('create_character',choices=choices());exported=self.request('/api/export',{})
        patient=exported['state']['characters'][0];patient['hp']=-5;exported['state']['board']['combatSerial']=1
        pf_recovery.record_stabilization(patient,assisted=True,round_number=1,initiative=patient['id'],order=[patient['id']],epoch=1)
        pf_recovery.apply_hour(patient,1);pf_rest.apply_night_healing(patient,elapsed_seconds=28800)
        self.action('import',campaign=exported);return patient['id']

    def test_copy_cold_client_and_manual_correction_keep_distinct_medical_causes(self):
        with patch.object(server,'ai_reply',side_effect=AssertionError('Medical audit called provider')):
            actor=self.prepare_proof_copy();self.assertEqual(self.state()['state']['characters'][0]['hp'],-4)
            self.action('manual',character=actor,hpDelta=1,reason='Corrección explícita',resolution='Ajustar PG sin certificar curación')
            before=self.state();patient=before['state']['characters'][0];self.assertEqual(patient['hp'],-3);self.assertNotIn('recoveryCare',patient)
            self.assertEqual(patient['recoveryState']['change']['kind'],'manual-hp-correction')
            self.assertEqual(patient['recoveryState']['previous']['recovery']['change']['kind'],'natural-night-rest')
            previous=server.STORE
            if isinstance(previous,FirestoreStore):server.STORE=FirestoreStore.from_environment();server.STORE.prefix=previous.prefix
            try:
                self.assertEqual(self.state(),before);exported=self.request('/api/export',{});self.action('import',campaign=exported)
                self.assertEqual(self.state()['state']['characters'],before['state']['characters'])
                baseline=self.state();forged=copy.deepcopy(exported);forged['state']['characters'][0]['recoveryState']['conscious']=True
                with self.assertRaises(urllib.error.HTTPError) as error:self.action('import',campaign=forged)
                self.assertEqual(error.exception.code,400);error.exception.close();self.assertEqual(self.state(),baseline)
            finally:server.STORE=previous

    def test_provider_receives_summary_and_cold_failed_commit_replays_original_full_proof(self):
        self.prepare_proof_copy();before=self.state()
        body={'id':secrets.token_hex(12),'version':before['version'],'type':'talk','kind':'ooc','text':'Reviso el estado registrado.','director':True,'captureContract':'pf-director-action-1'}
        raw=json.dumps({'stop_reason':'end_turn','content':[{'type':'text','text':json.dumps({'narration':'El estado registrado conserva las heridas.','proposals':[]})}]}).encode()
        original_open=urllib.request.urlopen;sent=[]
        def dispatch(request,*args,**kwargs):
            if getattr(request,'full_url','').startswith('https://api.anthropic.com/'):
                sent.append(json.loads(request.data));return io.BytesIO(raw)
            return original_open(request,*args,**kwargs)
        with patch.dict('os.environ',{'ANTHROPIC_API_KEY':'fixture-never-sent'}),patch.object(server,'search',return_value=[]),patch('urllib.request.urlopen',side_effect=dispatch):
            with patch.object(server.STORE,'commit',side_effect=Unavailable('Interrupted medical response')):
                with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/action',body)
                self.assertEqual(error.exception.code,503);error.exception.close()
        self.assertEqual(self.state(),before);self.assertEqual(len(sent),1)
        projected=json.loads(sent[0]['messages'][0]['content'])['state']['characters'][0]['recoveryState']
        self.assertEqual(projected,{'format':'cronicas-pf-medical-context-1','hours':1,'conscious':False})
        previous=server.STORE
        if isinstance(previous,FirestoreStore):server.STORE=FirestoreStore.from_environment();server.STORE.prefix=previous.prefix
        try:
            with patch.object(server,'search',return_value=[]),patch.object(server,'ai_reply',side_effect=AssertionError('Medical context repeated provider')):
                self.request('/api/action',body);after=self.state();self.assertTrue(self.request('/api/action',body)['duplicate']);self.assertEqual(self.state(),after)
            self.assertEqual(after['state']['characters'],before['state']['characters'])
            self.assertEqual(len([m for m in after['state']['messages'] if m.get('speaker')=='Director · Claude Haiku']),1)
        finally:server.STORE=previous
