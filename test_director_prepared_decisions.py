import copy
import hashlib
import json
import unittest
from unittest.mock import patch
import claude_dm
import director_prepared_decisions as decisions
import engine
import legacy_director_attempt as legacy
import pf_night_rest
import test_pf_truce_night as night_fixture
from rule_pack_authoring import canonical


class PreparedDecisionContractTests(unittest.TestCase):
    me={'id':'host','name':'Ana','host':True}

    def prepare(self,armor='chainshirt',zero=False,accept=True):
        fixture=night_fixture.TruceNightTests();fixture.prepare(armor);fixture.wound_guard()
        if zero:
            for _ in range(4):
                with patch('game_randomness.draw',side_effect=[19,1,4]):fixture.act('turn')
        if accept:fixture.act('accept_pf_ceasefire')
        self.state=fixture.state;self.actor=fixture.actor
        self.body={'type':'talk','kind':'action','character':self.actor,'text':'Elijo dormir esta noche','director':True}
        engine.apply_action(self.state,self.body,self.me)

    def parse(self,item,**extra):
        result={'narration':'El patio permanece tranquilo.','proposals':[],'preparedDecision':item,**extra}
        raw=json.dumps({'stop_reason':'end_turn','content':[{'type':'text','text':json.dumps(result)}]})
        return claude_dm.parse_response(self.state,raw)

    def test_zero_hp_explicit_sleep_uses_existing_receipt_and_does_not_continue_or_heal_guard(self):
        self.prepare(zero=True)
        choices=decisions.declaration_available(self.state)
        self.assertEqual([a['id'] for a in choices['actions']],['sleep-in-light-armor'])
        schema=claude_dm.response_schema(self.state)
        self.assertEqual(schema['properties']['preparedDecision']['properties']['action']['enum'],['sleep-in-light-armor'])
        result=self.parse({'action':'sleep-in-light-armor'})
        with patch('game_randomness.draw',side_effect=AssertionError('Declared sleep rolled')):
            decisions.apply(self.state,result['preparedDecision'],self.body,self.me)
        self.assertEqual([c['hp'] for c in self.state['characters']],[1,2]);self.assertNotIn('pfContinuation',self.state)
        pf_night_rest.validate_restored(self.state)

    def test_scale_plan_and_truce_are_distinct_available_decisions(self):
        self.prepare('scale')
        ids=[a['id'] for a in decisions.declaration_available(self.state)['actions']]
        self.assertEqual(ids,['sleep-after-removing-armor','investigate-courtyard'])
        self.body['text']='Me quito la cota, duermo sin ella y vuelvo a equiparla.'
        decisions.apply(self.state,{'action':'sleep-after-removing-armor'},self.body,self.me)
        self.assertEqual(self.state['pfNightRest']['result']['seconds'],29100)
        self.prepare(accept=False)
        self.assertEqual([a['id'] for a in decisions.declaration_available(self.state)['actions']],['accept-truce'])
        decisions.apply(self.state,{'action':'accept-truce'},self.body,self.me)
        self.assertFalse(self.state['board']['active']);self.assertNotIn('pfNightRest',self.state)

    def test_non_actions_combined_payload_unavailable_choices_and_other_owner_are_rejected(self):
        self.prepare();baseline=copy.deepcopy(self.state)
        for case in ('dialogue','ooc','extra','unavailable','combined','route'):
            self.state=copy.deepcopy(baseline);item={'action':'sleep-in-light-armor'};extra={}
            if case in ('dialogue','ooc'):self.state['messages'][-1]['kind']=case
            elif case=='extra':item['hp']=99
            elif case=='unavailable':item['action']='accept-truce'
            elif case=='combined':extra['checks']=[{'character':self.actor,'kind':'ability','key':'str','dc':10,'reason':'Fixture'}]
            else:extra['routeTravel']={'exit':'inventada'}
            before=copy.deepcopy(self.state)
            with self.subTest(case=case),self.assertRaises(ValueError):self.parse(item,**extra)
            self.assertEqual(self.state,before)
        self.state=copy.deepcopy(baseline)
        with self.assertRaises(PermissionError):decisions.apply(self.state,{'action':'sleep-in-light-armor'},self.body,{**self.me,'id':'other'})
        for options in ({'rules':True},{'starting':True}):self.assertNotIn('preparedDecision',claude_dm.response_schema(self.state,**options)['properties'])

    def test_capture_restores_only_the_recorded_choice_and_preserves_older_paid_key(self):
        self.prepare();prepared=legacy.prepare(self.state,self.body['text'],[])
        value={'narration':'El patio permanece tranquilo.','proposals':[],'preparedDecision':{'action':'sleep-in-light-armor'}}
        with patch.object(claude_dm,'ai_reply',side_effect=AssertionError('Restore called provider')):
            self.assertEqual(legacy.restore(prepared,{'kind':'report','value':value,'latencyMs':0},legacy.SCHEME),value)
        previous=copy.deepcopy(prepared['request']);previous['context'].pop('preparedDecisions')
        self.assertEqual(prepared['sha256'],hashlib.sha256(canonical(previous).encode()).hexdigest())
        original={'narration':'Respuesta histórica sin dormir.','proposals':[]}
        self.assertEqual(legacy.restore(prepared,{'kind':'report','value':original,'latencyMs':0},legacy.SCHEME),original)
