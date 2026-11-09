import copy
import unittest
import urllib.error
from unittest.mock import patch
import server
import adventure_modules as modules
import adventure_opening as opening
from firebase_store import FirestoreStore,Unavailable
import test_campaign_world_http as transport
from test_character_builder import choices


class AuthoredOpeningHTTPTests(unittest.TestCase):
    setUpClass=classmethod(transport.CampaignWorldHTTPTests.setUpClass.__func__)
    tearDownClass=classmethod(transport.CampaignWorldHTTPTests.tearDownClass.__func__)
    setUp=transport.CampaignWorldHTTPTests.setUp
    request=transport.CampaignWorldHTTPTests.request
    state=transport.CampaignWorldHTTPTests.state
    def action(self,kind,token=None,**fields):
        if 'openingContract' in fields and 'captureContract' not in fields:fields['captureContract']=opening.ACTION_CONTRACT
        return transport.CampaignWorldHTTPTests.action(self,kind,token,**fields)

    def hero(self):
        self.action('create_character',choices=choices());return self.state()['state']['characters'][0]['id']

    def test_no_provider_no_reservation_failed_commit_cold_retry_duplicate_and_private_copy(self):
        guest=self.request('/api/join',{'name':'Luis','invite':self.state()['invite']})['token']
        actor=self.hero();before=self.state();body={'id':'authored-opening','version':before['version'],'type':'start_adventure',
            'moduleId':'la-carta-perdida','openingContract':opening.CONTRACT,'worldMemoryContract':'structured-world-memory-1','captureContract':opening.ACTION_CONTRACT}
        with (patch.dict('os.environ',{'ANTHROPIC_API_KEY':''}),patch.object(server,'ai_reply',side_effect=AssertionError('Authored opening called provider')),
            patch.object(server.STORE,'begin_rule_preparation',side_effect=AssertionError('Authored opening reserved provider'))):
            with patch.object(server.STORE,'commit',side_effect=Unavailable('Interrupted authored intro')):
                with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/action',body)
            self.assertEqual(error.exception.code,503);error.exception.close()
        self.assertEqual(self.state(),before);previous=server.STORE
        if isinstance(previous,FirestoreStore):
            server.STORE=FirestoreStore.from_environment();server.STORE.prefix=previous.prefix
        try:
            with patch.dict('os.environ',{'ANTHROPIC_API_KEY':''}),patch.object(server,'ai_reply',side_effect=AssertionError('Retry called provider')):
                self.request('/api/action',body);after=self.state();self.assertTrue(self.request('/api/action',body)['duplicate']);self.assertEqual(self.state(),after)
            self.assertEqual(after['state']['characters'],before['state']['characters'])
            self.assertEqual(after['state']['moduleProgress']['discoveries'],[])
            self.assertEqual([m['text'] for m in after['state']['messages'] if m.get('kind')=='scene'],[modules.builtin('la-carta-perdida')['description']])
            self.assertFalse(any(m.get('kind')=='director' for m in after['state']['messages']))
            guest_state=self.state(guest)['state'];self.assertNotIn('directorMemory',guest_state);self.assertNotIn('adventureModule',guest_state)
            exported=self.request('/api/export',{});self.action('import',campaign=exported)
            self.assertEqual(self.state()['state']['preparedOpening'],after['state']['preparedOpening'])
            for opportunity in ('rastro','carta'):self.action('investigate',character=actor,opportunity=opportunity,method='take20')
            self.assertTrue(self.state()['state']['moduleProgress']['completed'])
            for case in ('receipt','marker','original'):
                altered=copy.deepcopy(self.request('/api/export',{}))
                if case=='receipt':del altered['state']['preparedOpening']
                elif case=='marker':altered['state']['messages']=[m for m in altered['state']['messages'] if 'preparedOpeningSha256' not in m]
                else:altered['state']['adventureModule']['preparation']='Otro original'
                baseline=self.state()
                with self.subTest(case=case),self.assertRaises(urllib.error.HTTPError) as error:self.action('import',campaign=altered)
                self.assertEqual(error.exception.code,400);error.exception.close();self.assertEqual(self.state(),baseline)
        finally:server.STORE=previous

    def test_invalid_or_generated_source_contract_is_rejected_before_provider(self):
        self.hero();before=self.state()
        for fields in ({'openingContract':'unknown','moduleId':'la-carta-perdida'},
                       {'openingContract':opening.CONTRACT},
                       {'openingContract':opening.CONTRACT,'moduleId':'la-carta-perdida','heal':100},
                       {'openingContract':opening.CONTRACT,'moduleId':'la-carta-perdida','structured':True},
                       {'openingContract':opening.CONTRACT,'moduleId':'la-carta-perdida','sourceText':'No convertir texto arbitrario sin IA.'}):
            with patch.object(server,'ai_reply',side_effect=AssertionError('Invalid authored contract called provider')):
                with self.subTest(fields=fields),self.assertRaises(urllib.error.HTTPError) as error:self.action('start_adventure',**fields)
                self.assertEqual(error.exception.code,400);error.exception.close();self.assertEqual(self.state(),before)

    def test_legacy_request_without_new_contract_preserves_real_director_path(self):
        self.hero();module=modules.builtin('la-carta-perdida')
        reply={'narration':'Presentación histórica del director.','proposals':[],
            'memory':{'summary':module['description'],'preparation':module['preparation']}}
        with patch.object(server,'ai_reply',return_value=reply) as provider:self.action('start_adventure',moduleId='la-carta-perdida')
        self.assertEqual(provider.call_count,1);after=self.state()['state']
        self.assertNotIn('preparedOpening',after);self.assertEqual(len([m for m in after['messages'] if m.get('kind')=='director']),1)

    def test_supplied_json_without_world_contract_can_start_without_provider(self):
        self.hero()
        with patch.dict('os.environ',{'ANTHROPIC_API_KEY':''}),patch.object(server,'ai_reply',side_effect=AssertionError('JSON intro called provider')):
            self.action('start_adventure',module=modules.builtin('la-carta-perdida'),openingContract=opening.CONTRACT)
        state=self.state()['state'];self.assertIn('preparedOpening',state);self.assertNotIn('campaignWorldView',state)
        self.assertEqual(state['moduleProgress']['discoveries'],[])

    def test_new_prepared_opening_keeps_an_existing_check_pending_and_does_not_call_provider(self):
        actor=self.hero();self.action('request_check',character=actor,checkKind='ability',key='str',dc=10,reason='Comprobación previa')
        before=self.state()
        with patch.object(server,'ai_reply',side_effect=AssertionError('Pending intro called provider')):
            with self.assertRaises(urllib.error.HTTPError) as error:self.action('start_adventure',moduleId='la-carta-perdida',openingContract=opening.CONTRACT)
        self.assertEqual(error.exception.code,400);error.exception.close();self.assertEqual(self.state(),before)

    def test_incomplete_protocol_pairs_never_fall_back_to_director(self):
        self.hero();before=self.state()
        pairs=({'captureContract':opening.ACTION_CONTRACT},
            {'openingContract':opening.CONTRACT,'captureContract':'pf-director-action-1'},
            {'openingContract':opening.CONTRACT})
        with patch.object(server,'ai_reply',side_effect=AssertionError('Incomplete no-IA protocol called provider')):
            for index,fields in enumerate(pairs):
                body={'id':'protocol-'+str(index),'version':before['version'],'type':'start_adventure','moduleId':'la-carta-perdida',**fields}
                with self.subTest(fields=fields),self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/action',body)
                self.assertEqual(error.exception.code,400);error.exception.close();self.assertEqual(self.state(),before)
