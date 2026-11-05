import copy
import unittest
from unittest.mock import Mock,patch
import adventure_plan
import objective_targets
import rule_pack_campaign as campaign
import rule_pack_director as director
from rule_pack_runtime import RulePack,RulePackError
from test_adventure_actor_plan import actor_plan_document
from test_rule_pack_narrative import reply
from test_target_context import abstract_document


def target_plan_document():
    plan=actor_plan_document();plan['format']=adventure_plan.TARGETS_FORMAT
    plan['npcPreparation']['npcs'][1].update(known=True,public='Otra participante de la escena abstracta.')
    plan['objectiveTargets']=[{'objective':'farol','action':'contest','field':'success','npc':'arda','inputs':{}}]
    return plan


class TargetObjectivePlanTests(unittest.TestCase):
    def setUp(self):
        self.me={'id':'ana','name':'Ana','host':True,'campaign':'target-goal'};self.plan=target_plan_document()
        state=campaign.execute_action(campaign.initial_state({}),{'type':'install_rule_pack','package':abstract_document(),'policy':'provided-rules'},self.me)
        state=campaign.execute_action(state,{'type':'create_pack_sheet','name':'Aria','physical':{'aptitude':[1]}},self.me);self.cid=state['characters'][0]['id']
        self.before=campaign.execute_action(state,{'type':'advance_pack_creation','character':self.cid,'step':'training','inputs':{'role':'cronista','focus':1}},self.me)
        self.provider=Mock(return_value=reply())
        self.state=campaign.execute_action(self.before,{'type':'start_pack_adventure','character':self.cid,'plan':self.plan,'sourcePolicy':'provided-adventure'},self.me,narrative_call=self.provider)

    def pending(self,state=None,target='a'*24):
        return campaign.execute_action(self.state if state is None else state,{'type':'request_pack_target','character':self.cid,'action':'contest','target':target,'inputs':{}},self.me)

    def resolve(self,pending,dice):
        return campaign.execute_action(pending,{'type':'resolve_pack_request','request':pending['narrative']['pending']['id'],'physical':{'pool':dice}},self.me)

    def test_correct_target_completes_and_reveals_in_the_two_sheet_commit(self):
        self.assertEqual(self.provider.call_args.args[0]['request']['contract'],director.TARGET_OBJECTIVES_CONTRACT)
        campaign.validate_restored(self.state);pending=self.pending()
        self.assertEqual(pending['narrative']['pending']['objectiveCheck'],{'objective':'farol','field':'success'})
        self.assertEqual(len(pending['narrative']['pending']['discoveryBindings']),1)
        result=self.resolve(pending,[3,4]);campaign.validate_restored(result)
        self.assertEqual(result['narrative']['objectives'][0]['status'],'completed')
        self.assertEqual(result['actors'][0]['sheet']['fields']['energy'],1)
        public=campaign.public_view(result,self.me)
        self.assertEqual(len(public['narrativeView']['discoveries']),1)
        self.assertNotIn('objectiveTargets',public['narrativeView'])
        with patch('rule_pack_runtime.secrets.randbelow',side_effect=AssertionError('Copy rolled')):
            copy_state=campaign.import_campaign(result,self.me|{'id':'eva'})
        campaign.validate_restored(copy_state);self.assertEqual(copy_state['actors'],result['actors'])

    def test_wrong_target_success_does_not_close_goal_then_correct_target_does(self):
        pending=self.pending(target='b'*24);self.assertNotIn('objectiveCheck',pending['narrative']['pending'])
        wrong=self.resolve(pending,[3,4]);campaign.validate_restored(wrong)
        self.assertEqual(wrong['narrative']['objectives'][0]['status'],'open')
        self.assertEqual(wrong['narrative']['discoveries']['receipts'],[])
        continued=campaign.execute_action(wrong,{'type':'continue_pack_adventure'},self.me,narrative_call=Mock(return_value=reply()))
        result=self.resolve(self.pending(continued),[3,4]);campaign.validate_restored(result)
        self.assertEqual(result['narrative']['objectives'][0]['status'],'completed')

    def test_failure_keeps_goal_open_and_cannot_drop_or_replace_bound_goal(self):
        pending=self.pending();failed=self.resolve(pending,[1,1]);campaign.validate_restored(failed)
        self.assertFalse(failed['messages'][-1]['objectiveResolution']['met'])
        self.assertEqual(failed['narrative']['objectives'][0]['status'],'open')
        for transform in [lambda p:p.pop('objectiveCheck'),lambda p:p['objectiveCheck'].update(field='exhausted'),
            lambda p:p.update(discoveryBindings=[])]:
            value=copy.deepcopy(pending);transform(value['narrative']['pending'])
            with patch('rule_pack_runtime.secrets.randbelow',side_effect=AssertionError('Invalid binding rolled')):
                with self.assertRaises(RulePackError):self.resolve(value,[3,4])

    def test_routed_goal_is_excluded_from_individual_proposals(self):
        request=director.prepare(self.state,'talk',self.state['characters'][0],'Examino la marca.','action',campaign.runtime(self.state,self.me['campaign']))
        self.assertIn('farol',request['request']['targetObjectiveIds'])
        schema=director.schema(request)
        if 'objectiveCheck' in schema['properties']:
            self.assertNotIn('farol',schema['properties']['objectiveCheck']['properties']['objective']['enum'])
        with self.assertRaises(RulePackError):director.validate_reply(request,reply('explore',objectiveCheck={'objective':'farol','field':'success'}))
        with self.assertRaises(RulePackError):objective_targets.check_request(self.state,{'action':'explore','inputs':{},'objectiveCheck':{'objective':'farol','field':'success'}})

    def test_missing_tampered_or_retrospective_preparation_is_rejected(self):
        result=self.resolve(self.pending(),[3,4])
        for transform in [lambda s:s['narrative'].pop('objectiveTargets'),
            lambda s:s['narrative']['objectiveTargets']['routes'][0].update(npc='sombra'),
            lambda s:s['messages'][-1]['targetRef'].update(npc='sombra'),
            lambda s:s['actors'][0].update(introducedAt=len(s['messages'])),
            lambda s:s['actors'][0].update(introducedAt='invalid')]:
            value=copy.deepcopy(result);transform(value)
            with self.assertRaises(RulePackError):campaign.validate_restored(value)

    def test_invalid_route_is_rejected_before_opening_inference(self):
        plan=copy.deepcopy(self.plan);plan['objectiveTargets'][0]['npc']='missing'
        provider=Mock(side_effect=AssertionError('Invalid route called provider'))
        with self.assertRaises(RulePackError):campaign.execute_action(self.before,{'type':'start_pack_adventure','character':self.cid,
            'plan':plan,'sourcePolicy':'provided-adventure'},self.me,narrative_call=provider)
        provider.assert_not_called()

    def test_editing_a_prepared_choice_does_not_complete_the_original_goal(self):
        data=abstract_document();data['actions']['contest']['inputs']={'approach':{'type':'text','label':'Enfoque propio',
            'maxLength':20,'options':['cauto','directo'],'default':'cauto'}}
        pack=RulePack(data);plan=copy.deepcopy(self.plan)
        plan['package']={'id':pack.id,'version':pack.version,'sha256':pack.digest}
        plan['npcPreparation']['package']=copy.deepcopy(plan['package'])
        plan['objectiveTargets'][0]['inputs']={'approach':'cauto'}
        before=campaign.execute_action(campaign.initial_state({}),{'type':'install_rule_pack','package':data,'policy':'provided-rules'},self.me)
        before=campaign.execute_action(before,{'type':'create_pack_sheet','name':'Aria','physical':{'aptitude':[1]}},self.me);cid=before['characters'][0]['id']
        before=campaign.execute_action(before,{'type':'advance_pack_creation','character':cid,'step':'training','inputs':{'role':'cronista','focus':1}},self.me)
        started=campaign.execute_action(before,{'type':'start_pack_adventure','character':cid,'plan':plan,'sourcePolicy':'provided-adventure'},self.me,narrative_call=Mock(return_value=reply()))
        pending=campaign.execute_action(started,{'type':'request_pack_target','character':cid,'action':'contest','target':'a'*24,'inputs':{}},self.me)
        result=campaign.execute_action(pending,{'type':'resolve_pack_request','request':pending['narrative']['pending']['id'],
            'inputs':{'approach':'directo'},'physical':{'pool':[3,4]}},self.me)
        campaign.validate_restored(result)
        self.assertTrue(result['messages'][-1]['trace']['results']['success'])
        self.assertFalse(result['messages'][-1]['objectiveResolution']['matchedInputs'])
        self.assertEqual(result['narrative']['objectives'][0]['status'],'open')
        self.assertEqual(result['narrative']['discoveries']['receipts'],[])
