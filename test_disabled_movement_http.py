import copy
import secrets
import unittest
import urllib.error
from unittest.mock import patch
import server
from firebase_store import FirestoreStore,Unavailable
import test_pf_night_rest_http as transport
from test_character_builder import choices


class DisabledMovementHTTPTests(unittest.TestCase):
    setUpClass=classmethod(transport.NightRestHTTPTests.setUpClass.__func__)
    tearDownClass=classmethod(transport.NightRestHTTPTests.tearDownClass.__func__)
    setUp=transport.NightRestHTTPTests.setUp
    request=transport.NightRestHTTPTests.request
    state=transport.NightRestHTTPTests.state
    action=transport.NightRestHTTPTests.action

    def test_half_speed_failure_is_atomic_and_valid_move_recovers_once_without_rng_or_ai(self):
        self.action('create_character',choices=choices());actor=self.state()['state']['characters'][0]['id'];self.action('create_npc',template='pf1-goblin-warrior-1')
        with patch('game_randomness.draw',side_effect=[20,1]),patch('game_randomness.initiative_tie',return_value=0):self.action('combat',automateEnemies=False)
        self.action('manual',character=actor,hpDelta=-16,reason='Estado inicial de prueba',resolution='PJ a0PG para comprobar movimiento')
        before=self.state();self.assertEqual(before['state']['characters'][0]['hp'],0)
        with patch.object(server,'ai_reply',side_effect=AssertionError('Move called provider')),patch.object(server.STORE,'action_random_seed',side_effect=AssertionError('Move reserved dice')):
            with self.assertRaises(urllib.error.HTTPError) as error:self.action('move',character=actor,path=[[0,i] for i in range(1,5)],acknowledge=True)
            self.assertEqual(error.exception.code,400);error.exception.close();self.assertEqual(self.state(),before)
            body={'id':secrets.token_hex(12),'version':before['version'],'type':'move','character':actor,'path':[[0,i] for i in range(1,4)],'acknowledge':True}
            with patch.object(server.STORE,'commit',side_effect=Unavailable('Interrupted movement')) as failed:
                with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/action',body)
                self.assertEqual(error.exception.code,503);error.exception.close()
            attempted=copy.deepcopy(failed.call_args.args[5]);self.assertNotIn('randomness',failed.call_args.kwargs);self.assertEqual(self.state(),before)
        previous=server.STORE
        if isinstance(previous,FirestoreStore):server.STORE=FirestoreStore.from_environment();server.STORE.prefix=previous.prefix
        try:
            with patch.object(server,'ai_reply',side_effect=AssertionError('Retry called provider')),patch.object(server.STORE,'action_random_seed',side_effect=AssertionError('Retry reserved dice')):
                self.request('/api/action',body);after=self.state();self.assertTrue(self.request('/api/action',body)['duplicate']);self.assertEqual(self.state(),after)
            for key in ('characters','board','worldTime'):self.assertEqual(after['state'][key],attempted[key])
            pc=after['state']['characters'][0];self.assertEqual((pc['x'],pc['y'],pc['hp'],pc['speed']),(0,3,0,6))
            self.action('import',campaign=self.request('/api/export',{}));self.assertEqual(self.state()['state']['characters'],after['state']['characters'])
        finally:server.STORE=previous


class FiveFootStepHTTPTests(unittest.TestCase):
    setUpClass=classmethod(transport.NightRestHTTPTests.setUpClass.__func__)
    tearDownClass=classmethod(transport.NightRestHTTPTests.tearDownClass.__func__)
    setUp=transport.NightRestHTTPTests.setUp
    request=transport.NightRestHTTPTests.request
    state=transport.NightRestHTTPTests.state
    action=transport.NightRestHTTPTests.action

    def test_step_is_atomic_owner_chosen_recovered_once_and_retained_in_a_copy(self):
        self.action('create_character',choices=choices());actor=self.state()['state']['characters'][0]['id']
        self.action('enter_pf_encounter',encounter='patio-del-peaje',encounterVersion='1.16.0',character=actor)
        with patch('game_randomness.draw',side_effect=[20,1]),patch('game_randomness.initiative_tie',return_value=0):self.action('choose_pf_encounter',choice='combat')
        current=self.state();spectator=self.request('/api/join',{'invite':current['invite'],'name':'Espectador'})['token'];before=self.state()
        body={'id':secrets.token_hex(12),'version':before['version'],'type':'five_foot_step','character':actor,'path':[[0,1]]}
        with self.assertRaises(urllib.error.HTTPError) as denied:self.request('/api/action',body,spectator)
        self.assertEqual(denied.exception.code,403);denied.exception.close();self.assertEqual(self.state(),before)
        body['id']=secrets.token_hex(12)
        with patch.object(server,'ai_reply',side_effect=AssertionError('Step called provider')),patch.object(server.STORE,'action_random_seed',side_effect=AssertionError('Step reserved dice')):
            with patch.object(server.STORE,'commit',side_effect=Unavailable('Interrupted step')):
                with self.assertRaises(urllib.error.HTTPError) as interrupted:self.request('/api/action',body)
                self.assertEqual(interrupted.exception.code,503);interrupted.exception.close();self.assertEqual(self.state(),before)
        previous=server.STORE
        if isinstance(previous,FirestoreStore):server.STORE=FirestoreStore.from_environment();server.STORE.prefix=previous.prefix
        try:
            with patch.object(server,'ai_reply',side_effect=AssertionError('Step retry called provider')),patch.object(server.STORE,'action_random_seed',side_effect=AssertionError('Step retry reserved dice')):
                self.request('/api/action',body);after=self.state();self.assertTrue(self.request('/api/action',body)['duplicate']);self.assertEqual(self.state(),after)
            self.assertEqual(after['version'],before['version']+1);self.assertEqual(after['state']['board']['spent'],before['state']['board']['spent'])
            pc=after['state']['characters'][0];self.assertEqual((pc['x'],pc['y'],pc['hp']),(0,1,before['state']['characters'][0]['hp']))
            self.assertEqual(len(after['state']['messages']),len(before['state']['messages'])+1)
            self.assertTrue(after['state']['board']['fiveFootSteps'][actor])
            self.action('restore_campaign_copy',campaign=self.request('/api/export',{}));restored=self.state()
            self.assertTrue(restored['state']['board']['fiveFootSteps'][actor])
            with self.assertRaises(urllib.error.HTTPError) as repeated:self.action('five_foot_step',character=actor,path=[[0,2]])
            self.assertEqual(repeated.exception.code,400);repeated.exception.close();self.assertEqual(self.state(),restored)
        finally:server.STORE=previous
