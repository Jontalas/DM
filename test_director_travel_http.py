import copy
import json
import secrets
import unittest
import urllib.error
from unittest.mock import patch
import server
from firebase_store import FirestoreStore,Unavailable
import test_pf_night_rest_http as night_http
from test_adventure import reply,memory


class DirectorTravelHTTPTests(unittest.TestCase):
    setUpClass=classmethod(night_http.NightRestHTTPTests.setUpClass.__func__)
    tearDownClass=classmethod(night_http.NightRestHTTPTests.tearDownClass.__func__)
    request=night_http.NightRestHTTPTests.request
    state=night_http.NightRestHTTPTests.state
    action=night_http.NightRestHTTPTests.action
    prepare=night_http.NightRestHTTPTests.prepare

    def setUp(self):
        configured=patch.dict('os.environ',{'ANTHROPIC_API_KEY':'fixture-never-sent'})
        configured.start();self.addCleanup(configured.stop)
        night_http.NightRestHTTPTests.setUp(self)

    def prepare_route(self,token=None):
        self.prepare(token,version='1.9.0');self.action('continue_pf_encounter',token)
        actor=self.state(token)['state']['characters'][0]['id']
        for clue in ('registro','recibo'):self.action('investigate',token,character=actor,opportunity=clue,method='take20')
        return actor

    def test_captured_travel_survives_failed_commit_and_new_client_without_second_provider(self):
        actor=self.prepare_route();before=self.state()
        body={'id':secrets.token_hex(12),'version':before['version'],'type':'talk','kind':'action','character':actor,'text':'Voy al cobertizo','director':True}
        result=reply(narration='El sendero del patio está despejado.',routeTravel={'exit':'cobertizo'},memory=memory(location='NO-CONFIRMADO'))
        with patch.object(server,'search',return_value=[]),patch.object(server,'ai_reply',return_value=result) as provider:
            with patch.object(server.STORE,'commit',side_effect=Unavailable('Interrupted route commit')):
                with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/action',body)
            detail=json.load(error.exception);error.exception.close();self.assertEqual(error.exception.code,503,detail);self.assertEqual(provider.call_count,1)
        self.assertEqual(self.state(),before)
        previous=server.STORE
        if isinstance(previous,FirestoreStore):
            server.STORE=FirestoreStore.from_environment();server.STORE.prefix=previous.prefix
        try:
            with patch.object(server,'search',return_value=[]),patch.object(server,'ai_reply',side_effect=AssertionError('Paid travel repeated')):
                self.request('/api/action',body);after=self.state()
                self.assertTrue(self.request('/api/action',body)['duplicate']);self.assertEqual(self.state(),after)
            state=after['state'];self.assertEqual(state['boardScenes']['current'],'cobertizo')
            self.assertNotEqual(state['location'],'NO-CONFIRMADO');self.assertEqual(state['characters'][1]['sceneId'],'patio')
            self.assertEqual([c['hp'] for c in state['characters']],[16,7])
            self.assertEqual(len([m for m in state['messages'] if m.get('routeTransition')]),1)
            exported=self.request('/api/export',{});self.action('import',campaign=exported)
            self.assertEqual(self.state()['state']['boardScenes']['current'],'cobertizo')
            self.assertEqual(self.state()['state']['worldTime'],before['state']['worldTime'])
        finally:server.STORE=previous

    def test_non_owner_ooc_and_dialogue_cannot_execute_a_suggested_travel(self):
        guest=self.request('/api/join',{'name':'Luis','invite':self.state()['invite']})['token']
        actor=self.prepare_route(guest);baseline=self.state()
        result=reply(narration='Fixture',routeTravel={'exit':'cobertizo'})
        for case in ('host','ooc','dialogue','locked'):
            body={'id':secrets.token_hex(12),'version':baseline['version'],'type':'talk','kind':'action','text':'Voy al cobertizo','director':True}
            token=guest
            if case=='host':token=self.token
            elif case in ('ooc','dialogue'):body['kind']=case
            answer=copy.deepcopy(result)
            if case=='locked':answer['routeTravel']['exit']='inventada'
            with self.subTest(case=case),patch.object(server,'search',return_value=[]),patch.object(server,'ai_reply',return_value=answer):
                with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/action',body,token)
                detail=json.load(error.exception);error.exception.close();self.assertEqual(error.exception.code,403 if case=='host' else 400,detail)
            self.assertEqual(self.state(),baseline)
