"""Generic package integration through the existing transactional HTTP API."""
import copy
import unittest
import urllib.error
from unittest.mock import patch
import rulesets
import server
import test_server
import test_render
import rule_pack_campaign as campaign
from rule_pack_runtime import RulePackError
from test_rule_pack_runtime import document


class RulePackServerTests(unittest.TestCase):
    request=test_server.IntegrationTests.request
    state=test_server.IntegrationTests.state
    action=test_server.IntegrationTests.action

    @classmethod
    def setUpClass(cls):
        cls.registration=patch.dict(rulesets.SYSTEMS,{'rule-pack':{'id':'rule-pack','name':'Generic test','status':'experimental'}})
        cls.registration.start()
        test_server.IntegrationTests.setUpClass.__func__(cls)

    @classmethod
    def tearDownClass(cls):
        try:test_server.IntegrationTests.tearDownClass.__func__(cls)
        finally:cls.registration.stop()

    def setUp(self):
        self.token=self.request('/api/create',{'title':'Generic rules','player':'Ana','ruleset':'rule-pack'})['token']

    def rejected(self,operation,code=400):
        before=self.state()
        with self.assertRaises(urllib.error.HTTPError) as error:operation()
        self.assertEqual(error.exception.code,code);error.exception.close()
        self.assertEqual(self.state(),before)

    def install(self,**changes):
        data=document('original-pool-example');data.update(changes)
        self.action('install_rule_pack',package=data,policy='provided-rules')
        self.action('create_pack_sheet',name='Aria')
        return self.state()['state']['characters'][0]['id']

    def test_inspection_is_stateless_and_does_not_certify_sources(self):
        with patch.object(server,'repository',side_effect=AssertionError('Inspection accessed storage')):
            result=self.request('/api/rule-pack/inspect',{'package':document('original-pool-example')})
        self.assertEqual(result['sourceVerification'],'unverified')
        self.assertEqual(result['structuralValidation'],'passed')
        self.assertEqual(result['actions'],1)

    def test_draft_requires_explicit_policy_and_host_installation(self):
        guest=self.request('/api/join',{'name':'Luis','invite':self.state()['invite']})['token']
        data=document('original-pool-example')
        self.rejected(lambda:self.action('install_rule_pack',guest,package=data),403)
        self.rejected(lambda:self.action('install_rule_pack',package=data,policy='verified'))
        self.action('install_rule_pack',package=data)
        self.rejected(lambda:self.action('create_pack_sheet',name='Aria'))
        self.action('install_rule_pack',package=data,policy='provided-rules')
        self.action('create_pack_sheet',guest,name='Luis')
        self.assertEqual(self.state(guest)['state']['characters'][0]['owner'],self.state(guest)['me']['id'])

    def test_new_package_id_runs_atomic_actions_and_deduplicates_dice(self):
        cid=self.install(id='new-game-without-code')
        with patch('rule_pack_runtime.secrets.randbelow',return_value=3) as rng:
            body=self.action('run_pack_action',character=cid,action='attempt')
            self.assertEqual(rng.call_count,2)
            self.assertTrue(self.request('/api/action',body,self.token)['duplicate'])
            self.assertEqual(rng.call_count,2)
        for _ in range(2):self.action('run_pack_action',character=cid,action='attempt',physical={'pool':[3,4]})
        state=self.state()['state'];sheet=state['characters'][0]['sheet']
        self.assertEqual(sheet['fields']['energy'],0);self.assertTrue(sheet['fields']['exhausted'])
        self.assertEqual(state['messages'][-1]['trace']['triggers'][0]['id'],'exhaustion')
        self.rejected(lambda:self.action('run_pack_action',character=cid,action='attempt'))

    def test_ownership_and_package_replacement_reject_before_randomness(self):
        cid=self.install()
        guest=self.request('/api/join',{'name':'Luis','invite':self.state()['invite']})['token']
        with patch('rule_pack_runtime.secrets.randbelow',side_effect=AssertionError('Rejected operation rolled')):
            self.rejected(lambda:self.action('run_pack_action',guest,character=cid,action='attempt'),403)
            self.rejected(lambda:self.action('install_rule_pack',package=document('cairn-saves'),policy='provided-rules'))
            self.rejected(lambda:self.action('run_pack_action',character=cid,action='attempt',physical={'pool':[7,1]}))

    def test_import_replays_saved_results_and_rejects_tampering(self):
        cid=self.install()
        self.action('run_pack_action',character=cid,action='attempt',physical={'pool':[3,4]})
        exported=self.request('/api/export',{},self.token)
        other=self.request('/api/create',{'title':'Recovery','player':'Eva','ruleset':'rule-pack'})['token']
        with patch('rule_pack_runtime.secrets.randbelow',side_effect=AssertionError('Recovery rolled')):
            self.action('import',other,campaign=exported)
            recovered=self.state(other)
            self.assertEqual(recovered['state']['characters'][0]['owner'],recovered['me']['id'])
            self.assertEqual(recovered['state']['characters'][0]['sheet']['fields']['energy'],2)
            for mutate in ('sheet','trace','hash'):
                altered=copy.deepcopy(exported)
                if mutate=='sheet':altered['state']['characters'][0]['sheet']['fields']['energy']=3
                elif mutate=='trace':altered['state']['messages'][-1]['trace']['rolls']['pool']['values']=[1,1]
                else:altered['state']['package']['sha256']='0'*64
                self.rejected(lambda:self.action('import',campaign=altered))

    def test_malformed_recovery_and_cached_views_are_bounded(self):
        self.install();state=self.state()['state']
        raw={key:value for key,value in state.items() if key!='packageView'}
        for char in raw['characters']:char.pop('view',None)
        raw['characters'][0]['sheet']=[]
        with self.assertRaises(RulePackError):campaign.validate_restored(raw)
        with patch.object(campaign,'RulePack',side_effect=AssertionError('Cached read recompiled')):
            self.assertEqual(self.state()['state']['packageView']['sourceVerification'],'unverified')

    def test_history_limit_aborts_action_without_losing_existing_events(self):
        me={'id':'ana','name':'Ana','host':True,'campaign':'bounded-history'}
        original=campaign.initial_state({})
        original=campaign.execute_action(original,{'type':'install_rule_pack','package':document('original-pool-example'),'policy':'provided-rules'},me)
        original=campaign.execute_action(original,{'type':'create_pack_sheet','name':'Aria'},me)
        before=copy.deepcopy(original)
        with patch.object(campaign,'MAX_MESSAGES',2),patch('rule_pack_runtime.secrets.randbelow',side_effect=AssertionError('Full history rolled')):
            with self.assertRaises(RulePackError):
                campaign.execute_action(original,{'type':'run_pack_action','character':original['characters'][0]['id'],'action':'attempt'},me)
        self.assertEqual(original,before)


class RulePackWaitressTests(RulePackServerTests):
    @classmethod
    def setUpClass(cls):
        cls.registration=patch.dict(rulesets.SYSTEMS,{'rule-pack':{'id':'rule-pack','name':'Generic test','status':'experimental'}})
        cls.registration.start()
        test_render.ProductionServerTests.setUpClass.__func__(cls)

    @classmethod
    def tearDownClass(cls):
        try:test_render.ProductionServerTests.tearDownClass.__func__(cls)
        finally:cls.registration.stop()
