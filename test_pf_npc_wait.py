import copy
import unittest
from unittest.mock import patch
import engine
import pf_encounters
import pf_npc_wait as waiting
import pf_recovery
import pf_scene_transition
import board_scenes
from test_character_builder import choices


class PreparedNPCWaitTests(unittest.TestCase):
    def setUp(self):
        self.me={'id':'host','name':'Ana','host':True};self.state=engine.initial_state({})
        self.act('create_character',choices=choices());self.actor=self.state['characters'][0]['id']
        self.act('enter_pf_encounter',encounter='patio-del-peaje',encounterVersion='1.11.0',character=self.actor)
        self.npc=self.state['characters'][1]['id']
        with patch('game_randomness.draw',side_effect=[20,1]),patch('game_randomness.initiative_tie',return_value=0):self.act('choose_pf_encounter',choice='combat')
        self.state['characters'][1]['hp']=-3;self.state['characters'][1]['stable']=False
        self.act('pf_first_aid',physical=20)

    def act(self,kind,**data):engine.apply_action(self.state,{'type':kind,**data},self.me)

    def test_assisted_wait_wakes_without_healing_or_pc_actions_and_allows_exact_guard_continuity(self):
        before=copy.deepcopy(self.state);self.assertIsNone(waiting.limitation(self.state))
        with patch('game_randomness.draw',side_effect=[1,20]) as dice:self.act('wait_pf_npc_recovery')
        self.assertEqual(dice.call_count,2);self.assertEqual(self.state['characters'][0],before['characters'][0]);self.assertEqual(self.state['board'],before['board'])
        patient=self.state['characters'][1];self.assertEqual(patient['hp'],-3);self.assertTrue(pf_recovery.is_conscious(patient))
        receipt=self.state['pfEncounter']['npcRecovery'];self.assertEqual(receipt['hours'],2);self.assertEqual(receipt['elapsedSeconds'],7200)
        waiting.validate_restored(self.state);pf_encounters.validate_restored(self.state);self.assertTrue(waiting.can_remain_awake(self.state,patient));self.assertIsNone(pf_scene_transition.limitation(self.state))
        self.act('continue_pf_encounter');self.assertEqual(self.state['boardScenes']['current'],'patio')
        # The exact conscious guard may remain remote; arbitrary negative patients may not.
        self.state['boardScenes']['current']='other'
        board_scenes.require_no_remote_events(self.state)
        patient=self.state['characters'][1]
        pf_recovery.manual_hp_change(patient,1,reason='Corrección explícita')
        with self.assertRaises(ValueError):board_scenes.require_no_remote_events(self.state)

    def test_unassisted_failure_can_kill_and_no_unnecessary_checks_are_drawn(self):
        state=self.state;patient=state['characters'][1];state['pfEncounter'].pop('outcome');state['pfEncounter']['phase']='combat';state['board']['active']=True
        patient['hp']=-8;state['board']['turn']=1
        pf_recovery.record_stabilization(patient,assisted=False,round_number=1,initiative=self.npc,order=[self.actor,self.npc],epoch=1);pf_encounters.sync_outcome(state)
        with patch('game_randomness.draw',side_effect=[1,1]) as dice:self.act('wait_pf_npc_recovery')
        self.assertEqual(dice.call_count,2);self.assertEqual(patient['hp'],-8) # original object was replaced atomically
        self.assertEqual(self.state['characters'][1]['hp'],-10);self.assertEqual(self.state['pfEncounter']['npcRecovery']['status'],'dead');self.assertIsNone(pf_scene_transition.limitation(self.state))

    def test_six_failed_assisted_checks_keep_the_coverage_frontier_and_cannot_repeat(self):
        with patch('game_randomness.draw',return_value=1) as dice:self.act('wait_pf_npc_recovery')
        self.assertEqual(dice.call_count,6);self.assertEqual(self.state['characters'][1]['hp'],-3)
        self.assertEqual(self.state['pfEncounter']['npcRecovery']['status'],'limit');self.assertIsNotNone(pf_scene_transition.limitation(self.state))
        before=copy.deepcopy(self.state)
        with patch('game_randomness.draw',side_effect=AssertionError('Repeated wait rolled')),self.assertRaises(ValueError):self.act('wait_pf_npc_recovery')
        self.assertEqual(self.state,before)

    def test_different_start_count_keeps_exact_origin_and_no_invented_elapsed_seconds(self):
        start=waiting._snapshot(self.state);start['npc']['care']['initiative']=self.npc;start['round']=2;start['initiative']=self.actor
        before=copy.deepcopy(start);result=waiting.simulate(start,lambda:20)
        self.assertIsNone(result['elapsedSeconds']);self.assertEqual(result['secondsSinceStabilization'],3600);self.assertEqual(result['end']['initiative'],self.npc);self.assertEqual(start,before)

    def test_owner_overdue_clock_pending_and_conditions_reject_before_rng(self):
        before=copy.deepcopy(self.state)
        with self.assertRaises(PermissionError):waiting.wait(self.state,{'type':'wait_pf_npc_recovery'},{**self.me,'id':'other'})
        for case in ('zero','pending','condition','late','epoch'):
            self.state=copy.deepcopy(before)
            if case=='zero':self.state['characters'][0]['hp']=0
            elif case=='pending':self.state['pending']=[{'reason':'Pending'}]
            elif case=='condition':self.state['characters'][1]['conditions']='Fatigada'
            elif case=='late':self.state['board']['round']=601
            elif case=='epoch':self.state['board']['combatSerial']=2
            with self.subTest(case=case),patch('game_randomness.draw',side_effect=AssertionError('Unavailable wait rolled')),self.assertRaises(ValueError):self.act('wait_pf_npc_recovery')

    def test_copy_replay_rejects_orphan_markers_extra_dice_and_false_status(self):
        with patch('game_randomness.draw',return_value=20):self.act('wait_pf_npc_recovery')
        baseline=copy.deepcopy(self.state)
        for case in ('orphan','extra','status','hp'):
            state=copy.deepcopy(baseline)
            if case=='orphan':state['pfEncounter'].pop('npcRecovery')
            elif case=='extra':state['pfEncounter']['npcRecovery']['dice'].append(20)
            elif case=='status':state['pfEncounter']['npcRecovery']['status']='dead'
            else:state['pfEncounter']['npcRecovery']['npcHp']=1
            with self.subTest(case=case),self.assertRaises(ValueError):pf_encounters.validate_restored(state)
        with patch('game_randomness.draw',side_effect=AssertionError('Copy replay rolled')):pf_encounters.validate_restored(baseline)

    def test_historical_receipt_survives_later_combat_but_never_authorizes_its_clock(self):
        with patch('game_randomness.draw',return_value=20):self.act('wait_pf_npc_recovery')
        historical=copy.deepcopy(self.state['pfEncounter']['npcRecovery'])
        with patch('game_randomness.draw',side_effect=[20,1]),patch('game_randomness.initiative_tie',return_value=0):self.act('combat',automateEnemies=True)
        pf_encounters.validate_restored(self.state);self.assertEqual(self.state['pfEncounter']['npcRecovery'],historical)
        self.assertFalse(waiting.can_remain_awake(self.state,self.state['characters'][1]))
        with patch('game_randomness.draw',side_effect=AssertionError('Later combat reused wait')),self.assertRaises(ValueError):self.act('wait_pf_npc_recovery')
