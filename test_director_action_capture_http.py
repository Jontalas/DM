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
import test_character_builder as builder


class DirectorActionCaptureHTTPTests(unittest.TestCase):
    setUpClass=classmethod(transport.NightRestHTTPTests.setUpClass.__func__)
    tearDownClass=classmethod(transport.NightRestHTTPTests.tearDownClass.__func__)
    request=transport.NightRestHTTPTests.request
    state=transport.NightRestHTTPTests.state
    action=transport.NightRestHTTPTests.action

    def setUp(self):
        configured=patch.dict('os.environ',{'ANTHROPIC_API_KEY':'fixture-never-sent'});configured.start();self.addCleanup(configured.stop)
        transport.NightRestHTTPTests.setUp(self)

    def test_original_capture_survives_reindexed_sources_and_changed_submission_is_rejected(self):
        self.action('create_character',choices=builder.choices());before=self.state()
        body={'id':secrets.token_hex(12),'version':before['version'],'type':'talk','kind':'action','text':'Observo el patio.','character':before['state']['characters'][0]['id'],'director':True,'captureContract':'pf-director-action-1'}
        raw=json.dumps({'stop_reason':'end_turn','content':[{'type':'text','text':json.dumps({'narration':'El patio conserva su aspecto.','proposals':[]})}]}).encode()
        original_open=urllib.request.urlopen;sent=[]
        def dispatch(request,*args,**kwargs):
            if getattr(request,'full_url','').startswith('https://api.anthropic.com/'):
                sent.append(json.loads(request.data));return io.BytesIO(raw)
            return original_open(request,*args,**kwargs)
        with patch.object(server,'search',return_value=[{'book':'reglas','page':180,'text':'Original reference'}]),patch('urllib.request.urlopen',side_effect=dispatch):
            with patch.object(server.STORE,'commit',side_effect=Unavailable('Interrupted commit')):
                with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/action',body)
            self.assertEqual(error.exception.code,503);error.exception.close()
        self.assertEqual(len(sent),1);self.assertEqual(self.state(),before)
        previous=server.STORE
        if isinstance(previous,FirestoreStore):server.STORE=FirestoreStore.from_environment();server.STORE.prefix=previous.prefix
        try:
            with patch.object(server,'search',return_value=[{'book':'reglas','page':185,'text':'Changed index'}]),patch.object(server,'ai_reply',side_effect=AssertionError('Repeated inference')):
                with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/action',{**body,'text':'Una decisión diferente.'})
                self.assertEqual(error.exception.code,409);error.exception.close();self.assertEqual(self.state(),before)
                self.request('/api/action',body);after=self.state()
                self.assertEqual(after['version'],before['version']+1)
                self.assertEqual(len([m for m in after['state']['messages'] if m.get('speaker')=='Director · Claude Haiku']),1)
                self.assertTrue(self.request('/api/action',body)['duplicate']);self.assertEqual(self.state(),after)
            self.action('import',campaign=self.request('/api/export',{}));self.assertEqual(self.state()['state']['messages'],after['state']['messages'])
        finally:server.STORE=previous

    def test_unknown_capture_contract_is_rejected_without_provider(self):
        before=self.state()
        for action in ({'type':'talk','text':'Observo','captureContract':'unknown'},{'type':'scene','location':'Patio','captureContract':'pf-director-action-1'}):
            with patch.object(server,'ai_reply',side_effect=AssertionError('Invalid contract reached provider')):
                with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/action',{'id':secrets.token_hex(12),'version':before['version'],**action})
                self.assertEqual(error.exception.code,400);error.exception.close()
            self.assertEqual(self.state(),before)
