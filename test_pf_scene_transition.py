import copy
import unittest
from unittest.mock import patch
import engine
import adventure_modules
import pf_encounters
import pf_scene_transition as transition
from test_character_builder import choices


class CourtyardContinuityTests(unittest.TestCase):
    def setUp(self):
        self.me={'id':'player','name':'Ana','host':True}
        self.state=engine.initial_state({})
        engine.apply_action(self.state,{'type':'create_character','choices':choices()},self.me)
        self.actor=self.state['characters'][0]['id']
        engine.apply_action(self.state,{'type':'enter_pf_encounter','encounter':pf_encounters.ID,
            'encounterVersion':'1.3.0','character':self.actor},self.me)

    def agree(self):
        engine.apply_action(self.state,{'type':'choose_pf_encounter','choice':'parley'},self.me)

    def continue_scene(self):
        engine.apply_action(self.state,{'type':'continue_pf_encounter'},self.me)

    def test_agreement_continues_without_healing_moving_rolling_or_a_provider(self):
        self.agree();before=copy.deepcopy(self.state)
        with patch('game_randomness.draw',side_effect=AssertionError('Transition rolled dice')):
            self.continue_scene()
        for key in ('characters','board','worldTime','pfEncounter'):
            self.assertEqual(self.state[key],before[key])
        self.assertEqual(self.state['adventureModule'],transition.module())
        self.assertEqual(self.state['moduleProgress']['discoveries'],[])
        self.assertNotIn('IA',self.state['adventure']['source'])
        pf_encounters.validate_restored(self.state)
        adventure_modules.validate_restored(self.state)
        transition.validate_restored(self.state)
        after=copy.deepcopy(self.state)
        with self.assertRaises(ValueError):self.continue_scene()
        self.assertEqual(self.state,after)

    def test_owner_decision_and_pending_combat_are_required_before_any_mutation(self):
        before=copy.deepcopy(self.state)
        with self.assertRaises(ValueError):self.continue_scene()
        self.assertEqual(self.state,before)
        self.agree();before=copy.deepcopy(self.state)
        with self.assertRaises(PermissionError):
            engine.apply_action(self.state,{'type':'continue_pf_encounter'},{**self.me,'id':'other'})
        self.assertEqual(self.state,before)

    def test_negative_patient_or_player_cannot_skip_recovery_by_entering_investigation(self):
        self.agree();baseline=copy.deepcopy(self.state)
        for role,hp in ((0,0),(0,-1),(1,-3)):
            self.state=copy.deepcopy(baseline);self.state['characters'][role]['hp']=hp
            before=copy.deepcopy(self.state)
            with self.assertRaises(ValueError):self.continue_scene()
            self.assertEqual(self.state,before)

    def test_dead_npc_and_wounded_positive_player_keep_their_actual_states(self):
        with patch('game_randomness.draw',side_effect=[20,1]):
            engine.apply_action(self.state,{'type':'choose_pf_encounter','choice':'combat'},self.me)
        actor,npc=self.state['characters'];actor['hp']=5;npc['hp']=-12
        pf_encounters.sync_outcome(self.state)
        self.assertEqual(self.state['pfEncounter']['phase'],'resolved')
        before=copy.deepcopy(self.state['characters']);self.continue_scene()
        self.assertEqual(self.state['characters'],before)
        transition.validate_restored(self.state)

    def test_copy_rejects_wrong_link_revision_or_changed_authored_clues(self):
        self.agree();self.continue_scene()
        for field,value in (('moduleSha256','0'*64),('encounterSha256','0'*64),('entryPhase','offered')):
            forged=copy.deepcopy(self.state);forged['pfContinuation'][field]=value
            with self.assertRaises(ValueError):transition.validate_restored(forged)
        forged=copy.deepcopy(self.state);forged['adventureModule']['opportunities'][0]['discovery']='Otra pista'
        with self.assertRaises(ValueError):transition.validate_restored(forged)
        forged=copy.deepcopy(self.state);del forged['pfContinuation']
        with self.assertRaises(ValueError):transition.validate_restored(forged)

    def test_old_scene_does_not_gain_unversioned_continuation(self):
        old=copy.deepcopy(self.state);definition=pf_encounters.definition('1.2.0')
        old['pfEncounter']['definition']=definition
        self.assertIsNotNone(transition.limitation(old))

    def test_later_injury_stops_search_before_dice_instead_of_skipping_patient_events(self):
        self.agree();self.continue_scene()
        self.state['characters'][1]['hp']=-3
        before=copy.deepcopy(self.state)
        with patch('game_randomness.draw',side_effect=AssertionError('Invalid search rolled')):
            with self.assertRaises(ValueError):
                adventure_modules.investigation(self.state,{'character':self.actor,'opportunity':'registro'},self.me)
        self.assertEqual(self.state,before)
