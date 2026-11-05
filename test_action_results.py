import copy
import json
import unittest
from unittest.mock import Mock,patch
from rule_pack_runtime import RulePack,RulePackError
from test_rule_pack_runtime import document
import rule_pack_campaign as campaign
import rule_pack_director as director
import test_rule_pack_narrative as fixture
from test_rule_pack_objectives import goal


class ActionResultTests(unittest.TestCase):
    def test_final_results_include_unchanged_values_and_follow_triggers(self):
        data=document('original-staged-results-example')
        data['actions']['explore']['resultFields']=['success','energy','exhausted']
        pack=RulePack(data);sheet,_=pack.create_character('ana',physical={'aptitude':[1]})
        sheet,_=pack.advance_character(sheet,'training',{'role':'cronista','focus':1},'ana')
        for energy in [2,1,0]:
            sheet,trace=pack.execute(sheet,'explore',{},'ana',physical={'pool':[3,4]})
            self.assertEqual(trace['results'],{'success':True,'energy':energy,'exhausted':energy==0})
            if energy<2:self.assertNotIn('success',trace['changes'])

    def test_result_metadata_requires_existing_unique_fields_and_capability(self):
        for values in [[],['missing'],['success','success'],['success']*17]:
            data=document('original-staged-results-example');data['actions']['explore']['resultFields']=values
            with self.assertRaises(RulePackError):RulePack(data)
        data=document('original-staged-results-example');data['requires'].remove('action-results')
        with self.assertRaises(RulePackError):RulePack(data)


class ResolutionFactTests(unittest.TestCase):
    def setUp(self):
        self.me={'id':'ana','name':'Ana','host':True,'campaign':'facts-test'}
        self.state=campaign.execute_action(campaign.initial_state({}),{'type':'install_rule_pack','package':document('original-staged-results-example'),'policy':'provided-rules'},self.me)
        self.state=campaign.execute_action(self.state,{'type':'create_pack_sheet','name':'Aria','physical':{'aptitude':[1]}},self.me)
        self.character=self.state['characters'][0]['id']
        self.state=campaign.execute_action(self.state,{'type':'advance_pack_creation','character':self.character,'step':'training','inputs':{'role':'cronista','focus':1}},self.me)
        self.state=self.apply(self.state,'start_pack_adventure',fixture.reply(objectiveUpdates=[goal()]),character=self.character)

    def apply(self,state,kind,answer=None,**data):
        return campaign.execute_action(state,{'type':kind,**data},self.me,narrative_call=Mock(return_value=answer or fixture.reply()))

    def resolved(self,linked=False):
        answer=fixture.reply('explore',**({'objectiveCheck':{'objective':'farol','field':'success'}} if linked else {'objectiveCheck':{'objective':'','field':''}}))
        state=self.apply(self.state,'talk_pack_adventure',answer,character=self.character,text='Examino la marca.',mode='action')
        return self.apply(state,'resolve_pack_request',request=state['narrative']['pending']['id'],physical={'pool':[3,4]})

    def test_fact_contract_exposes_canonical_values_intent_and_actual_objective_status(self):
        for linked in [False,True]:
            state=self.resolved(linked);pack=campaign.runtime(state,self.me['campaign'])
            prepared=director.prepare(state,'continue',state['characters'][0],'','action',pack);request=prepared['request'];facts=request['verifiedResolution']
            self.assertEqual(request['contract'],director.FACTS_CONTRACT);self.assertEqual(request['rules']['actions'],{});self.assertEqual(request['history'],[])
            self.assertEqual(facts['declaredIntent'],'Examino la marca.');self.assertEqual(facts['outputs']['success'],{'label':'Éxito','value':True})
            self.assertEqual(facts['changes']['energy']['after'],2)
            self.assertEqual(facts['objectiveLink'],'completed' if linked else 'none')
            self.assertEqual(facts['objectiveStates'][0]['status'],'completed' if linked else 'open')
            self.assertEqual(facts['objectiveStates'][0]['completedByThisResult'],linked)
            self.assertEqual(facts['rolls'][0]['values'],[3,4]);self.assertIn('priorSummary',request)

    def test_partial_and_played_copies_replay_results_without_dice_and_reject_forgery(self):
        state=self.resolved(True)
        with patch('rule_pack_runtime.secrets.randbelow',side_effect=AssertionError('Result replay rolled')):
            copied=campaign.import_campaign(state,self.me|{'id':'eva'})
        self.assertEqual(copied['messages'][-1]['trace']['results'],{'success':True})
        bad=copy.deepcopy(state);bad['messages'][-1]['trace']['results']['success']=False
        with self.assertRaises(RulePackError):campaign.validate_restored(bad)
        bad=copy.deepcopy(state);bad['characters'][0]['creation']['steps'][0]['trace']['results']['talent']=6
        with self.assertRaises(RulePackError):campaign.validate_restored(bad)
        for value in (None,[],{},'wrong'):
            bad=copy.deepcopy(state);bad['messages'][-1]['trace']=value
            with self.assertRaises(RulePackError):campaign.validate_restored(bad)

    def test_legacy_contract_and_trace_shape_remain_unchanged(self):
        f=fixture.RulePackNarrativeTests();f.setUp();state=f.pending();state=f.apply(state,'resolve_pack_request',request=state['narrative']['pending']['id'],physical={'dice':[3,4]})
        prepared=director.prepare(state,'continue',state['characters'][0],'','action',campaign.runtime(state,f.me['campaign']))
        self.assertEqual(prepared['request']['contract'],director.CONTRACT);self.assertTrue(prepared['request']['rules']['actions'])
        self.assertIn('trace',prepared['request']['confirmedResult']);self.assertNotIn('results',prepared['request']['confirmedResult']['trace'])
