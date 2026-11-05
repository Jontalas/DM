import copy
import unittest
from unittest.mock import Mock,patch
import adventure_plan
import rule_pack_campaign as campaign
import rule_pack_director as director
from rule_pack_runtime import RulePack,RulePackError
from test_rule_pack_runtime import document
from test_rule_pack_narrative import reply
from test_rule_pack_objectives import goal


def plan_document():
    pack=RulePack(document('original-narrative-results-example'))
    source='Preparación propia CC0.\r\nLa marca señala el archivo.\r\nOtro secreto.'
    text='La marca señala el archivo.';start=source.index(text)
    return {'format':adventure_plan.FORMAT,'source':{'title':'El farol — ejemplo propio','text':source},
        'package':{'id':pack.id,'version':pack.version,'sha256':pack.digest},'objectives':[goal()],
        'discoveries':[{'id':'archivo','objective':'farol','field':'success','start':start,'end':start+len(text),'text':text}]}


class AdventurePlanTests(unittest.TestCase):
    def setUp(self):
        self.pack=RulePack(document('original-narrative-results-example'));self.plan=plan_document()
        self.me={'id':'ana','name':'Ana','host':True,'campaign':'adventure-plan'}
        self.state=campaign.execute_action(campaign.initial_state({}),{'type':'install_rule_pack','package':self.pack.document(),'policy':'provided-rules'},self.me)
        self.state=campaign.execute_action(self.state,{'type':'create_pack_sheet','name':'Aria'},self.me)
        self.cid=self.state['characters'][0]['id']

    def test_compile_exact_package_source_and_information_only(self):
        result=adventure_plan.compile_plan(self.plan,self.pack,'provided-adventure')
        self.assertEqual(result['source']['text'],self.plan['source']['text'])
        self.assertEqual(result['catalog']['definitions'],self.plan['discoveries'])
        original=copy.deepcopy(result);self.plan['objectives'][0]['title']='Cambiado'
        self.assertEqual(result,original)

    def test_plan_starts_with_one_call_and_no_technical_configuration(self):
        provider=Mock(return_value=reply())
        started=campaign.execute_action(self.state,{'type':'start_pack_adventure','character':self.cid,'plan':self.plan,'sourcePolicy':'provided-adventure'},self.me,narrative_call=provider)
        self.assertEqual(provider.call_count,1);prepared=provider.call_args.args[0]
        self.assertEqual(prepared['request']['contract'],director.PLAN_CONTRACT)
        self.assertEqual(prepared['request']['directorKnowledge']['objectives'][0]['id'],'farol')
        self.assertIn('farol',director.schema(prepared)['properties']['objectiveUpdates']['items']['properties']['id']['enum'])
        self.assertEqual(started['narrative']['discoveries']['receipts'],[]);campaign.validate_restored(started)
        pending=campaign.execute_action(started,{'type':'talk_pack_adventure','character':self.cid,'mode':'action','text':'Examino la marca.'},self.me,
            narrative_call=Mock(return_value=reply('intentar',objectiveCheck={'objective':'farol','field':'success'})))
        resolved=campaign.execute_action(pending,{'type':'resolve_pack_request','request':pending['narrative']['pending']['id'],'physical':{'dice':[3,4]}},self.me)
        self.assertEqual(campaign.public_view(resolved,self.me)['narrativeView']['discoveries'][0]['text'],self.plan['discoveries'][0]['text'])
        with patch('rule_pack_runtime.secrets.randbelow',side_effect=AssertionError('Copy rolled')):
            copied=campaign.import_campaign(resolved,self.me|{'id':'eva'})
        self.assertEqual(copied['narrative']['discoveries'],resolved['narrative']['discoveries'])

    def test_bad_preparation_is_rejected_before_inference(self):
        bad_plans=[]
        for transform in [lambda p:p['package'].update(sha256='0'*64),lambda p:p['discoveries'][0].update(text='Inventado'),
            lambda p:p['discoveries'][0].update(field='energy'),lambda p:p['objectives'][0].update(known=False),
            lambda p:p.update(rewards=['gold']),lambda p:p.update(format='other')]:
            value=copy.deepcopy(self.plan);transform(value);bad_plans.append(value)
        for plan in bad_plans:
            provider=Mock(side_effect=AssertionError('Invalid preparation called AI'))
            with self.assertRaises(RulePackError):campaign.execute_action(self.state,{'type':'start_pack_adventure','character':self.cid,'plan':plan,'sourcePolicy':'provided-adventure'},self.me,narrative_call=provider)
            provider.assert_not_called()
