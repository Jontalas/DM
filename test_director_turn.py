import copy
import json
import unittest
from unittest.mock import patch
import claude_dm
import director_turn
import engine
import legacy_director_attempt as legacy
import rule_preparation_attempt as attempts
import test_director_combat as melee_fixture


class DeclaredTurnTests(unittest.TestCase):
    def setUp(self):
        fixture=melee_fixture.DeclaredMeleeTests();fixture.setUp();self.state=fixture.state;self.actor=fixture.actor;self.me=fixture.me
        self.body={'type':'talk','kind':'action','text':'Termino mi turno','character':self.actor}
        engine.apply_action(self.state,self.body,self.me)

    def parse(self,item=None,**extra):
        result={'narration':'Cedes el turno sin realizar otra acción.','proposals':[],'turnEnd':item or {'character':self.actor},**extra}
        raw=json.dumps({'stop_reason':'end_turn','content':[{'type':'text','text':json.dumps(result)}]})
        return claude_dm.parse_response(self.state,raw)

    def test_readonly_availability_and_turn_matches_button_with_npc_automation(self):
        before=copy.deepcopy(self.state)
        with patch('game_randomness.draw',side_effect=AssertionError('Availability drew dice')):
            self.assertEqual(director_turn.declaration_available(self.state),{'character':self.actor})
            self.assertEqual(claude_dm.response_schema(self.state)['properties']['turnEnd']['properties']['character']['enum'],[self.actor])
            self.assertEqual(claude_dm.build_context(self.state,self.body['text'],[])['availableTurnEnd'],{'character':self.actor})
        self.assertEqual(self.state,before);self.parse()
        with patch('game_randomness.draw',side_effect=[18,1]):director_turn.apply(self.state,{'character':self.actor},self.body,self.me)
        with patch('game_randomness.draw',side_effect=[18,1]):engine.apply_action(before,{'type':'turn'},self.me)
        for key in ('characters','board','pfEncounter','worldTime'):self.assertEqual(self.state[key],before[key])
        self.assertEqual(self.state['board']['round'],2);self.assertEqual(self.state['board']['order'][self.state['board']['turn']]['id'],self.actor)
        self.assertLess(self.state['characters'][0]['hp'],16)

    def test_only_explicit_owner_action_in_supported_turn_is_exposed(self):
        baseline=copy.deepcopy(self.state)
        for case in ('dialogue','ooc','other-owner','paused','manual','terrain','fallen','pending','other-turn','manual-npc'):
            self.state=copy.deepcopy(baseline)
            if case in ('dialogue','ooc'):self.state['messages'][-1]['kind']=case
            elif case=='other-owner':self.state['messages'][-1]['owner']='other'
            elif case=='paused':self.state['board']['autoPaused']={'reason':'Pending'}
            elif case=='manual':self.state['board']['autoEnemies']=False
            elif case=='terrain':self.state['board']['terrain']={'1,1':'wall'}
            elif case=='fallen':self.state['characters'][0]['hp']=-1
            elif case=='pending':self.state['pending']=[{'reason':'Pending'}]
            elif case=='other-turn':self.state['board']['turn']=1
            elif case=='manual-npc':self.state['characters'][1]['npcCreation']['manualOverride']=True
            with self.subTest(case=case):
                self.assertIsNone(director_turn.declaration_available(self.state));self.assertNotIn('turnEnd',claude_dm.response_schema(self.state)['properties'])
                with self.assertRaises(ValueError):self.parse()

    def test_spent_standard_does_not_choose_ending_turn_and_combinations_are_rejected(self):
        self.state['board']['spent'][self.actor]={'standard':True}
        self.assertEqual(director_turn.declaration_available(self.state),{'character':self.actor})
        for extra in ({'meleeAttack':{'target':self.state['characters'][1]['id']}},{'checks':[{'character':self.actor,'kind':'ability','key':'strength','dc':10,'reason':'Check'}]}):
            with self.assertRaises(ValueError):self.parse(**extra)
        with self.assertRaises(ValueError):self.parse({'character':self.actor,'rounds':5})
        with self.assertRaises(PermissionError):director_turn.apply(self.state,{'character':self.actor},self.body,{**self.me,'id':'other'})
        for options in ({'rules':True},{'starting':True}):self.assertNotIn('turnEnd',claude_dm.response_schema(self.state,**options)['properties'])

    def test_old_capture_key_and_capabilities_are_preserved(self):
        prepared=legacy.prepare(self.state,self.body['text'],[]);old=copy.deepcopy(prepared['captureRequest']);old['context'].pop('availableTurnEnd')
        self.assertEqual(legacy.request_sha(old),prepared['sha256']);self.assertTrue(attempts.inputs_match(old,prepared['captureRequest'],legacy.SCHEME,legacy.SCHEME))
        payload={'kind':'report','value':{'narration':'Texto histórico.','proposals':[],'turnEnd':{'character':self.actor}},'latencyMs':0}
        with self.assertRaises(ValueError):legacy.restore({**prepared,'request':old},payload,legacy.SCHEME)
