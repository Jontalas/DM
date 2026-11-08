import copy
import unittest
import urllib.error
from unittest.mock import patch
import test_pf_night_rest_http as transport


class CommonGuardHTTPTests(unittest.TestCase):
    setUpClass=classmethod(transport.NightRestHTTPTests.setUpClass.__func__)
    tearDownClass=classmethod(transport.NightRestHTTPTests.tearDownClass.__func__)
    setUp=transport.NightRestHTTPTests.setUp
    request=transport.NightRestHTTPTests.request
    state=transport.NightRestHTTPTests.state
    action=transport.NightRestHTTPTests.action

    def prepare(self,token=None):
        from test_character_builder import choices
        self.action('create_character',token,choices=choices());actor=self.state(token)['state']['characters'][0]['id']
        self.action('enter_pf_encounter',token,encounter='patio-del-peaje',encounterVersion='1.10.0',character=actor)
        with patch('game_randomness.draw',side_effect=[20,1]),patch('game_randomness.initiative_tie',return_value=0):self.action('choose_pf_encounter',token,choice='combat')
        npc=self.state(token)['state']['characters'][1]['id']
        with patch('game_randomness.draw',side_effect=[12,1]):self.action('attack',token,character=actor,target=npc)
        return actor

    def test_default_languages_common_truce_sleep_copy_and_original_template_provenance(self):
        self.prepare();before=self.state()['state']
        self.assertEqual(before['characters'][0]['creation']['choices']['languages'],[])
        self.assertEqual(before['pfCeasefireView']['offerLanguage'],'Común');self.assertIsNone(before['pfCeasefireView']['reason'])
        self.assertEqual([c['hp'] for c in before['characters']],[16,1])
        body=self.action('accept_pf_ceasefire');self.assertTrue(self.request('/api/action',body)['duplicate'])
        self.action('rest_pf_night');exported=self.request('/api/export',{})
        self.assertEqual(exported['state']['pfEncounter']['ceasefire']['sharedLanguage'],'Común')
        self.action('import',campaign=exported);self.action('continue_pf_encounter')
        final=self.state()['state'];self.assertEqual(final['characters'][1]['maxHp'],6)
        self.assertEqual([c['hp'] for c in final['characters']],[16,1]);self.assertEqual(final['boardScenes']['current'],'patio')
        self.assertEqual(final['characters'][1]['npcCreation']['profile']['languages'],['Goblin','Común'])
        for case in ('shared-language','template','profile'):
            altered=copy.deepcopy(exported)
            if case=='shared-language':altered['state']['pfEncounter']['ceasefire']['sharedLanguage']='Goblin'
            elif case=='template':altered['state']['characters'][1]['npcCreation']['template']='pf1-goblin-warrior-1'
            else:altered['state']['characters'][1]['ac']=16
            baseline=self.state()
            with self.subTest(case=case),self.assertRaises(urllib.error.HTTPError) as error:self.action('import',campaign=altered)
            self.assertEqual(error.exception.code,400);error.exception.close();self.assertEqual(self.state(),baseline)

    def test_guest_default_character_keeps_ownership_of_common_response(self):
        guest=self.request('/api/join',{'name':'Luis','invite':self.state()['invite']})['token']
        self.prepare(guest);baseline=self.state()
        with self.assertRaises(urllib.error.HTTPError) as error:self.action('accept_pf_ceasefire')
        self.assertEqual(error.exception.code,403);error.exception.close();self.assertEqual(self.state(),baseline)
        self.action('accept_pf_ceasefire',guest)
        exported=self.request('/api/export',{});self.action('import',campaign=exported)
        self.assertEqual(self.state()['state']['pfEncounter']['ceasefire']['sharedLanguage'],'Común')
