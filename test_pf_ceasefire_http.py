import copy
import secrets
import urllib.error
import unittest
from unittest.mock import patch
import server
from firebase_store import FirestoreStore,Unavailable
import test_pf_night_rest_http as night_http
from test_character_builder import choices


class CeasefireHTTPTests(unittest.TestCase):
    setUpClass=classmethod(night_http.NightRestHTTPTests.setUpClass.__func__)
    tearDownClass=classmethod(night_http.NightRestHTTPTests.tearDownClass.__func__)
    setUp=night_http.NightRestHTTPTests.setUp
    request=night_http.NightRestHTTPTests.request
    state=night_http.NightRestHTTPTests.state
    action=night_http.NightRestHTTPTests.action

    def prepare_truce(self,token=None,version='1.8.0',armor=None):
        selected=choices();selected['abilities'][3:5]=[12,10]
        selected['languages']=['Goblin'];selected['skills'].append('swim')
        if armor:selected['armor']=armor
        self.action('create_character',token,choices=selected)
        actor=self.state(token)['state']['characters'][0]['id']
        self.action('enter_pf_encounter',token,encounter='patio-del-peaje',encounterVersion=version,character=actor)
        with patch('game_randomness.draw',side_effect=[20,1]),patch('game_randomness.initiative_tie',return_value=0):
            self.action('choose_pf_encounter',token,choice='combat')
        npc=self.state(token)['state']['characters'][1]['id']
        with patch('game_randomness.draw',side_effect=[12,1]):self.action('attack',token,character=actor,target=npc)

    def test_commit_retry_new_client_duplicate_copy_and_no_provider(self):
        self.prepare_truce();before=self.state()
        self.assertIsNone(before['state']['pfCeasefireView']['reason'])
        body={'id':secrets.token_hex(12),'version':before['version'],'type':'accept_pf_ceasefire'}
        with patch.object(server.STORE,'commit',side_effect=Unavailable('Interrupted truce commit')):
            with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/action',body)
        self.assertEqual(error.exception.code,503);error.exception.close();self.assertEqual(self.state(),before)
        previous=server.STORE
        if isinstance(previous,FirestoreStore):
            server.STORE=FirestoreStore.from_environment();server.STORE.prefix=previous.prefix
        try:
            with patch.object(server,'ai_reply',side_effect=AssertionError('Truce called provider')),patch('game_randomness.draw',side_effect=AssertionError('Truce rolled')):
                self.request('/api/action',body);after=self.state()
                self.assertTrue(self.request('/api/action',body)['duplicate']);self.assertEqual(self.state(),after)
            self.assertEqual(after['state']['characters'],before['state']['characters'])
            exported=self.request('/api/export',{})
            exported['state']['pfCeasefireView']={'reason':None}
            self.action('import',campaign=exported)
            self.assertIsNotNone(self.state()['state']['pfCeasefireView']['reason'])
            self.action('continue_pf_encounter')
            exported=self.request('/api/export',{});self.action('import',campaign=exported)
            self.assertEqual(self.state()['state']['characters'][1]['hp'],2)
            for case in ('proof','marker','encounter'):
                altered=copy.deepcopy(exported)
                if case=='proof':del altered['state']['pfEncounter']['ceasefire']
                elif case=='marker':altered['state']['messages']=[m for m in altered['state']['messages'] if 'ceasefireSha256' not in m]
                else:altered['state']['pfEncounter']=None
                baseline=self.state()
                with self.subTest(case=case),self.assertRaises(urllib.error.HTTPError) as error:self.action('import',campaign=altered)
                self.assertEqual(error.exception.code,400);error.exception.close();self.assertEqual(self.state(),baseline)
        finally:server.STORE=previous

    def test_host_cannot_accept_for_guest_owner(self):
        guest=self.request('/api/join',{'name':'Luis','invite':self.state()['invite']})['token']
        self.prepare_truce(guest);before=self.state()
        with self.assertRaises(urllib.error.HTTPError) as error:self.action('accept_pf_ceasefire')
        self.assertEqual(error.exception.code,403);error.exception.close();self.assertEqual(self.state(),before)
        self.action('accept_pf_ceasefire',guest)
        self.assertEqual(self.state()['state']['pfEncounter']['phase'],'agreement')
