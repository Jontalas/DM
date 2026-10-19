import copy
import unittest
from unittest.mock import patch

import combat
import tactics
from engine import initial_state,apply_action

HOST={'id':'host','name':'Ana','host':True}
GUEST={'id':'guest','name':'Luis','host':False}


class AutomaticEnemyTests(unittest.TestCase):
    def setUp(self):
        self.state=initial_state({})
        for name,enemy in [('Aria',False),('Bandido',True)]:
            self.act('character',character={'name':name,'enemy':enemy,'maxHp':30,
                'abilities':[14,14,12,10,10,10],'ac':16,'attack':4,'damage':'1d6+2',
                'meleeProfile':{'flatAc':14,'criticalMin':20,'multiplier':2}})
        self.a,self.e=self.state['characters']
        self.act('combat')
        self.state['board'].update(order=[{'id':c['id'],'roll':10,'modifier':0} for c in (self.a,self.e)],
                                  turn=0,acted=[self.a['id']],spent={},autoEnemies=True)

    def act(self,kind,**body):apply_action(self.state,{'type':kind,**body},HOST)

    def test_enemy_attack_and_turn_end_are_automatic(self):
        with patch('engine.dice',side_effect=[[12],[4]]) as dice:self.act('turn')
        self.assertEqual(dice.call_count,2);self.assertEqual(self.a['hp'],24)
        board=self.state['board'];self.assertEqual(board['order'][board['turn']]['id'],self.a['id'])
        self.assertEqual(board['round'],2);self.assertTrue(board['spent'][self.e['id']]['standard'])
        self.assertNotIn('autoPaused',board)

    def test_enemy_can_act_first_when_combat_starts(self):
        self.state['board']['active']=False;self.a['initiative']=-100;self.e['initiative']=100
        with patch('engine.dice',side_effect=[[8],[18],[12],[4]]):self.act('combat',automateEnemies=True)
        self.assertEqual(self.a['hp'],24)
        board=self.state['board'];self.assertEqual(board['order'][board['turn']]['id'],self.a['id'])
        result=next(m['combat'] for m in self.state['messages'] if 'combat' in m)
        self.assertTrue(result['flatFooted']);self.assertEqual(board['round'],1)

    def test_enemy_moves_then_attacks_without_moving_player(self):
        self.e.update(x=5,y=0)
        with patch('engine.dice',side_effect=[[12],[4]]):self.act('turn')
        self.assertTrue(combat.adjacent(self.e,self.a));self.assertEqual((self.a['x'],self.a['y']),(0,0))
        self.assertEqual(self.a['hp'],24)
        self.assertTrue(self.state['board']['spent'][self.e['id']]['move'])

    def test_far_enemy_spends_one_move_within_speed_and_waits(self):
        self.e.update(x=15,y=0,speed=3)
        with patch('engine.dice') as dice:self.act('turn');dice.assert_not_called()
        self.assertEqual(self.a['hp'],30);self.assertLess(self.e['x'],15)
        self.assertGreaterEqual(self.e['x'],12)
        self.assertNotIn('standard',self.state['board']['spent'][self.e['id']])

    def test_blocked_route_pauses_without_spending_or_rolling(self):
        self.e.update(x=5,y=0)
        self.state['board']['terrain']={f'2,{y}':'wall' for y in range(20)}
        with patch('engine.dice') as dice:self.act('turn');dice.assert_not_called()
        self.assertEqual(self.e['x'],5);self.assertEqual(self.a['hp'],30)
        self.assertEqual(self.state['board']['autoPaused']['character'],self.e['id'])
        self.assertNotIn('move',self.state['board']['spent'][self.e['id']])

    def test_unknown_condition_cannot_be_bypassed_by_leaving_threatened_square(self):
        self.a['conditions']='invisible'
        with patch('engine.dice') as dice:self.act('turn');dice.assert_not_called()
        self.assertIn('autoPaused',self.state['board']);self.assertEqual(self.e['x'],1)

    def test_missing_profile_pauses_and_host_can_take_control(self):
        self.e.pop('meleeProfile')
        self.act('turn');self.assertIn('autoPaused',self.state['board'])
        self.act('automation',enabled=False)
        self.assertFalse(self.state['board']['autoEnemies']);self.assertNotIn('autoPaused',self.state['board'])
        before=copy.deepcopy(self.state)
        with self.assertRaises(PermissionError):
            apply_action(self.state,{'type':'automation','enabled':True},GUEST)
        self.assertEqual(self.state,before)

    def test_resuming_after_clearing_obstacle_runs_remaining_turn(self):
        self.state['board']['terrain']['0,1']='wall'
        self.act('turn');self.assertIn('autoPaused',self.state['board'])
        self.state['board']['terrain'].clear()
        with patch('engine.dice',side_effect=[[12],[4]]):self.act('automation',enabled=True)
        self.assertEqual(self.a['hp'],24);self.assertNotIn('autoPaused',self.state['board'])

    def test_manual_attack_is_not_repeated_when_automation_resumes(self):
        board=self.state['board'];board['turn']=1;board['spent'][self.e['id']]={'standard':True}
        with patch('engine.dice') as dice:self.act('automation',enabled=True);dice.assert_not_called()
        self.assertEqual(self.a['hp'],30);self.assertEqual(board['turn'],0)

    def test_incapacitated_enemy_attacks_once_then_falls_unconscious(self):
        self.e['hp']=0
        with patch('engine.dice',side_effect=[[12],[4]]):self.act('turn')
        self.assertEqual(self.e['hp'],-1);self.assertEqual(self.a['hp'],24)

    def test_no_conscious_players_stops_without_an_infinite_loop(self):
        self.a['hp']=-1
        with patch('engine.dice') as dice:self.act('turn');dice.assert_not_called()
        self.assertIn('autoPaused',self.state['board']);self.assertEqual(self.state['board']['round'],1)

    def test_downed_player_is_stabilized_and_skipped_when_another_player_can_act(self):
        ally=copy.deepcopy(self.a);ally.update(id='ally',name='Luis',x=4,y=4)
        self.state['characters'].append(ally)
        board=self.state['board'];board['order'].append({'id':'ally','roll':1,'modifier':0});board['turn']=2
        self.a['hp']=-2;self.e['hp']=-12
        with patch('engine.dice',return_value=[20]) as dice:self.act('turn')
        self.assertTrue(self.a['stable']);self.assertEqual(self.a['hp'],-2)
        self.assertEqual(board['order'][board['turn']]['id'],'ally');self.assertEqual(dice.call_count,1)

    def test_legacy_combat_requires_restart_before_enabling(self):
        self.state['board'].pop('acted')
        with self.assertRaisesRegex(ValueError,'Reinicia'):self.act('automation',enabled=True)

    def test_route_avoids_occupied_cells_and_matches_movement_validator(self):
        self.e.update(x=6,y=0)
        blocker=copy.deepcopy(self.e);blocker.update(id='blocker',x=4,y=0)
        self.state['characters'].append(blocker)
        decision=tactics.plan(self.state,self.e)
        self.assertNotIn([4,0],decision['path'])
        self.state['board']['turn']=1
        self.act('move',character=self.e['id'],path=decision['path'],acknowledge=True)
        self.assertTrue(combat.adjacent(self.e,self.a))

    def test_difficult_terrain_and_alternating_diagonals_respect_budget(self):
        self.e.update(x=5,y=5,speed=3)
        self.state['board']['terrain']={f'{x},{y}':'difficult' for x in range(20) for y in range(20)}
        decision=tactics.plan(self.state,self.e)
        self.assertEqual(len(decision['path']),1)
        self.state['board']['turn']=1
        self.act('move',character=self.e['id'],path=decision['path'],acknowledge=True)
        self.assertNotEqual((self.e['x'],self.e['y']),(5,5))

    def test_consecutive_enemies_each_act_once_before_control_returns_to_player(self):
        second=copy.deepcopy(self.e);second.update(id='second-enemy',name='Guardia',x=0,y=1)
        self.state['characters'].append(second)
        self.state['board']['order'].append({'id':second['id'],'roll':1,'modifier':0})
        with patch('engine.dice',side_effect=[[12],[4],[12],[4]]) as dice:self.act('turn')
        self.assertEqual(self.a['hp'],18);self.assertEqual(dice.call_count,4)
        board=self.state['board'];self.assertEqual(board['turn'],0);self.assertEqual(board['round'],2)
        attacks=[m['combat'] for m in self.state['messages'] if 'combat' in m]
        self.assertEqual([a['attacker'] for a in attacks],[self.e['id'],second['id']])

    def test_enemies_stop_when_last_player_falls_and_do_not_execute_them(self):
        self.a['hp']=5
        second=copy.deepcopy(self.e);second.update(id='second-enemy',x=0,y=1)
        self.state['characters'].append(second)
        self.state['board']['order'].append({'id':second['id'],'roll':1,'modifier':0})
        with patch('engine.dice',side_effect=[[12],[4]]) as dice:self.act('turn')
        self.assertEqual(self.a['hp'],-1);self.assertEqual(dice.call_count,2)
        self.assertIn('autoPaused',self.state['board'])
        self.assertNotIn('standard',self.state['board']['spent'].get(second['id'],{}))

    def test_incapacitated_enemy_does_not_move_and_attack_in_same_turn(self):
        self.e.update(x=5,y=0,hp=0)
        with patch('engine.dice') as dice:self.act('turn');dice.assert_not_called()
        self.assertEqual((self.e['x'],self.e['y']),(5,0));self.assertEqual(self.a['hp'],30)


if __name__=='__main__':unittest.main()
