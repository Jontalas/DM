import copy
import secrets
import unittest
import urllib.error
from unittest.mock import patch
import server
from firebase_store import FirestoreStore,Unavailable
import test_pf_night_rest_http as transport
from test_character_builder import choices


class NPCWaitHTTPTests(unittest.TestCase):
    setUpClass=classmethod(transport.NightRestHTTPTests.setUpClass.__func__)
    tearDownClass=classmethod(transport.NightRestHTTPTests.tearDownClass.__func__)
    setUp=transport.NightRestHTTPTests.setUp
    request=transport.NightRestHTTPTests.request
    state=transport.NightRestHTTPTests.state
    action=transport.NightRestHTTPTests.action

    def prepare(self,token=None,version='1.11.0'):
        self.action('create_character',token,choices=choices());actor=self.state(token)['state']['characters'][0]['id']
        self.action('enter_pf_encounter',token,encounter='patio-del-peaje',encounterVersion=version,character=actor)
        with patch('game_randomness.draw',side_effect=[20,1]),patch('game_randomness.initiative_tie',return_value=0):self.action('choose_pf_encounter',token,choice='combat')
        npc=self.state(token)['state']['characters'][1]['id']
        with patch('game_randomness.draw',side_effect=[12,4]):self.action('attack',token,character=actor,target=npc)
        with patch('game_randomness.draw',return_value=1):self.action('turn',token)
        with patch('game_randomness.draw',return_value=20):self.action('pf_first_aid',token)
        self.assertEqual(self.state(token)['state']['pfEncounter']['phase'],'resolved')
        return actor,npc

    def test_failed_commit_new_client_same_server_dice_duplicate_and_copy_with_zero_ai(self):
        self.prepare();before=self.state();body={'id':secrets.token_hex(12),'version':before['version'],'type':'wait_pf_npc_recovery'}
        with patch.object(server,'ai_reply',side_effect=AssertionError('Wait called provider')):
            with patch.object(server.STORE,'commit',side_effect=Unavailable('Interrupted NPC wait')) as failed:
                with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/action',body)
                self.assertEqual(error.exception.code,503);error.exception.close()
            attempted=copy.deepcopy(failed.call_args.args[5]);self.assertTrue(failed.call_args.kwargs['randomness']);self.assertEqual(self.state(),before)
            previous=server.STORE
            if isinstance(previous,FirestoreStore):server.STORE=FirestoreStore.from_environment();server.STORE.prefix=previous.prefix
            try:
                self.request('/api/action',body);after=self.state();self.assertTrue(self.request('/api/action',body)['duplicate']);self.assertEqual(self.state(),after)
                for key in ('characters','pfEncounter','worldTime','board'):self.assertEqual(after['state'][key],attempted[key])
                self.assertEqual(after['state']['characters'][0],before['state']['characters'][0]);self.assertEqual(after['state']['characters'][1]['hp'],-3)
                self.action('import',campaign=self.request('/api/export',{}));self.assertEqual(self.state()['state']['characters'],after['state']['characters'])
                baseline=self.state();forged=self.request('/api/export',{});forged['state']['pfEncounter']['npcRecovery']['dice'].append(20)
                with self.assertRaises(urllib.error.HTTPError) as error:self.action('import',campaign=forged)
                self.assertEqual(error.exception.code,400);error.exception.close();self.assertEqual(self.state(),baseline)
            finally:server.STORE=previous

    def test_guest_decides_wait_host_cannot_and_only_exact_awake_guard_can_stay_remote(self):
        guest=self.request('/api/join',{'name':'Luis','invite':self.state()['invite']})['token'];actor,npc=self.prepare(guest);before=self.state()
        with patch.object(server,'ai_reply',side_effect=AssertionError('Wait called provider')),patch.object(server.STORE,'action_random_seed',side_effect=AssertionError('Wrong owner reserved dice')),patch.object(server.STORE,'commit',wraps=server.STORE.commit) as commit:
            with self.assertRaises(urllib.error.HTTPError) as error:self.action('wait_pf_npc_recovery')
            self.assertEqual(error.exception.code,403);error.exception.close();commit.assert_not_called()
        self.assertEqual(self.state(),before)
        with patch('game_randomness.draw',return_value=20),patch.object(server,'ai_reply',side_effect=AssertionError('Wait called provider')):self.action('wait_pf_npc_recovery',guest)
        self.assertTrue(self.state(guest)['state']['pfNpcRecoveryView']['canContinue']);self.action('continue_pf_encounter',guest)
        for clue in ('registro','recibo'):self.action('investigate',guest,character=actor,opportunity=clue,method='take20')
        self.action('travel_scene',guest,exit='cobertizo');self.assertEqual(self.state(guest)['state']['characters'][1]['sceneId'],'patio')
        self.action('manual',character=npc,hpDelta=1,reason='Corrección excepcional',resolution='Sin certificar asistencia')
        baseline=self.state(guest);self.assertFalse(baseline['state']['pfNpcRecoveryView']['canContinue'])
        with self.assertRaises(urllib.error.HTTPError) as error:self.action('investigate',guest,character=actor,opportunity='marca',method='take20')
        self.assertEqual(error.exception.code,400);error.exception.close();self.assertEqual(self.state(guest),baseline)

    def test_published_previous_definition_does_not_acquire_the_new_wait(self):
        self.prepare(version='1.10.0');before=self.state()
        with patch('game_randomness.draw',side_effect=AssertionError('Old definition rolled')):
            with self.assertRaises(urllib.error.HTTPError) as error:self.action('wait_pf_npc_recovery')
            self.assertEqual(error.exception.code,400);error.exception.close()
        self.assertEqual(self.state(),before);self.assertNotIn('pfNpcRecoveryView',before['state'])

    def test_imported_display_permission_cannot_replace_a_verified_recovery(self):
        self.prepare();exported=self.request('/api/export',{});exported['state']['pfNpcRecoveryView']={'canContinue':True,'currentResult':True,'reason':None}
        self.action('import',campaign=exported);before=self.state();self.assertFalse(before['state']['pfNpcRecoveryView']['canContinue'])
        with self.assertRaises(urllib.error.HTTPError) as error:self.action('continue_pf_encounter')
        self.assertEqual(error.exception.code,400);error.exception.close();self.assertEqual(self.state(),before)
