import copy
import unittest
from unittest.mock import patch
import checks
from engine import initial_state,apply_action

HOST={'id':'host','name':'Ana','host':True}
PLAYER={'id':'player','name':'Luis','host':False}
OTHER={'id':'other','name':'Otro','host':False}


class CharacterChecksTests(unittest.TestCase):
    def setUp(self):
        self.state=initial_state({})
        self.act('character',character={'name':'Aria','owner':'player','abilities':[9,16,12,10,14,8],
            'saves':[4,6,2],'skillTotals':[{'name':'Percepción','total':8}]})
        self.c=self.state['characters'][0]

    def act(self,kind,me=HOST,**data):apply_action(self.state,{'type':kind,**data},me)
    def request(self,kind='save',key='fort',dc=15):
        self.act('request_check',character=self.c['id'],checkKind=kind,key=key,dc=dc,reason='Resistir el peligro')
        return self.state['pending'][-1]['check']['id']

    def test_ability_floor_and_prepared_totals_not_double_counted(self):
        self.assertEqual(checks.modifier(self.c,'ability','str')[0],-1)
        self.assertEqual(checks.modifier(self.c,'save','ref')[0],6)
        self.assertEqual(checks.modifier(self.c,'skill','Percepción')[0],8)
        with self.assertRaises(ValueError):checks.modifier(self.c,'skill','Sigilo')

    def test_naturals_apply_only_to_saves_and_equal_dc_succeeds(self):
        self.assertFalse(checks.resolve(self.c,'save','fort',1,0)['success'])
        self.assertTrue(checks.resolve(self.c,'save','fort',20,999)['success'])
        self.assertTrue(checks.resolve(self.c,'skill','Percepción',1,9)['success'])
        self.assertFalse(checks.resolve(self.c,'ability','str',20,20)['success'])
        self.assertIsNone(checks.resolve(self.c,'ability','dex',10)['success'])

    def test_request_owner_rolls_uses_stored_dc_and_removes_once(self):
        request=self.request()
        with patch('engine.dice',return_value=[11]):
            self.act('check',me=PLAYER,request=request,dc=1000,modifier=1000,character='forged')
        result=self.state['messages'][-1]['check']
        self.assertEqual((result['total'],result['dc'],result['success']),(15,15,True))
        self.assertEqual(self.state['pending'],[])
        with patch('engine.dice') as dice:
            with self.assertRaises(ValueError):self.act('check',me=PLAYER,request=request)
            dice.assert_not_called()

    def test_permissions_and_physical_dice_are_checked_before_rng(self):
        request=self.request()
        with patch('engine.dice') as dice:
            for actor,body in [(OTHER,{'request':request}),(PLAYER,{'request':request,'physical':[20]}),
                (OTHER,{'character':self.c['id'],'checkKind':'ability','key':'str'})]:
                with self.assertRaises(PermissionError):self.act('check',me=actor,**body)
            dice.assert_not_called()
        with self.assertRaises(PermissionError):self.act('request_check',me=PLAYER,character=self.c['id'],checkKind='save',key='fort',dc=10,reason='X')
        with self.assertRaises(PermissionError):self.act('cancel_check',me=PLAYER,request=request)
        self.assertEqual(len(self.state['pending']),1)

    def test_cancellation_does_not_remove_unrelated_manual_pending(self):
        self.state['pending'].append({'reason':'Manual','source':'Test'})
        with self.assertRaises(ValueError):self.act('cancel_check')
        request=self.request();self.act('cancel_check',request=request)
        self.assertEqual(len(self.state['pending']),1)

    def test_invalid_data_and_conditions_do_not_consume_request_or_dice(self):
        request=self.request();before=copy.deepcopy(self.state)
        with self.assertRaises(ValueError):self.act('check',request=request,physical=[21])
        self.assertEqual(self.state,before)
        for field,value in [('conditions','Asustado'),('hp',-1)]:
            previous=self.c[field];self.c[field]=value
            with patch('engine.dice') as dice:
                with self.assertRaises(ValueError):self.act('check',me=PLAYER,request=request)
                dice.assert_not_called()
            self.c[field]=previous
        for dc in [-1,1001,True,'15']:
            with self.assertRaises(ValueError):self.request(dc=dc)

    def test_legacy_sheets_and_skill_edit_roundtrip(self):
        payload=copy.deepcopy(self.c);payload.pop('skillTotals')
        self.act('character',character=payload)
        self.assertEqual(self.state['characters'][0]['skillTotals'],[{'name':'Percepción','total':8}])
        self.act('character',character={'name':'Antiguo'})
        self.assertEqual(self.state['characters'][1]['skillTotals'],[])
        for skills in [[{'name':'A','total':True}],[{'name':'A','total':1},{'name':'a','total':2}],['invalid']]:
            with self.assertRaises(ValueError):checks.skill_totals(skills)

    def test_free_sheet_roll_has_no_effect_on_hp_resources_or_action_budget(self):
        before=copy.deepcopy(self.c);budget=copy.deepcopy(self.state['board'])
        self.act('check',character=self.c['id'],checkKind='skill',key='Percepción',physical=[12])
        self.assertEqual(self.state['messages'][-1]['check']['total'],20)
        self.assertEqual(self.c,before);self.assertEqual(self.state['board'],budget)


if __name__=='__main__':unittest.main()
