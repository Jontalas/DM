import copy
import secrets
import unittest
import urllib.error
from unittest.mock import patch
import server
from firebase_store import FirestoreStore,Unavailable
import test_pf_night_rest_http as transport
from test_character_builder import choices


class LightExplorationHTTPTests(unittest.TestCase):
    setUpClass=classmethod(transport.NightRestHTTPTests.setUpClass.__func__)
    tearDownClass=classmethod(transport.NightRestHTTPTests.tearDownClass.__func__)
    setUp=transport.NightRestHTTPTests.setUp
    request=transport.NightRestHTTPTests.request
    state=transport.NightRestHTTPTests.state
    action=transport.NightRestHTTPTests.action

    def prepare(self,version='1.12.0'):
        self.action('create_character',choices=choices());actor=self.state()['state']['characters'][0]['id']
        self.action('enter_pf_encounter',encounter='patio-del-peaje',encounterVersion=version,character=actor)
        with patch('game_randomness.draw',side_effect=[20,1]),patch('game_randomness.initiative_tie',return_value=0):self.action('choose_pf_encounter',choice='combat')
        npc=self.state()['state']['characters'][1]['id']
        with patch('game_randomness.draw',side_effect=[12,1]):self.action('attack',character=actor,target=npc)
        for _ in range(4):
            with patch('game_randomness.draw',side_effect=[19,1,4]):self.action('turn')
        self.action('accept_pf_ceasefire');return actor

    def test_zero_perception_retries_once_after_failed_commit_and_preserves_copy_health(self):
        actor=self.prepare();self.assertTrue(self.state()['state']['pfLightExplorationView']['canExplore'])
        self.action('continue_pf_encounter');before=self.state()
        body={'id':secrets.token_hex(12),'version':before['version'],'type':'investigate','character':actor,'opportunity':'registro','method':'take20'}
        with patch.object(server,'ai_reply',side_effect=AssertionError('Search called provider')),patch.object(server.STORE,'action_random_seed',side_effect=AssertionError('Take20 reserved dice')):
            with patch.object(server.STORE,'commit',side_effect=Unavailable('Interrupted light search')) as failed:
                with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/action',body)
                self.assertEqual(error.exception.code,503);error.exception.close()
            attempted=copy.deepcopy(failed.call_args.args[5]);self.assertEqual(self.state(),before)
            previous=server.STORE
            if isinstance(previous,FirestoreStore):server.STORE=FirestoreStore.from_environment();server.STORE.prefix=previous.prefix
            try:
                self.request('/api/action',body);after=self.state();self.assertTrue(self.request('/api/action',body)['duplicate']);self.assertEqual(self.state(),after)
                for key in ('characters','moduleProgress','worldTime'):self.assertEqual(after['state'][key],attempted[key])
                self.assertEqual([c['hp'] for c in after['state']['characters']],[0,1]);self.assertEqual(after['state']['moduleProgress']['searchActions'],20)
                self.action('import',campaign=self.request('/api/export',{}));self.assertEqual(self.state()['state']['characters'],after['state']['characters'])
            finally:server.STORE=previous

    def test_imported_display_capability_cannot_upgrade_old_campaign(self):
        actor=self.prepare(version='1.11.0');exported=self.request('/api/export',{})
        exported['state']['pfLightExplorationView']={'character':actor,'canExplore':True};self.action('import',campaign=exported)
        before=self.state();self.assertNotIn('pfLightExplorationView',before['state'])
        with self.assertRaises(urllib.error.HTTPError) as error:self.action('continue_pf_encounter')
        self.assertEqual(error.exception.code,400);error.exception.close();self.assertEqual(self.state(),before)
