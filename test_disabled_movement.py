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
