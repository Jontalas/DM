import copy
import secrets
import unittest
import urllib.error
from unittest.mock import patch
import server
from firebase_store import FirestoreStore,Unavailable
import test_pf_night_rest_http as transport
from test_character_builder import choices


class AwakeExplorationHTTPTests(unittest.TestCase):
    setUpClass=classmethod(transport.NightRestHTTPTests.setUpClass.__func__)
    tearDownClass=classmethod(transport.NightRestHTTPTests.tearDownClass.__func__)
    setUp=transport.NightRestHTTPTests.setUp
    request=transport.NightRestHTTPTests.request
    state=transport.NightRestHTTPTests.state
    action=transport.NightRestHTTPTests.action

    def prepare(self):
        self.action('create_character',choices=choices());actor=self.state()['state']['characters'][0]['id']
        self.action('enter_pf_encounter',encounter='patio-del-peaje',encounterVersion=getattr(self,'encounter_version','1.13.0'),character=actor)
        with patch('game_randomness.draw',side_effect=[20,1]),patch('game_randomness.initiative_tie',return_value=0):self.action('choose_pf_encounter',choice='combat')
        for _ in range(4):
            with patch('game_randomness.draw',side_effect=[19,1,4]):self.action('turn')
        npc=self.state()['state']['characters'][1]['id']
        with patch('game_randomness.draw',side_effect=[12,4,20,20,20,20]):self.action('attack',character=actor,target=npc)
        self.assertEqual([c['hp'] for c in self.state()['state']['characters']],[-1,-2])
        self.assertTrue(self.state()['state']['pfLightExplorationView']['canExplore'])
        self.action('continue_pf_encounter')
        for clue in ('registro','recibo'):self.action('investigate',character=actor,opportunity=clue,method='take20')
        return actor,npc

    def test_travel_failed_commit_new_client_duplicate_and_copy_keep_both_medical_proofs(self):
        self.prepare();before=self.state();body={'id':secrets.token_hex(12),'version':before['version'],'type':'travel_scene','exit':'cobertizo'}
        with patch.object(server,'ai_reply',side_effect=AssertionError('Travel called provider')),patch.object(server.STORE,'action_random_seed',side_effect=AssertionError('Walking reserved dice')):
            with patch.object(server.STORE,'commit',side_effect=Unavailable('Interrupted awake travel')) as failed:
                with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/action',body)
                self.assertEqual(error.exception.code,503);error.exception.close()
            attempted=copy.deepcopy(failed.call_args.args[5]);self.assertEqual(self.state(),before)
            previous=server.STORE
            if isinstance(previous,FirestoreStore):server.STORE=FirestoreStore.from_environment();server.STORE.prefix=previous.prefix
            try:
                self.request('/api/action',body);after=self.state();self.assertTrue(self.request('/api/action',body)['duplicate']);self.assertEqual(self.state(),after)
                for key in ('characters','pfEncounter','worldTime','board','routeProgress'):self.assertEqual(after['state'][key],attempted[key])
                self.assertEqual(after['state']['characters'][1]['sceneId'],'patio')
                self.action('import',campaign=self.request('/api/export',{}));self.assertEqual(self.state()['state']['characters'],after['state']['characters'])
            finally:server.STORE=previous

    def test_latest_catalog_revision_preserves_clinical_travel_receipts_and_copy(self):
        import pf_encounters
        self.encounter_version=pf_encounters.definition()['version']
        self.test_travel_failed_commit_new_client_duplicate_and_copy_keep_both_medical_proofs()

    def test_manual_correction_leaves_history_but_revokes_current_clinical_permission(self):
        actor,npc=self.prepare();self.action('travel_scene',exit='cobertizo');old_receipt=self.state()['state']['pfEncounter']['recoveryOutcome']
        self.action('manual',character=npc,hpDelta=1,reason='Corrección técnica explícita',resolution='No certifica cuidados nuevos')
        before=self.state();self.assertFalse(before['state']['pfLightExplorationView']['canExplore'])
        self.assertEqual(before['state']['pfEncounter']['recoveryOutcome'],old_receipt)
        with patch('game_randomness.draw',side_effect=AssertionError('Unavailable search rolled')),self.assertRaises(urllib.error.HTTPError) as error:self.action('investigate',character=actor,opportunity='marca',method='take20')
        self.assertEqual(error.exception.code,400);error.exception.close();self.assertEqual(self.state(),before)
