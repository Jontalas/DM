import copy
import unittest
from unittest.mock import patch
import combat
import engine
import pf_recovery


class DisabledMovementTests(unittest.TestCase):
    me={'id':'host','name':'Ana','host':True}

    def setUp(self):
        self.state=engine.initial_state({})
        engine.apply_action(self.state,{'type':'character','character':{'name':'Aria','speed':6}},self.me)
        self.actor=self.state['characters'][0];self.actor['hp']=0
        self.state['board'].update(active=True,order=[{'id':self.actor['id'],'roll':20,'modifier':0}],turn=0,spent={},acted=[self.actor['id']])

    def move(self,path):engine.apply_action(self.state,{'type':'move','character':self.actor['id'],'path':path,'acknowledge':True},self.me)

    def test_zero_hp_moves_half_normal_speed_without_damage_or_speed_rewrite(self):
        self.assertEqual(combat.movement_cells(self.actor),3)
        before=copy.deepcopy(self.state)
        with patch('game_randomness.draw',side_effect=AssertionError('Movement rolled')):
            with self.assertRaises(ValueError):self.move([[0,1],[0,2],[0,3],[0,4]])
            self.assertEqual(self.state,before);self.move([[0,1],[0,2],[0,3]])
        self.assertEqual((self.actor['x'],self.actor['y']),(0,3));self.assertEqual(self.actor['hp'],0);self.assertEqual(self.actor['speed'],6)
        self.assertTrue(self.state['board']['spent'][self.actor['id']]['move']);self.assertIn({'book':'reglas','page':568},self.state['messages'][-1]['refs'])

    def test_conscious_negative_hp_gets_same_limit_and_retains_its_medical_proof(self):
        self.actor['hp']=-1;pf_recovery.record_stabilization(self.actor,assisted=False,round_number=1);pf_recovery.apply_hour(self.actor,20)
        medical=copy.deepcopy(self.actor['recoveryState']);self.assertEqual(combat.movement_cells(self.actor),3)
        self.move([[1,1],[2,2]]);self.assertEqual(self.actor['recoveryState'],medical);self.assertEqual(self.actor['hp'],-1)
        with self.assertRaises(ValueError):self.move([[2,3]])

    def test_diagonal_and_difficult_costs_still_use_the_reduced_budget(self):
        before=copy.deepcopy(self.state)
        with self.assertRaises(ValueError):self.move([[1,1],[2,2],[3,3]])
        self.assertEqual(self.state,before);self.state['board']['terrain']={'1,1':'difficult'}
        self.move([[1,1]]);self.assertEqual((self.actor['x'],self.actor['y']),(1,1))

    def test_odd_speed_limits_only_full_grid_cells_and_never_grants_a_minimum_cell(self):
        for speed,expected in ((1,0),(3,1),(5,2),(6,3),(100,50)):
            self.actor['speed']=speed;self.assertEqual(combat.movement_cells(self.actor),expected)
        self.actor['speed']=1;before=copy.deepcopy(self.state)
        with self.assertRaises(ValueError):self.move([[0,1]])
        self.assertEqual(self.state,before)

    def test_healthy_unconscious_and_spent_standard_keep_distinct_limits(self):
        self.actor['hp']=1;self.assertEqual(combat.movement_cells(self.actor),6)
        self.actor['hp']=-1;self.actor['stable']=True;self.assertEqual(combat.movement_cells(self.actor),0)
        with self.assertRaises(ValueError):self.move([[0,1]])
        self.actor['hp']=0;self.state['board']['spent'][self.actor['id']]={'standard':True}
        before=copy.deepcopy(self.state)
        with self.assertRaises(ValueError):self.move([[0,1]])
        self.assertEqual(self.state,before)

    def test_outside_combat_does_not_claim_the_whole_route_is_one_move_action(self):
        self.state['board']['active']=False;self.move([[0,i] for i in range(1,7)])
        self.assertEqual(self.actor['y'],6);self.assertEqual(self.actor['hp'],0);self.assertEqual(self.actor['speed'],6)


class FiveFootStepTests(unittest.TestCase):
    me={'id':'host','name':'Ana','host':True}

    def setUp(self,version='1.16.0'):
        from test_character_builder import choices
        self.state=engine.initial_state({})
        engine.apply_action(self.state,{'type':'create_character','choices':choices()},self.me)
        self.identifier=self.state['characters'][0]['id']
        engine.apply_action(self.state,{'type':'enter_pf_encounter','encounter':'patio-del-peaje','encounterVersion':version,'character':self.identifier},self.me)
        with patch('game_randomness.draw',side_effect=[20,1]),patch('game_randomness.initiative_tie',return_value=0):
            engine.apply_action(self.state,{'type':'choose_pf_encounter','choice':'combat'},self.me)
        self.state['board']['autoEnemies']=False

    @property
    def actor(self):return next(c for c in self.state['characters'] if c['id']==self.identifier)

    def step(self,path=None,me=None):
        engine.apply_action(self.state,{'type':'five_foot_step','character':self.identifier,'path':path if path is not None else [[0,1]]},me or self.me)

    def test_one_clear_step_is_no_action_no_rng_and_no_change_to_health_or_turn(self):
        before=copy.deepcopy(self.state);budget=copy.deepcopy(before['board']['spent'])
        with patch('game_randomness.draw',side_effect=AssertionError('Step rolled dice')):self.step()
        self.assertEqual((self.actor['x'],self.actor['y']),(0,1))
        self.assertEqual((self.actor['hp'],self.actor['speed']),(before['characters'][0]['hp'],before['characters'][0]['speed']))
        self.assertEqual(self.state['board']['spent'],budget)
        self.assertEqual((self.state['board']['round'],self.state['board']['turn']),(before['board']['round'],before['board']['turn']))
        self.assertTrue(self.state['board']['fiveFootSteps'][self.identifier])
        for page in (184,190,194):self.assertIn({'book':'reglas','page':page},self.state['messages'][-1]['refs'])

    def rejected(self,callback,error=ValueError):
        before=copy.deepcopy(self.state)
        with patch('game_randomness.draw',side_effect=AssertionError('Rejected step rolled dice')):
            with self.assertRaises(error):callback()
        self.assertEqual(self.state,before)

    def test_step_and_other_movement_are_mutually_exclusive_until_own_next_turn(self):
        self.step();self.rejected(lambda:self.step([[0,2]]))
        self.rejected(lambda:engine.apply_action(self.state,{'type':'move','character':self.identifier,'path':[[0,2]],'acknowledge':True},self.me))
        engine.apply_action(self.state,{'type':'turn'},self.me)
        self.assertTrue(self.state['board']['fiveFootSteps'][self.identifier]);self.rejected(lambda:self.step([[0,2]]))
        engine.apply_action(self.state,{'type':'turn'},self.me)
        self.assertNotIn('fiveFootSteps',self.state['board']);self.step([[0,2]])

    def test_regular_movement_even_back_to_origin_prevents_the_step(self):
        engine.apply_action(self.state,{'type':'move','character':self.identifier,'path':[[0,1],[0,0]],'acknowledge':True},self.me)
        self.assertEqual((self.actor['x'],self.actor['y']),(0,0));self.rejected(self.step)

    def test_step_can_precede_or_follow_a_standard_attack_without_spending_movement(self):
        for step_first in (True,False):
            with self.subTest(step_first=step_first):
                self.setUp();npc=self.state['pfEncounter']['npc']
                if step_first:self.step()
                with patch('game_randomness.draw',side_effect=AssertionError('Physical attack rolled twice')):
                    engine.apply_action(self.state,{'type':'attack','character':self.identifier,'target':npc,'physical':{'attack':[1]}},self.me)
                if not step_first:self.step()
                self.assertEqual(self.state['board']['spent'][self.identifier],{'standard':True})
                self.assertEqual((self.actor['x'],self.actor['y']),(0,1))

    def test_zero_and_verified_conscious_negative_hp_keep_health_and_medical_proof(self):
        for hp in (0,-1):
            with self.subTest(hp=hp):
                self.setUp();self.actor['hp']=hp
                if hp<0:
                    pf_recovery.record_stabilization(self.actor,assisted=False,round_number=1);pf_recovery.apply_hour(self.actor,20)
                medical=copy.deepcopy(self.actor.get('recoveryState'));speed=self.actor['speed']
                with patch('game_randomness.draw',side_effect=AssertionError('Step advanced the medical clock')):self.step()
                self.assertEqual((self.actor['hp'],self.actor['speed']),(hp,speed));self.assertEqual(self.actor.get('recoveryState'),medical)
                self.assertFalse(self.state['board']['spent'].get(self.identifier,{}).get('move'))

    def test_step_checks_normal_speed_not_the_reduced_move_action_allowance(self):
        self.actor['hp']=0;self.actor['speed']=2;self.actor['creation']['manualOverride']=True
        self.assertEqual(combat.movement_cells(self.actor),1);self.step();self.assertEqual(self.actor['hp'],0)

    def test_unconscious_dead_conditioned_and_slow_characters_are_not_moved(self):
        changes=[{'hp':-1,'stable':True},{'hp':-self.actor['abilities'][2]}, {'conditions':'Cegado'}]
        changes.extend({'speed':speed} for speed in (0,1,True,2.5))
        for change in changes:
            with self.subTest(change=change):
                self.setUp();self.actor.update(change);self.rejected(self.step)

    def test_occupied_difficult_and_corner_cells_are_rejected_without_side_effects(self):
        cases=[({},[[1,0]]),({'0,1':'wall'},[[0,1]]),({'0,1':'difficult'},[[0,1]]),({'0,0':'difficult'},[[0,1]]),({'0,1':'wall'},[[1,1]])]
        for terrain,path in cases:
            with self.subTest(terrain=terrain,path=path):
                self.setUp();self.state['board']['terrain']=terrain;self.rejected(lambda:self.step(path))
        self.setUp();self.step([[1,1]]);self.assertEqual((self.actor['x'],self.actor['y']),(1,1))

    def test_path_shape_permissions_pending_and_lighting_are_validated(self):
        for path in ([],[[0,1],[0,2]],[[0,0]],[[0,2]],[[-1,0]],[[0,True]],[[0,1.0]],['0,1']):
            with self.subTest(path=path):self.rejected(lambda:self.step(path))
        self.rejected(lambda:self.step(me={'id':'other','host':False}),PermissionError)
        self.rejected(lambda:self.step(me={'id':'other','host':True}),PermissionError)
        self.state['pending']=[{'reason':'Excepción todavía pendiente'}];self.rejected(self.step);self.state['pending']=[]
        self.state['pfEncounter']['definition']['conditions']['lighting']='dark';self.rejected(self.step)

    def test_legacy_encounters_and_unknown_manual_movement_are_not_reinterpreted(self):
        for version in ('1.0.0','1.15.0'):
            self.setUp(version);self.rejected(self.step)
        for cost in ('move','full'):
            self.setUp();engine.apply_action(self.state,{'type':'manual','character':self.identifier,'actionCost':cost,'reason':'Acción de prueba','resolution':'Sin desplazamiento verificable'},self.me)
            with self.assertRaisesRegex(ValueError,'revisión excepcional'):self.step()

    def test_step_counter_survives_structural_copy_validation_and_rejects_corruption(self):
        self.step();before=copy.deepcopy(self.state);engine.validate_copy_structure(self.state);self.assertEqual(self.state,before)
        for marks in ([],None,{self.identifier:1},{'missing-character':True}):
            damaged=copy.deepcopy(before);damaged['board']['fiveFootSteps']=marks
            with self.subTest(marks=marks),self.assertRaises(ValueError):engine.validate_copy_structure(damaged)

    def test_end_and_restart_clear_the_temporary_step_counter(self):
        self.step();engine.apply_action(self.state,{'type':'endcombat'},self.me);self.assertNotIn('fiveFootSteps',self.state['board'])
        with patch('game_randomness.draw',side_effect=[20,1]),patch('game_randomness.initiative_tie',return_value=0):
            engine.apply_action(self.state,{'type':'combat','automateEnemies':False},self.me)
        self.step([[0,2]])

    def test_step_counter_does_not_change_the_verified_npc_aid_budget_or_receipt(self):
        import pf_encounters
        self.actor['hp']=0;self.step();npc=self.state['pfEncounter']['npc']
        with patch('game_randomness.draw',side_effect=[20,20]):
            engine.apply_action(self.state,{'type':'attack','character':self.identifier,'target':npc,'physical':{'attack':[1]}},self.me)
        self.assertFalse(self.state['board']['active']);self.assertNotIn('fiveFootSteps',self.state['board'])
        self.assertEqual((self.actor['hp'],self.actor['stable']),(-1,True))
        self.assertEqual(self.state['pfEncounter']['npcAidEpisode']['end']['attempts'],1)
        pf_encounters.validate_restored(self.state)
