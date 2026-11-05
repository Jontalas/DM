import copy
import unittest
from rule_pack_runtime import RulePack,RulePackError
from test_rule_pack_runtime import document


class StagedCreationTests(unittest.TestCase):
    def setUp(self):self.pack=RulePack(document('original-staged-creation-example'))

    def test_later_decision_uses_confirmed_roll_and_final_sheet_becomes_playable(self):
        sheet,trace=self.pack.create_character('ana',physical={'aptitude':[1]})
        self.assertEqual(trace['rolls']['aptitude']['values'],[1]);self.assertFalse(self.pack.ready(sheet))
        self.assertEqual(self.pack.creation_progress(sheet),{'complete':False,'completed':1,'total':2,'next':'training'})
        self.assertEqual(self.pack.creation_inputs(sheet)['focus']['max'],1)
        before=copy.deepcopy(sheet)
        with self.assertRaises(RulePackError):self.pack.advance_character(sheet,'training',{'role':'cronista','focus':2},'ana')
        self.assertEqual(sheet,before)
        final,_=self.pack.advance_character(sheet,'training',{'role':'vigía','focus':1},'ana')
        self.assertTrue(self.pack.ready(final));self.assertEqual(final['fields']['talent'],2)
        played,_=self.pack.execute(final,'explore',{},'ana',physical={'pool':[3,4]})
        self.assertEqual(played['fields']['energy'],2)

    def test_stage_order_replay_ownership_and_gameplay_before_completion_are_rejected(self):
        sheet,_=self.pack.create_character('ana',physical={'aptitude':[4]})
        for action,creating in [('aptitude',True),('explore',False),('training',False)]:
            with self.assertRaises(RulePackError):self.pack.execute(sheet,action,{},'ana',creating=creating)
        with self.assertRaises(PermissionError):self.pack.advance_character(sheet,'training',{'role':'cronista','focus':0},'other')
        final,_=self.pack.advance_character(sheet,'training',{'role':'cronista','focus':2},'ana')
        with self.assertRaises(RulePackError):self.pack.advance_character(final,'training',{'role':'cronista','focus':0},'ana')

    def test_definition_requires_unique_owner_steps_and_explicit_capability(self):
        for mutation in ('duplicate','unknown','host','capability','both'):
            data=document('original-staged-creation-example')
            if mutation=='duplicate':data['creation']['steps']=['aptitude','aptitude']
            elif mutation=='unknown':data['creation']['steps']=['absent']
            elif mutation=='host':data['actions']['training']['permission']='host'
            elif mutation=='capability':data['requires'].remove('staged-character-creation')
            else:data['creation']['action']='aptitude'
            with self.assertRaises(RulePackError):RulePack(data)


class StagedCampaignTests(unittest.TestCase):
    def setUp(self):
        import rule_pack_campaign as campaign
        self.campaign=campaign;self.me={'id':'ana','name':'Ana','host':True,'campaign':'staged-test'}
        self.state=campaign.execute_action(campaign.initial_state({}),{'type':'install_rule_pack','package':document('original-staged-creation-example'),'policy':'provided-rules'},self.me)
        self.state=campaign.execute_action(self.state,{'type':'create_pack_sheet','name':'Aria','physical':{'aptitude':[1]}},self.me)
        self.character=self.state['characters'][0]['id']

    def test_partial_copy_resumes_without_reroll_and_gameplay_waits_for_completion(self):
        from unittest.mock import Mock,patch
        c=self.campaign
        with patch('rule_pack_runtime.secrets.randbelow',side_effect=AssertionError('Copy rolled')):
            copied=c.import_campaign(self.state,self.me|{'id':'eva'})
        self.assertEqual(copied['characters'][0]['sheet']['fields']['talent'],1)
        provider=Mock(side_effect=AssertionError('Partial character called director'))
        with self.assertRaises(RulePackError):c.execute_action(self.state,{'type':'start_pack_adventure','character':self.character},self.me,narrative_call=provider)
        import adventure_source
        with_source=copy.deepcopy(self.state);with_source['adventureSourceRef']=adventure_source.reference(adventure_source.create('Propia','Preparación privada.','provided-adventure'))
        loader=Mock(side_effect=AssertionError('Partial character fetched source'))
        with self.assertRaises(RulePackError):c.execute_action(with_source,{'type':'start_pack_adventure','character':self.character},self.me,narrative_call=provider,source_loader=loader)
        loader.assert_not_called()
        with self.assertRaises(PermissionError):c.execute_action(self.state,{'type':'advance_pack_creation','character':self.character,'step':'training','inputs':{'role':'cronista','focus':1}},self.me|{'id':'other'})
        final=c.execute_action(copied,{'type':'advance_pack_creation','character':self.character,'step':'training','inputs':{'role':'cronista','focus':1}},self.me|{'id':'eva'})
        c.validate_restored(final);self.assertEqual(final['characters'][0]['sheet']['fields']['talent'],2)
        self.assertTrue(c.public_view(final,self.me)['characters'][0]['creationProgress']['complete'])
        for mutate in ('roll','inputs','order','revision'):
            bad=copy.deepcopy(final);record=bad['characters'][0]
            if mutate=='roll':record['creation']['steps'][0]['trace']['rolls']['aptitude']['values']=[6]
            elif mutate=='inputs':record['creation']['steps'][1]['inputs']['focus']=2
            elif mutate=='order':record['creation']['steps'].reverse()
            else:record['sheet']['revision']=1
            with self.assertRaises(RulePackError):c.validate_restored(bad)


class StagedAuthoringTests(unittest.TestCase):
    def test_candidate_examples_must_finish_all_creation_steps_in_order(self):
        import json
        import rule_pack_authoring as authoring
        import test_rule_pack_authoring as fixture
        data=document('original-staged-creation-example');raw=fixture.request()
        raw['identity']={key:data[key] for key in ('id','name','edition','version')};raw['license']=data['license']
        raw['document']['pages'][0]['text']=data['sources'][0]['locator'];prepared=authoring.prepare_input(raw)
        data['sources']=prepared['sources']
        for group in ('fields','actions','triggers'):
            for spec in data[group].values():spec['sources']=[prepared['sources'][0]['id']]
        steps=[{'action':'aptitude','inputs':{},'physical':{'aptitude':[1]}},
               {'action':'training','inputs':{'role':'cronista','focus':1},'physical':{}},
               {'action':'explore','inputs':{},'physical':{'pool':[3,4]}}]
        result={'status':'candidate','packageJson':json.dumps(data),'issues':[],
            'examples':[{'name':'Creación completa antes de explorar','stepsJson':json.dumps(steps),'expectedJson':json.dumps({'talent':2,'energy':2,'success':True})}]}
        self.assertEqual(authoring.validate_reply(prepared,result)['status'],'candidate')
        for invalid in [steps[:1],[steps[1],steps[0]],steps[::2]]:
            bad=copy.deepcopy(result);bad['examples'][0]['stepsJson']=json.dumps(invalid)
            with self.assertRaises(RulePackError):authoring.validate_reply(prepared,bad)
