import copy
import secrets
import unittest
import urllib.error
from unittest.mock import patch
import server
from firebase_store import FirestoreStore,Unavailable
import test_pf_night_rest_http as transport
from test_adventure import reply
from test_character_builder import choices


class DeclaredMeleeHTTPTests(unittest.TestCase):
    setUpClass=classmethod(transport.NightRestHTTPTests.setUpClass.__func__)
    tearDownClass=classmethod(transport.NightRestHTTPTests.tearDownClass.__func__)
    request=transport.NightRestHTTPTests.request
    state=transport.NightRestHTTPTests.state
    action=transport.NightRestHTTPTests.action

    def setUp(self):
        configured=patch.dict('os.environ',{'ANTHROPIC_API_KEY':'fixture-never-sent'})
        configured.start();self.addCleanup(configured.stop);transport.NightRestHTTPTests.setUp(self)

    def prepare(self,token=None):
        self.action('create_character',token,choices=choices());actor=self.state(token)['state']['characters'][0]['id']
        self.action('enter_pf_encounter',token,encounter='patio-del-peaje',encounterVersion='1.9.0',character=actor)
        with patch('game_randomness.draw',side_effect=[20,1]),patch('game_randomness.initiative_tie',return_value=0):self.action('choose_pf_encounter',token,choice='combat')
        return actor,self.state(token)['state']['characters'][1]['id']

    def test_failed_commit_new_client_replays_both_paid_intent_and_the_same_server_dice(self):
        actor,target=self.prepare();before=self.state()
        body={'id':secrets.token_hex(12),'version':before['version'],'type':'talk','kind':'action','character':actor,'text':'Ataco a la guardiana con mi espada','director':True}
        result=reply(narration='La guardiana mantiene su espada preparada.',meleeAttack={'target':target})
        with patch.object(server,'search',return_value=[]),patch.object(server,'ai_reply',return_value=result) as provider:
            with patch.object(server.STORE,'commit',side_effect=Unavailable('Interrupted declared attack')) as failed:
                with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/action',body)
            self.assertEqual(error.exception.code,503);error.exception.close();self.assertEqual(provider.call_count,1)
            attempted=copy.deepcopy(failed.call_args.args[5]);self.assertTrue(failed.call_args.kwargs['randomness'])
        self.assertEqual(self.state(),before);previous=server.STORE
        if isinstance(previous,FirestoreStore):
            server.STORE=FirestoreStore.from_environment();server.STORE.prefix=previous.prefix
        try:
            with patch.object(server,'search',return_value=[]),patch.object(server,'ai_reply',side_effect=AssertionError('Attack repeated provider')):
                self.request('/api/action',body);after=self.state();self.assertTrue(self.request('/api/action',body)['duplicate']);self.assertEqual(self.state(),after)
            for key in ('characters','board','pfEncounter','worldTime'):self.assertEqual(after['state'][key],attempted[key])
            attempted_combat=[m['combat'] for m in attempted['messages'] if 'combat' in m]
            self.assertEqual([m['combat'] for m in after['state']['messages'] if 'combat' in m],attempted_combat)
            self.assertEqual(len(attempted_combat),1);self.assertTrue(after['state']['board']['spent'][actor]['standard'])
            exported=self.request('/api/export',{});self.action('import',campaign=exported)
            self.assertEqual(self.state()['state']['characters'],after['state']['characters'])
        finally:server.STORE=previous

    def test_host_cannot_attack_for_guest_and_non_action_intents_are_atomic(self):
        guest=self.request('/api/join',{'name':'Luis','invite':self.state()['invite']})['token']
        actor,target=self.prepare(guest);baseline=self.state()
        result=reply(narration='Fixture',meleeAttack={'target':target})
        for kind,token,code in (('action',self.token,403),('dialogue',guest,400),('ooc',guest,400)):
            with patch.object(server,'search',return_value=[]),patch.object(server,'ai_reply',return_value=result):
                with self.assertRaises(urllib.error.HTTPError) as error:self.action('talk',token,kind=kind,text='Ataco a la guardiana',director=True)
            self.assertEqual(error.exception.code,code);error.exception.close();self.assertEqual(self.state(),baseline)
