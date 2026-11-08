import copy
import io
import json
import secrets
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch
import server
from firebase_store import FirestoreStore,Unavailable
import test_pf_night_rest_http as transport
from test_character_builder import choices


class PreparedFactsHTTPTests(unittest.TestCase):
    setUpClass=classmethod(transport.NightRestHTTPTests.setUpClass.__func__)
    tearDownClass=classmethod(transport.NightRestHTTPTests.tearDownClass.__func__)
    request=transport.NightRestHTTPTests.request
    state=transport.NightRestHTTPTests.state
    action=transport.NightRestHTTPTests.action

    def setUp(self):
        configured=patch.dict('os.environ',{'ANTHROPIC_API_KEY':'fixture-never-sent'});configured.start();self.addCleanup(configured.stop)
        transport.NightRestHTTPTests.setUp(self)

    def test_sdk_gets_permission_in_dialogue_and_failed_commit_restores_without_hint_or_second_call(self):
        self.action('create_character',choices=choices());actor=self.state()['state']['characters'][0]['id']
        self.action('enter_pf_encounter',encounter='patio-del-peaje',encounterVersion='1.13.0',character=actor)
        self.action('choose_pf_encounter',choice='parley');before=self.state()
        body={'id':secrets.token_hex(12),'version':before['version'],'type':'talk','kind':'dialogue','character':actor,'text':'¿Me dejas revisar el registro?','director':True,'captureContract':'pf-director-action-1'}
        raw=json.dumps({'stop_reason':'end_turn','content':[{'type':'text','text':json.dumps({'narration':'La guardiana confirma que puedes consultar los papeles públicos. Tú decides si lo haces.','proposals':[]})}]}).encode()
        original_open=urllib.request.urlopen;sent=[]
        def dispatch(request,*args,**kwargs):
            if getattr(request,'full_url','').startswith('https://api.anthropic.com/'):
                sent.append(json.loads(request.data));return io.BytesIO(raw)
            return original_open(request,*args,**kwargs)
        with patch.object(server,'search',return_value=[]),patch('urllib.request.urlopen',side_effect=dispatch),patch.object(server.STORE,'commit',side_effect=Unavailable('Interrupted dialogue')):
            with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/action',body)
            self.assertEqual(error.exception.code,503);error.exception.close()
        self.assertEqual(len(sent),1);context=json.loads(sent[0]['messages'][0]['content'])
        self.assertEqual(context['preparedSceneFacts']['publicDocumentsAccess'],'already-permitted')
        self.assertNotIn('preparedDecision',sent[0]['output_config']['format']['schema']['properties'])
        self.assertIn('No niegues ni dejes pendiente ese permiso',sent[0]['system']);self.assertEqual(self.state(),before)
        previous=server.STORE
        if isinstance(previous,FirestoreStore):server.STORE=FirestoreStore.from_environment();server.STORE.prefix=previous.prefix
        try:
            with patch.object(server,'search',return_value=[]),patch('director_prepared_facts.public_facts',return_value=None),patch.object(server,'ai_reply',side_effect=AssertionError('Recovered dialogue repeated provider')):
                self.request('/api/action',body);after=self.state();self.assertTrue(self.request('/api/action',body)['duplicate']);self.assertEqual(self.state(),after)
            for key in ('characters','board','pending','location','worldTime','pfEncounter'):self.assertEqual(after['state'][key],before['state'][key])
            self.assertEqual(len([m for m in after['state']['messages'] if m.get('kind')=='director']),1)
            self.action('import',campaign=self.request('/api/export',{}));self.assertEqual(self.state()['state']['messages'],after['state']['messages'])
        finally:server.STORE=previous
