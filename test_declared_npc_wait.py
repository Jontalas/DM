import copy
import json
import unittest
from unittest.mock import patch
import claude_dm
import director_prepared_decisions as decisions
import engine
import legacy_director_attempt as legacy
import test_pf_npc_wait as fixture


class DeclaredNPCWaitTests(unittest.TestCase):
    def setUp(self):
        game=fixture.PreparedNPCWaitTests();game.setUp();self.state=game.state;self.me=game.me;self.actor=game.actor
        self.body={'type':'talk','kind':'action','character':self.actor,'text':'Espero junto a la guardiana a que despierte'}
        engine.apply_action(self.state,self.body,self.me)

    def test_only_current_wait_is_enumerated_and_matches_button_without_chained_investigation(self):
        before=copy.deepcopy(self.state)
        with patch('game_randomness.draw',side_effect=AssertionError('Availability rolled')):
            choices=decisions.declaration_available(self.state)
            self.assertEqual([a['id'] for a in choices['actions']],['wait-for-guard'])
            self.assertEqual(claude_dm.response_schema(self.state)['properties']['preparedDecision']['properties']['action']['enum'],['wait-for-guard'])
        self.assertEqual(self.state,before)
        value={'narration':'Permaneces junto a la guardiana.','proposals':[],'preparedDecision':{'action':'wait-for-guard'}}
        raw=json.dumps({'stop_reason':'end_turn','content':[{'type':'text','text':json.dumps(value)}]})
        self.assertEqual(claude_dm.parse_response(self.state,raw),value)
        with patch('game_randomness.draw',side_effect=[1,20]):decisions.apply(self.state,value['preparedDecision'],self.body,self.me)
        with patch('game_randomness.draw',side_effect=[1,20]):engine.apply_action(before,{'type':'wait_pf_npc_recovery'},self.me)
        for key in ('characters','board','pfEncounter','worldTime'):self.assertEqual(self.state[key],before[key])
        self.assertNotIn('pfContinuation',self.state)

    def test_foreign_owner_non_actions_and_old_capture_do_not_gain_wait_permission(self):
        baseline=copy.deepcopy(self.state)
        for case in ('dialogue','ooc','other-owner'):
            self.state=copy.deepcopy(baseline)
            if case=='other-owner':self.state['messages'][-1]['owner']='other'
            else:self.state['messages'][-1]['kind']=case
            with self.subTest(case=case):self.assertIsNone(decisions.declaration_available(self.state))
        self.state=baseline;prepared=legacy.prepare(self.state,self.body['text'],[]);old=copy.deepcopy(prepared['request']);old['context'].pop('preparedDecisions')
        self.assertEqual(legacy.request_sha(old),prepared['sha256'])
        payload={'kind':'report','value':{'narration':'Respuesta anterior.','proposals':[],'preparedDecision':{'action':'wait-for-guard'}},'latencyMs':0}
        with self.assertRaises(ValueError):legacy.restore({**prepared,'request':old},payload,legacy.SCHEME)

    def test_unassisted_risk_is_explicit_in_available_choice(self):
        self.state['characters'][1]['recoveryCare']['assisted']=False
        self.assertIn('perder PG y morir',decisions.declaration_available(self.state)['actions'][0]['label'])
