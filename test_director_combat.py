import copy
import hashlib
import json
import unittest
from unittest.mock import patch
import claude_dm
import combat
import director_combat
import engine
import legacy_director_attempt as legacy
import test_pf_ceasefire as fixture
from rule_pack_authoring import canonical


class DeclaredMeleeTests(unittest.TestCase):
    me={'id':'host','name':'Ana','host':True}

    def setUp(self):
        game=fixture.PreparedCeasefireTests();game.setUp()
        with patch('game_randomness.draw',side_effect=[20,1]),patch('game_randomness.initiative_tie',return_value=0):game.act('choose_pf_encounter',choice='combat')
        self.state=game.state;self.actor=game.actor;self.target=game.npc
        self.body={'type':'talk','kind':'action','text':'Ataco a la guardiana con mi espada','character':self.actor,'director':True}
        engine.apply_action(self.state,self.body,self.me)

    def parse(self,item,**extra):
        result={'narration':'La guardiana mantiene la espada preparada.','proposals':[],'meleeAttack':item,**extra}
        raw=json.dumps({'stop_reason':'end_turn','content':[{'type':'text','text':json.dumps(result)}]})
        return claude_dm.parse_response(self.state,raw)

    def test_preflight_does_not_draw_or_mutate_and_declared_attack_matches_button(self):
        before=copy.deepcopy(self.state)
        with patch('game_randomness.draw',side_effect=AssertionError('Preflight rolled')):
            choices=director_combat.declaration_available(self.state)
            schema=claude_dm.response_schema(self.state)
            context=claude_dm.build_context(self.state,self.body['text'],[])
            combat.attack_context(self.state,{'character':self.actor,'target':self.target},self.me)
        self.assertEqual(self.state,before);self.assertEqual(choices['targets'],[self.target])
        self.assertEqual(schema['properties']['meleeAttack']['properties']['target']['enum'],[self.target])
        self.assertEqual(context['availableMeleeAttack'],choices)
        result=self.parse({'target':self.target});button=copy.deepcopy(self.state)
        with patch('game_randomness.draw',side_effect=[12,1]):director_combat.apply(self.state,result['meleeAttack'],self.body,self.me)
        with patch('game_randomness.draw',side_effect=[12,1]):engine.apply_action(button,{'type':'attack','character':self.actor,'target':self.target},self.me)
        for key in ('characters','board','pfEncounter','worldTime'):self.assertEqual(self.state[key],button[key])
        self.assertEqual(self.state['messages'][-1]['combat'],button['messages'][-1]['combat'])
        self.assertEqual(self.state['characters'][1]['hp'],2)

    def test_unavailable_attacks_are_removed_before_any_dice(self):
        baseline=copy.deepcopy(self.state)
        for case in ('distance','condition','spent','turn','fallen','manual','pending','dialogue','ooc'):
            self.state=copy.deepcopy(baseline)
            if case=='distance':self.state['characters'][1]['x']=5
            elif case=='condition':self.state['characters'][0]['conditions']='Fatigado'
            elif case=='spent':self.state['board']['spent'][self.actor]={'standard':True}
            elif case=='turn':self.state['board']['turn']=1
            elif case=='fallen':self.state['characters'][1]['hp']=0
            elif case=='manual':self.state['characters'][0]['creation']['manualOverride']=True
            elif case=='pending':self.state['pending']=[{'reason':'Pendiente'}]
            else:self.state['messages'][-1]['kind']=case
            before=copy.deepcopy(self.state)
            with self.subTest(case=case),patch('game_randomness.draw',side_effect=AssertionError('Blocked attack rolled')):
                self.assertIsNone(director_combat.declaration_available(self.state))
                self.assertNotIn('meleeAttack',claude_dm.response_schema(self.state)['properties'])
                with self.assertRaises(ValueError):self.parse({'target':self.target})
            self.assertEqual(self.state,before)

    def test_extra_payload_combined_resolutions_and_other_owner_are_rejected(self):
        for item,extra in (({'target':self.target,'damage':99},{}),({'target':'other'},{}),
            ({'target':self.target},{'preparedDecision':{'action':'accept-truce'}})):
            with self.assertRaises(ValueError):self.parse(item,**extra)
        before=copy.deepcopy(self.state)
        with self.assertRaises(PermissionError):director_combat.apply(self.state,{'target':self.target},self.body,{**self.me,'id':'other'})
        self.assertEqual(self.state,before)
        for options in ({'rules':True},{'starting':True}):self.assertNotIn('meleeAttack',claude_dm.response_schema(self.state,**options)['properties'])

    def test_private_capture_restores_target_without_paid_retry_or_new_historical_action(self):
        prepared=legacy.prepare(self.state,self.body['text'],[])
        value={'narration':'La guardiana mantiene la espada preparada.','proposals':[],'meleeAttack':{'target':self.target}}
        with patch.object(claude_dm,'ai_reply',side_effect=AssertionError('Restore called provider')):
            self.assertEqual(legacy.restore(prepared,{'kind':'report','value':value,'latencyMs':0},legacy.SCHEME),value)
        previous=copy.deepcopy(prepared['request']);previous['context'].pop('availableMeleeAttack')
        previous['context'].pop('preparedDecisions',None)
        previous['context'].pop('availableTurnEnd',None)
        self.assertEqual(prepared['sha256'],hashlib.sha256(canonical(previous).encode()).hexdigest())
