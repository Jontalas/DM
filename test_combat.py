import copy
import unittest
from unittest.mock import patch

import combat
from engine import initial_state,apply_action

HOST={'id':'host','name':'Ana','host':True}
GUEST={'id':'guest','name':'Luis','host':False}


class CombatTests(unittest.TestCase):
    def setUp(self):
        self.state=initial_state({})
        for name,enemy in [('Aria',False),('Bandido',True)]:
            self.act('character',character={'name':name,'enemy':enemy,'abilities':[14,14,12,10,10,10],
                'hp':30,'maxHp':30,'ac':16,'attack':4,'damage':'1d6+2',
                'meleeProfile':{'flatAc':14,'criticalMin':19,'multiplier':2}})
        self.a,self.b=self.state['characters']
        self.act('combat')
        self.state['board'].update(order=[{'id':c['id'],'roll':10,'modifier':0} for c in (self.a,self.b)],turn=0,acted=[self.a['id']])

    def act(self,kind,**body):apply_action(self.state,{'type':kind,**body},HOST)
    def attack(self,roll=12,damage=None,confirmation=None,actor=HOST):
        physical={'attack':[roll]}
        if damage is not None:physical['damage']=damage
        if confirmation is not None:physical['confirmation']=[confirmation]
        apply_action(self.state,{'type':'attack','character':self.a['id'],'target':self.b['id'],'physical':physical},actor)
        return self.state['messages'][-1]['combat']

    def test_hit_applies_flat_footed_ac_damage_and_one_standard_action(self):
        result=self.attack(10,[4])
        self.assertTrue(result['hit']);self.assertTrue(result['flatFooted'])
        self.assertEqual(result['ac'],14);self.assertEqual(self.b['hp'],24)
        before=copy.deepcopy(self.state)
        with self.assertRaisesRegex(ValueError,'gastada'):self.attack(20,[6,6],20)
        self.assertEqual(self.state,before)

    def test_natural_one_misses_and_natural_twenty_requires_confirmation(self):
        self.a['attack']=100
        self.assertFalse(self.attack(1)['hit']);self.assertEqual(self.b['hp'],30)
        self.state['board']['spent']={};self.a['attack']=-100
        result=self.attack(20,[3],1)
        self.assertTrue(result['hit']);self.assertFalse(result['critical']);self.assertEqual(result['damage'],5)

    def test_confirmed_critical_rolls_damage_twice_and_multiplies_bonus(self):
        result=self.attack(19,[2,5],12)
        self.assertTrue(result['critical']);self.assertEqual(result['damage'],11)
        self.assertEqual(self.b['hp'],19)

    def test_threat_is_not_a_hit_when_below_armor(self):
        self.a['attack']=-10
        self.assertFalse(self.attack(19)['hit'])

    def test_invalid_physical_damage_does_not_mutate_state(self):
        for physical in ({'attack':[20]}, {'attack':[20],'confirmation':[21]},
                         {'attack':[12],'damage':[7]}, {'attack':[12],'damage':[]}):
            with self.subTest(physical=physical):
                before=copy.deepcopy(self.state)
                with self.assertRaises(ValueError):
                    self.act('attack',character=self.a['id'],target=self.b['id'],physical=physical)
                self.assertEqual(self.state,before)

    def test_illegal_attacks_do_not_roll_or_change_state(self):
        cases=[('range',lambda:self.b.update(x=5)),
               ('wall',lambda:self.state['board']['terrain'].update({'0,1':'wall'})),
               ('condition',lambda:self.b.update(conditions='invisible')),
               ('profile',lambda:self.b.pop('meleeProfile')),
               ('fallen',lambda:self.b.update(hp=-1)),
               ('turn',lambda:self.state['board'].update(turn=1)),
               ('legacy',lambda:self.state['board'].pop('acted'))]
        original=copy.deepcopy(self.state)
        for name,change in cases:
            with self.subTest(case=name):
                self.state=copy.deepcopy(original);self.a,self.b=self.state['characters'];change()
                before=copy.deepcopy(self.state)
                with patch('engine.dice') as roll:
                    with self.assertRaises(ValueError):self.act('attack',character=self.a['id'],target=self.b['id'])
                    roll.assert_not_called()
                self.assertEqual(self.state,before)

    def test_guest_cannot_control_host_or_supply_physical_dice(self):
        with self.assertRaises(PermissionError):self.attack(actor=GUEST)
        self.a['owner']=GUEST['id']
        with self.assertRaises(PermissionError):self.attack(actor=GUEST)
        with patch('engine.dice',side_effect=[[12],[4]]):
            apply_action(self.state,{'type':'attack','character':self.a['id'],'target':self.b['id']},GUEST)
        self.assertEqual(self.b['hp'],24)

    def test_flanking_bonus_and_regular_ac_after_first_turn(self):
        ally=copy.deepcopy(self.a);ally.update(id='ally',x=2,y=0)
        self.state['characters'].append(ally)
        self.state['board']['acted'].append(self.b['id'])
        result=self.attack(10,[3])
        self.assertTrue(result['flanking']);self.assertEqual(result['modifier'],6)
        self.assertEqual(result['ac'],16);self.assertTrue(result['hit'])

    def test_disabled_attacker_loses_one_hp_even_on_miss(self):
        self.a['hp']=0;self.attack(1)
        self.assertEqual(self.a['hp'],-1)
        with self.assertRaises(ValueError):self.act('move',character=self.a['id'],path=[[0,1]],acknowledge=True)

    def test_disabled_attacker_cannot_attack_after_moving(self):
        self.a['hp']=0;self.state['board']['spent'][self.a['id']]={'move':True}
        with self.assertRaises(ValueError):self.attack()

    def test_dying_stabilizes_on_natural_twenty_and_stays_stable(self):
        self.b['hp']=-10
        with patch('engine.dice',return_value=[20]):self.act('turn')
        self.assertTrue(self.b['stable']);self.assertEqual(self.b['hp'],-10)
        self.act('turn')
        with patch('engine.dice') as roll:self.act('turn');roll.assert_not_called()

    def test_failed_stabilization_loses_hp_and_respects_death_threshold(self):
        self.b['hp']=-11
        with patch('engine.dice',return_value=[2]):self.act('turn')
        self.assertEqual(self.b['hp'],-12);self.assertEqual(combat.health_status(self.b),'muerto')
        self.act('turn')
        with patch('engine.dice') as roll:self.act('turn');roll.assert_not_called()

    def test_damage_profiles_reject_unsupported_cases(self):
        for value in ('1d6-3','1d6+1d6','100d6','1d0','2d999','garbage'):
            with self.subTest(value=value),self.assertRaises(ValueError):combat.damage_spec(value)


if __name__=='__main__':unittest.main()
