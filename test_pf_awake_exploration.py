import copy
import unittest
from unittest.mock import patch
import engine
import adventure_modules
import board_scenes
import pf_light_exploration as light
import pf_scene_transition
import test_pf_awake_party as clinical_fixture
import test_pf_light_exploration as zero_fixture


class AwakeExplorationTests(unittest.TestCase):
    act=zero_fixture.LightExplorationTests.act

    def setUp(self):
        fixture=clinical_fixture.AwakePartyProofTests();fixture.encounter_version='1.13.0';fixture.setUp()
        self.state,self.me,self.actor=fixture.state,fixture.me,fixture.actor

    def test_both_negative_awake_patients_can_complete_route_without_clinical_changes(self):
        self.assertTrue(light.can_remain_awake(self.state,self.state['characters'][1]))
        zero_fixture.LightExplorationTests.test_zero_searches_walks_all_scenes_and_returns_without_healing_or_rest(self)
        self.assertEqual([c['hp'] for c in self.state['characters']],[-1,-2])
        self.assertTrue(light.eligible(self.state,self.state['characters'][0]))

    def test_pending_perception_resolves_and_spends_no_hp_or_future_hourly_check(self):
        self.act('continue_pf_encounter');before=copy.deepcopy(self.state['characters'])
        with patch('game_randomness.draw',side_effect=AssertionError('Search advanced medical dice')):
            self.act('investigate',character=self.actor,opportunity='registro',method='take20')
        self.assertEqual(self.state['characters'],before);self.assertFalse(self.state['pending'])
        self.assertEqual(len(self.state['moduleProgress']['discoveries']),1)

    def test_changed_or_sleeping_remote_patient_blocks_before_search_and_travel(self):
        self.act('continue_pf_encounter')
        for clue in ('registro','recibo'):self.act('investigate',character=self.actor,opportunity=clue,method='take20')
        self.act('travel_scene',exit='cobertizo');baseline=copy.deepcopy(self.state)
        for case in ('hp','care','awake','epoch','profile'):
            self.state=copy.deepcopy(baseline);actor,npc=self.state['characters']
            if case=='hp':npc['hp']+=1
            elif case=='care':npc.pop('recoveryCare')
            elif case=='awake':npc['recoveryState']['conscious']=False
            elif case=='epoch':self.state['board']['combatSerial']=2
            else:actor['speed']+=1
            before=copy.deepcopy(self.state)
            with self.subTest(case=case),patch('game_randomness.draw',side_effect=AssertionError('Unsafe search rolled')):
                self.assertFalse(light.eligible(self.state,actor));self.assertIsNotNone(pf_scene_transition.limitation(self.state,active=True))
                with self.assertRaises(ValueError):adventure_modules.investigation(self.state,{'character':self.actor,'opportunity':'marca'},self.me)
                if case!='profile':
                    with self.assertRaises(ValueError):board_scenes.require_no_remote_events(self.state)
                self.assertEqual(self.state,before)
