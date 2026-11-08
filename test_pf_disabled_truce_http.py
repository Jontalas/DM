import copy
import hashlib
import secrets
import urllib.error
import unittest
from unittest.mock import patch
import server
from firebase_store import FirestoreStore,Unavailable
from rule_pack_authoring import canonical
from test_character_builder import choices
import test_pf_ceasefire_http as http_fixture


class DisabledTruceHTTPTests(unittest.TestCase):
    setUpClass=classmethod(http_fixture.CeasefireHTTPTests.setUpClass.__func__)
    tearDownClass=classmethod(http_fixture.CeasefireHTTPTests.tearDownClass.__func__)
    setUp=http_fixture.CeasefireHTTPTests.setUp
    request=http_fixture.CeasefireHTTPTests.request
    state=http_fixture.CeasefireHTTPTests.state
    action=http_fixture.CeasefireHTTPTests.action

    def prepare_zero(self,token=None):
        self.action('create_character',token,choices=choices())
        actor=self.state(token)['state']['characters'][0]['id']
        self.action('enter_pf_encounter',token,encounter='patio-del-peaje',encounterVersion='1.15.0',character=actor)
        with patch('game_randomness.draw',side_effect=[20,1]),patch('game_randomness.initiative_tie',return_value=0):self.action('choose_pf_encounter',token,choice='combat')
        for _ in range(4):
            with patch('game_randomness.draw',side_effect=[19,1,4]):self.action('turn',token)
        return actor

    def test_failed_commit_retry_duplicate_copy_and_full_route_without_ia_or_rolls(self):
        actor=self.prepare_zero();before=self.state()
        self.assertIsNone(before['state']['pfCeasefireView']['reason']);self.assertTrue(before['state']['pfCeasefireView']['disabledPlayerOffer'])
        body={'id':secrets.token_hex(12),'version':before['version'],'type':'accept_pf_ceasefire'}
        with patch.object(server.STORE,'commit',side_effect=Unavailable('Interrupted truce commit')):
            with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/action',body)
        self.assertEqual(error.exception.code,503);error.exception.close();self.assertEqual(self.state(),before)
        previous=server.STORE
        if isinstance(previous,FirestoreStore):
            server.STORE=FirestoreStore.from_environment();server.STORE.prefix=previous.prefix
        try:
            with patch.object(server,'ai_reply',side_effect=AssertionError('Truce called provider')),patch('game_randomness.draw',side_effect=AssertionError('Quiet route rolled')):
                self.request('/api/action',body);after=self.state()
                self.assertTrue(self.request('/api/action',body)['duplicate']);self.assertEqual(self.state(),after)
                self.assertEqual(after['state']['characters'],before['state']['characters'])
                self.assertEqual(after['state']['worldTime'],before['state']['worldTime'])
                exported=self.request('/api/export',{});self.action('import',campaign=exported)
                self.action('continue_pf_encounter')
                for clue in ('registro','recibo'):self.action('investigate',character=actor,opportunity=clue,method='take20')
                self.action('travel_scene',exit='cobertizo');self.action('investigate',character=actor,opportunity='marca',method='take20')
                self.action('travel_scene',exit='almacen')
                for clue in ('bulto','recepcion'):self.action('investigate',character=actor,opportunity=clue,method='take20')
                self.action('travel_scene',exit='patio');self.assertTrue(self.state()['state']['adventureRouteView']['completed'])
                self.assertEqual([c['hp'] for c in self.state()['state']['characters']],[0,6])
                exported=self.request('/api/export',{});self.action('import',campaign=exported)
        finally:server.STORE=previous

    def test_host_cannot_accept_guest_choice_or_import_forged_mercy_receipt(self):
        guest=self.request('/api/join',{'name':'Luis','invite':self.state()['invite']})['token']
        self.prepare_zero(guest);before=self.state()
        with self.assertRaises(urllib.error.HTTPError) as error:self.action('accept_pf_ceasefire')
        self.assertEqual(error.exception.code,403);error.exception.close();self.assertEqual(self.state(),before)
        self.action('accept_pf_ceasefire',guest);exported=self.request('/api/export',{})
        for case in ('healthy-player','legacy-format','missing'):
            altered=copy.deepcopy(exported);record=altered['state']['pfEncounter'];proof=record['ceasefire']
            if case=='healthy-player':proof['actorHp']=1
            elif case=='legacy-format':proof['format']='cronicas-pf-ceasefire-2'
            else:del record['ceasefire']
            if case!='missing':
                for message in altered['state']['messages']:
                    if 'ceasefireSha256' in message:message['ceasefireSha256']=hashlib.sha256(canonical(proof).encode()).hexdigest()
            baseline=self.state()
            with self.subTest(case=case),self.assertRaises(urllib.error.HTTPError) as error:self.action('import',campaign=altered)
            self.assertEqual(error.exception.code,400);error.exception.close();self.assertEqual(self.state(),baseline)
