import copy
import unittest
from unittest.mock import Mock,patch
import adventure_plan
import adventure_actors
import rule_pack_campaign as campaign
import rule_pack_director as director
from rule_pack_runtime import RulePack,RulePackError
from test_target_context import abstract_document
from test_adventure_plan import plan_document
from test_rule_pack_narrative import reply
from test_rule_pack_world import npc


def actor_plan_document():
    pack=RulePack(abstract_document());plan=plan_document()
    plan.update(format=adventure_plan.ACTORS_FORMAT,package={'id':pack.id,'version':pack.version,'sha256':pack.digest})
    plan['npcPreparation']={'format':adventure_actors.FORMAT,'package':copy.deepcopy(plan['package']),
        'npcs':[npc(),npc('sombra',known=False,public='')],
        'actors':[{'id':identifier,'npc':reference,'profile':'support','stages':[{'inputs':{},'physical':{}}],
            'publicFields':['energy','exhausted']} for identifier,reference in [('a'*24,'arda'),('b'*24,'sombra')]]}
    return plan


class AdventureActorPlanTests(unittest.TestCase):
    def setUp(self):
        self.me={'id':'ana','name':'Ana','host':True,'campaign':'actor-plan'};self.plan=actor_plan_document()
        state=campaign.execute_action(campaign.initial_state({}),{'type':'install_rule_pack','package':abstract_document(),'policy':'provided-rules'},self.me)
        state=campaign.execute_action(state,{'type':'create_pack_sheet','name':'Aria','physical':{'aptitude':[1]}},self.me)
        self.cid=state['characters'][0]['id']
        self.state=campaign.execute_action(state,{'type':'advance_pack_creation','character':self.cid,'step':'training',
            'inputs':{'role':'cronista','focus':1}},self.me)

    def start(self,plan=None,provider=None):
        return campaign.execute_action(self.state,{'type':'start_pack_adventure','character':self.cid,
            'plan':self.plan if plan is None else plan,'sourcePolicy':'provided-adventure'},self.me,
            narrative_call=provider if provider is not None else Mock(return_value=reply()))

    def test_one_opening_creates_ready_npcs_with_private_fields_and_no_extra_dice(self):
        provider=Mock(return_value=reply());before=copy.deepcopy(self.state)
        with patch('rule_pack_runtime.secrets.randbelow',side_effect=AssertionError('Plan rolled new dice')):
            started=self.start(provider=provider)
        provider.assert_called_once();prepared=provider.call_args.args[0]['request']
        self.assertEqual(prepared['contract'],director.ACTORS_PLAN_CONTRACT)
        self.assertEqual(len(prepared['directorKnowledge']['npcs']),2)
        self.assertNotIn('sheet',str(prepared['directorKnowledge']['npcs']))
        self.assertEqual(self.state,before);campaign.validate_restored(started)
        public=campaign.public_view(started,self.me)
        self.assertNotIn('actors',public);self.assertEqual(len(public['actorViews']),1)
        self.assertEqual(public['targetOptions']['byCharacter'][self.cid]['scene:visible'],['a'*24])
        self.assertEqual(started['actors'][0]['introducedAt'],len(started['messages'])-1)

    def test_imported_plan_immediately_allows_explicit_target_and_copy(self):
        started=self.start()
        pending=campaign.execute_action(started,{'type':'request_pack_target','character':self.cid,'action':'contest','target':'a'*24,'inputs':{}},self.me)
        resolved=campaign.execute_action(pending,{'type':'resolve_pack_request','request':pending['narrative']['pending']['id'],
            'physical':{'pool':[3,4]}},self.me)
        self.assertEqual(resolved['actors'][0]['sheet']['fields']['energy'],1)
        self.assertEqual(resolved['narrative']['objectives'][0]['status'],'open')
        with patch('rule_pack_runtime.secrets.randbelow',side_effect=AssertionError('Copy rolled')):
            copied=campaign.import_campaign(resolved,self.me|{'id':'eva'})
        self.assertEqual(copied['actors'],resolved['actors']);campaign.validate_restored(copied)

    def test_invalid_npc_preparation_and_player_collision_reject_before_provider(self):
        for transform in [lambda p:p['npcPreparation']['package'].update(sha256='0'*64),
            lambda p:p['npcPreparation']['actors'][0].update(id=self.cid),
            lambda p:p['npcPreparation']['actors'][0].update(stages=[]),
            lambda p:p['npcPreparation']['actors'][0].update(sheet={}),
            lambda p:p['npcPreparation']['npcs'][1].update(public='Leaked')]:
            plan=copy.deepcopy(self.plan);transform(plan);provider=Mock(side_effect=AssertionError('Invalid plan called provider'))
            with self.assertRaises(RulePackError):self.start(plan,provider)
            provider.assert_not_called()

    def test_legacy_plan_context_remains_unchanged(self):
        legacy=copy.deepcopy(self.plan);legacy.pop('npcPreparation');legacy['format']=adventure_plan.FORMAT
        provider=Mock(return_value=reply());started=self.start(legacy,provider)
        self.assertEqual(provider.call_args.args[0]['request']['contract'],director.PLAN_CONTRACT)
        self.assertNotIn('providedActors',provider.call_args.args[0]['request'])
        self.assertNotIn('actors',started)
