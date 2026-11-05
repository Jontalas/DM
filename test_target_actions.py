import copy
import unittest
from unittest.mock import Mock,patch
import rule_pack_campaign as campaign
import rule_pack_director as director
from rule_pack_runtime import RulePackError
import test_target_context as fixture


class TargetActionTests(unittest.TestCase):
    def setUp(self):
        f=fixture.AbstractTargetContextTests();f.setUp();self.state=f.state;self.me=f.me;self.cid=f.cid
        self.request={'type':'request_pack_target','character':self.cid,'action':'contest','target':'a'*24,'inputs':{}}

    def pending(self,state=None):
        provider=Mock(side_effect=AssertionError('Explicit selection called AI'))
        result=campaign.execute_action(self.state if state is None else state,self.request,self.me,narrative_call=provider)
        provider.assert_not_called();return result

    def resolve(self,state,physical=None):
        data={'type':'resolve_pack_request','request':state['narrative']['pending']['id']}
        if physical is not None:data['physical']=physical
        return campaign.execute_action(state,data,self.me)

    def test_select_then_resolve_commits_both_sheets_and_private_proof(self):
        pending=self.pending();campaign.validate_restored(pending)
        self.assertEqual(pending['characters'],self.state['characters']);self.assertEqual(pending['actors'],self.state['actors'])
        self.assertIn('targetBinding',pending['narrative']['pending'])
        result=self.resolve(pending,{'pool':[3,4]});campaign.validate_restored(result)
        self.assertEqual(result['characters'][0]['sheet']['fields']['energy'],2)
        self.assertEqual(result['actors'][0]['sheet']['fields']['energy'],1)
        self.assertEqual(len(result['targetResolutions']),1)
        public=campaign.public_view(result,self.me);self.assertNotIn('targetResolutions',public);self.assertNotIn('target',public['messages'][-1]['trace'])
        self.assertIsNotNone(result['narrative']['continuation']);self.assertIsNone(result['narrative']['pending'])

    def test_stale_or_changed_context_and_other_player_rejected_before_dice(self):
        pending=self.pending()
        for transform in [lambda s:s['actors'][0]['sheet'].update(revision=2),lambda s:s['actors'][0]['sheet']['fields'].update(visible=False),
            lambda s:s['actors'][0]['sheet']['fields'].update(scene='otro')]:
            bad=copy.deepcopy(pending);transform(bad)
            with patch('rule_pack_runtime.secrets.randbelow',side_effect=AssertionError('Rejected target rolled')):
                with self.assertRaises(RulePackError):self.resolve(bad)
        with self.assertRaises(PermissionError):campaign.execute_action(self.state,self.request,self.me|{'id':'eva'})
        with self.assertRaises(RulePackError):campaign.execute_action(self.state,self.request|{'target':'b'*24},self.me)

    def test_cancel_and_copy_pending_preserve_player_control(self):
        pending=self.pending();request=pending['narrative']['pending']['id']
        cancelled=campaign.execute_action(pending,{'type':'cancel_pack_request','request':request},self.me)
        self.assertEqual(cancelled['actors'],self.state['actors']);self.assertNotIn('targetResolutions',cancelled)
        copied=campaign.import_campaign(pending,self.me|{'id':'eva'})
        result=campaign.execute_action(copied,{'type':'resolve_pack_request','request':request,'physical':{'pool':[3,4]}},self.me|{'id':'eva'})
        campaign.validate_restored(result);self.assertEqual(result['actors'][0]['sheet']['owner'],'director:'+'a'*24)

    def test_new_reference_cannot_claim_an_unbound_adventure_objective(self):
        pending=self.pending();pending['narrative']['pending']['objectiveCheck']={'objective':'other','field':'success'}
        with self.assertRaises(RulePackError):self.resolve(pending,{'pool':[3,4]})

    def test_continuation_can_report_lost_contact_without_disclosing_private_location(self):
        data=fixture.abstract_document();data['actions']['contest']['effects'].append({'field':'scene','scope':'target','value':'otro'})
        with patch.object(fixture,'abstract_document',return_value=data):self.setUp()
        result=self.resolve(self.pending(),{'pool':[3,4]});campaign.validate_restored(result)
        request=director.prepare(result,'continue',result['characters'][0],'','action',campaign.runtime(result,self.me['campaign']))['request']
        self.assertEqual(request['verifiedResolution']['target']['context'],{'kind':'abstract-scene','sharedPerception':False})
        self.assertNotIn('scene',request['verifiedResolution']['target']['fields'])
        self.assertNotIn('"otro"',campaign._canonical(request))

    def test_target_changes_only_include_fields_shared_then_and_now(self):
        self.state['actors'][0]['publicFields']=['energy']
        result=self.resolve(self.pending(),{'pool':[3,4]})
        pack=campaign.runtime(result,self.me['campaign'])
        request=director.prepare(result,'continue',result['characters'][0],'','action',pack)['request']
        self.assertEqual(request['verifiedResolution']['target']['changes'],{'energy':{'label':'Energía','before':2,'after':1}})
        result['actors'][0]['publicFields']=[]
        request=director.prepare(result,'continue',result['characters'][0],'','action',pack)['request']
        self.assertEqual(request['verifiedResolution']['target']['changes'],{})
        result['actors'][0]['publicFields']=['energy'];result['targetResolutions'][0]['sharedFields']=[]
        request=director.prepare(result,'continue',result['characters'][0],'','action',pack)['request']
        self.assertEqual(request['verifiedResolution']['target']['changes'],{})
