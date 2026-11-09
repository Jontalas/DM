import copy
import unittest
from unittest.mock import patch
import engine
import pf_encounters
import pf_light_exploration as light
import pf_scene_transition
import adventure_modules
import adventure_routes
from test_character_builder import choices


class LightExplorationTests(unittest.TestCase):
    def setUp(self,version='1.12.0'):
        self.me={'id':'player','name':'Ana','host':True}
        self.state=engine.initial_state({})
        self.act('create_character',choices=choices());self.actor=self.state['characters'][0]['id']
        self.act('enter_pf_encounter',encounter='patio-del-peaje',encounterVersion=version,character=self.actor)
        with patch('game_randomness.draw',side_effect=[20,1]),patch('game_randomness.initiative_tie',return_value=0):self.act('choose_pf_encounter',choice='combat')
        self.npc=self.state['characters'][1]['id']
        with patch('game_randomness.draw',side_effect=[12,1]):self.act('attack',character=self.actor,target=self.npc)
        for _ in range(4):
            with patch('game_randomness.draw',side_effect=[19,1,4]):self.act('turn')
        self.assertEqual([c['hp'] for c in self.state['characters']],[0,1])
        self.act('accept_pf_ceasefire')

    def act(self,kind,**body):
        if kind=='investigate':
            import server
            server.queue_investigation(self.state,body,self.me)
            engine.apply_action(self.state,{'type':'check','request':self.state['pending'][-1]['check']['id'],'method':body['method']},self.me)
        elif kind=='travel_scene':adventure_routes.travel(self.state,body,self.me)
        else:engine.apply_action(self.state,{'type':kind,**body},self.me)

    def test_zero_searches_walks_all_scenes_and_returns_without_healing_or_rest(self):
        before=copy.deepcopy(self.state['characters'])
        self.assertTrue(light.eligible(self.state,self.state['characters'][0]))
        with patch('game_randomness.draw',side_effect=AssertionError('Light action rolled')):
            self.act('continue_pf_encounter')
            for scene,clues in [('patio',('registro','recibo')),('cobertizo',('marca',)),('almacen',('bulto','recepcion'))]:
                if scene!='patio':self.act('travel_scene',exit=scene)
                for clue in clues:self.act('investigate',character=self.actor,opportunity=clue,method='take20')
            self.assertTrue(adventure_routes.public_view(self.state)['completed'])
            self.act('travel_scene',exit='patio')
        for old,new in zip(before,self.state['characters']):
            self.assertEqual({k:v for k,v in new.items() if k!='sceneId'},old)
        self.assertNotIn('pfNightRest',self.state);self.assertNotIn('npcRecovery',self.state['pfEncounter'])
        pf_encounters.validate_restored(self.state);pf_scene_transition.validate_restored(self.state)

    def test_latest_catalog_revision_keeps_zero_hp_route_and_pending_validation(self):
        version=pf_encounters.definition()['version'];self.setUp(version)
        self.test_zero_searches_walks_all_scenes_and_returns_without_healing_or_rest()
        self.setUp(version);self.test_pending_search_revalidates_zero_and_does_not_deadlock_itself()

    def test_pending_search_revalidates_zero_and_does_not_deadlock_itself(self):
        self.act('continue_pf_encounter')
        spec=adventure_modules.investigation(self.state,{'character':self.actor,'opportunity':'registro'},self.me)
        pending={'investigation':'registro','check':{'character':self.actor,'kind':'skill','key':'Percepción','dc':spec['dc']}}
        self.state['pending']=[pending];adventure_modules.validate_pending(self.state,pending)
        self.state['characters'][0]['hp']=-1
        with self.assertRaises(ValueError):adventure_modules.validate_pending(self.state,pending)

    def test_clinical_unknowns_edits_and_previous_definition_never_gain_coverage(self):
        baseline=copy.deepcopy(self.state)
        for case in ('negative','unconscious-npc','condition','speed','skills','override','old','combat','terrain','event'):
            self.state=copy.deepcopy(baseline);actor,npc=self.state['characters']
            if case=='negative':actor.update(hp=-1,stable=True,recoveryState={'conscious':True})
            elif case=='unconscious-npc':npc.update(hp=-1,stable=True)
            elif case=='condition':actor['conditions']='Fatigado'
            elif case=='speed':actor['speed']+=1
            elif case=='skills':actor['skillTotals'][0]['total']+=1
            elif case=='override':actor['creation']['manualOverride']=True
            elif case=='old':self.state['pfEncounter']['definition']=pf_encounters.definition('1.11.0')
            elif case=='combat':self.state['board']['active']=True
            elif case=='terrain':self.state['board']['terrain']={'1,1':'difficult'}
            else:self.state['consequences']=[{'interpreted':False}]
            before=copy.deepcopy(self.state)
            with self.subTest(case=case):
                self.assertFalse(light.eligible(self.state,actor))
                self.assertIsNotNone(pf_scene_transition.limitation(self.state))
                self.assertEqual(self.state,before)

    def test_owner_retains_search_and_exit_decisions_even_against_host(self):
        self.act('continue_pf_encounter')
        other={**self.me,'id':'different-host'};before=copy.deepcopy(self.state)
        with self.assertRaises(PermissionError):adventure_modules.investigation(self.state,{'character':self.actor,'opportunity':'registro'},other)
        self.assertEqual(self.state,before)
