"""Generic package integration through the existing transactional HTTP API."""
import copy
import unittest
import urllib.error
import urllib.request
import secrets
import os
from unittest.mock import patch
import rulesets
import server
from firebase_store import Conflict,Unavailable
import test_server
import test_render
import rule_pack_campaign as campaign
from rule_pack_runtime import RulePackError
from test_rule_pack_runtime import document
import rule_pack_authoring as authoring
import test_rule_pack_authoring as authoring_fixture
import rule_pack_director as pack_director
from test_rule_pack_narrative import reply as narrative_reply
from test_rule_pack_composition import blocks as composition_blocks


class RulePackServerTests(unittest.TestCase):
    request=test_server.IntegrationTests.request
    state=test_server.IntegrationTests.state
    action=test_server.IntegrationTests.action

    @classmethod
    def setUpClass(cls):
        cls.environment=patch.dict(os.environ,{'ANTHROPIC_API_KEY':'fixture-never-sent'});cls.environment.start()
        cls.registration=patch.dict(rulesets.SYSTEMS,{'rule-pack':{'id':'rule-pack','name':'Generic test','status':'experimental'}})
        cls.registration.start()
        test_server.IntegrationTests.setUpClass.__func__(cls)

    @classmethod
    def tearDownClass(cls):
        try:test_server.IntegrationTests.tearDownClass.__func__(cls)
        finally:cls.registration.stop();cls.environment.stop()

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

    def test_pdf_library_modules_are_local_versioned_and_cacheable(self):
        # Reproduce the Windows large-response regression without retrying failures.
        for asset,mime in [('build/pdf.min.mjs','text/javascript'),('wasm/jbig2.wasm','application/wasm')]*3:
            with urllib.request.urlopen(self.url+'/vendor/pdfjs-6.5.438/'+asset) as response:
                self.assertEqual(response.headers.get_content_type(),mime)
                self.assertIn('immutable',response.headers['Cache-Control']);self.assertGreater(len(response.read()),1000)
        with urllib.request.urlopen(self.url+'/rule-source-pdf.js') as response:self.assertEqual(response.headers['Cache-Control'],'no-cache')

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
        with patch('action_randomness.hmac.digest',return_value=(3).to_bytes(32,'big')) as rng:
            body=self.action('run_pack_action',character=cid,action='attempt')
            self.assertEqual(rng.call_count,2)
            self.assertTrue(self.request('/api/action',body,self.token)['duplicate'])
            self.assertEqual(rng.call_count,2)
        for _ in range(2):self.action('run_pack_action',character=cid,action='attempt',physical={'pool':[3,4]})
        state=self.state()['state'];sheet=state['characters'][0]['sheet']
        self.assertEqual(sheet['fields']['energy'],0);self.assertTrue(sheet['fields']['exhausted'])
        self.assertEqual(state['messages'][-1]['trace']['triggers'][0]['id'],'exhaustion')
        self.rejected(lambda:self.action('run_pack_action',character=cid,action='attempt'))

    def test_generated_dice_survive_failed_commit_without_process_cache(self):
        cid=self.install();before=self.state();me=before['me']
        body={'id':secrets.token_hex(12),'version':before['version'],'type':'run_pack_action','character':cid,'action':'attempt'}
        captured=[]
        def fail(*args,**kwargs):
            captured.append(copy.deepcopy(args[5]));raise Unavailable('Failed before commit')
        with patch.object(server.STORE,'commit',side_effect=fail):
            with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/action',body,self.token)
            self.assertEqual(error.exception.code,503);error.exception.close()
        self.assertEqual(self.state(),before)
        # No RNG object or stream survives between HTTP requests. Reconnect the
        # Firestore client too, proving the seed is durable rather than cached.
        old=server.STORE
        from firebase_store import FirestoreStore
        if isinstance(old,FirestoreStore):
            server.STORE=FirestoreStore.from_environment();server.STORE.prefix=old.prefix
        try:
            self.request('/api/action',body,self.token)
            result=self.state()['state']
            self.assertEqual(result['characters'][0]['sheet'],captured[0]['characters'][0]['sheet'])
            self.assertEqual(result['messages'][-1]['trace'],captured[0]['messages'][-1]['trace'])
            self.assertTrue(self.request('/api/action',body,self.token)['duplicate'])
            with self.assertRaises(Conflict):
                server.STORE.action_random_seed(me['campaign'],body['id'],me['id'],server.fingerprint(body),body['version'])
        finally:server.STORE=old

    def test_random_seed_binding_failure_and_physical_dice_cost(self):
        cid=self.install();store=server.STORE;me=self.state()['me']
        with patch.object(store,'action_random_seed',side_effect=Unavailable('Cannot reserve')):
            before=self.state()
            with patch('action_randomness.hmac.digest',side_effect=AssertionError('Rolled without durable seed')):
                with self.assertRaises(urllib.error.HTTPError) as error:self.action('run_pack_action',character=cid,action='attempt')
                self.assertEqual(error.exception.code,503);error.exception.close()
            self.assertEqual(self.state(),before)
            self.action('run_pack_action',character=cid,action='attempt',physical={'pool':[3,4]})
        seed=store.action_random_seed(me['campaign'],'reserved',me['id'],'request-a',1)
        self.assertEqual(seed,store.action_random_seed(me['campaign'],'reserved',me['id'],'request-a',1))
        for actor,signature,version in [('other','request-a',1),(me['id'],'request-b',1),(me['id'],'request-a',2)]:
            with self.assertRaises(Conflict):store.action_random_seed(me['campaign'],'reserved',actor,signature,version)

    def test_creation_and_narrative_dice_recover_before_confirmation(self):
        def recover(body):
            before=self.state();staged=[]
            def fail(*args,**kwargs):
                staged.append(copy.deepcopy(args[5]));raise Unavailable('Interrupted persistence')
            with patch.object(server.STORE,'commit',side_effect=fail):
                with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/action',body,self.token)
                self.assertEqual(error.exception.code,503);error.exception.close()
            self.assertEqual(self.state(),before)
            self.request('/api/action',body,self.token)
            after=self.state()['state']
            self.assertEqual(after['characters'][0]['sheet'],staged[0]['characters'][0]['sheet'])
            return after,staged[0]
        self.action('install_rule_pack',package=document('original-creation-example'),policy='provided-rules')
        recover({'id':secrets.token_hex(12),'version':self.state()['version'],'type':'create_pack_sheet','name':'Aria','inputs':{'role':'cronista','focus':2}})
        self.token=self.request('/api/create',{'title':'Narrative recovery','player':'Ana','ruleset':'rule-pack'})['token']
        self.action('install_rule_pack',package=document('live-lantern-example'),policy='provided-rules')
        self.action('create_pack_sheet',name='Aria');cid=self.state()['state']['characters'][0]['id']
        with patch.object(pack_director,'propose',return_value=narrative_reply()) as provider:
            self.action('start_pack_adventure',character=cid)
            provider.return_value=narrative_reply('intentar')
            self.action('talk_pack_adventure',character=cid,text='Intento investigar.',mode='action')
        pending=self.state()['state']['narrativeView']['pending']
        after,staged=recover({'id':secrets.token_hex(12),'version':self.state()['version'],'type':'resolve_pack_request','request':pending['id']})
        self.assertEqual(after['messages'][-1]['trace'],staged['messages'][-1]['trace'])
        self.assertEqual(after['narrativeView']['continuation'],{'character':cid,'message':len(after['messages'])-1})

    def test_npc_memory_is_committed_with_narration_and_filtered_for_every_player(self):
        from test_rule_pack_world import npc
        cid=self.install()
        guest=self.request('/api/join',{'name':'Luis','invite':self.state()['invite']})['token']
        with patch.object(pack_director,'propose',return_value=narrative_reply(npcUpdates=[npc(),npc('sombra',name='PRIVATE-NAME',known=False,public='')])) as provider:
            self.action('start_pack_adventure',character=cid)
            provider.return_value=narrative_reply()
            self.action('talk_pack_adventure',character=cid,text='Saludo a Arda.',mode='dialogue')
            self.assertEqual(len(provider.call_args.args[0]['request']['directorKnowledge']['npcs']),2)
        for token in [self.token,guest]:
            view=self.state(token)['state']
            self.assertEqual(view['narrativeView']['npcs'],[{'id':'arda','name':'Arda','public':'Archivera junto al farol.'}])
            self.assertNotIn('PRIVATE-NPC',str(view));self.assertNotIn('PRIVATE-NAME',str(view))
        exported=self.request('/api/export',{},self.token)
        self.assertEqual(len(exported['state']['narrative']['npcs']),2)

    def test_objective_and_dice_commit_together_and_recover_the_same_request(self):
        from test_rule_pack_objectives import goal
        self.action('install_rule_pack',package=document('live-lantern-example'),policy='provided-rules')
        self.action('create_pack_sheet',name='Aria');cid=self.state()['state']['characters'][0]['id']
        guest=self.request('/api/join',{'name':'Luis','invite':self.state()['invite']})['token']
        with patch.object(pack_director,'propose',return_value=narrative_reply(objectiveUpdates=[goal(),goal('oculto',known=False,title='PRIVATE-TITLE')])) as provider:
            self.action('start_pack_adventure',character=cid)
            provider.return_value=narrative_reply('intentar',objectiveCheck={'objective':'farol','field':'success'})
            self.action('talk_pack_adventure',character=cid,text='Investigo la marca del farol.',mode='action')
        before=self.state();pending=before['state']['narrativeView']['pending']
        self.rejected(lambda:self.action('resolve_pack_request',guest,request=pending['id']),403)
        body={'id':secrets.token_hex(12),'version':before['version'],'type':'resolve_pack_request','request':pending['id'],'physical':{'dice':[3,4]}}
        with patch.object(server.STORE,'commit',side_effect=Unavailable('Interrupted before atomic commit')):
            with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/action',body,self.token)
            self.assertEqual(error.exception.code,503);error.exception.close()
        self.assertEqual(self.state(),before)
        self.request('/api/action',body,self.token);after=self.state()
        self.assertEqual(after['state']['narrativeView']['objectives'][0]['status'],'completed')
        self.assertEqual(after['state']['characters'][0]['sheet']['fields']['energy'],2)
        self.assertTrue(self.request('/api/action',body,self.token)['duplicate'])
        for token in [self.token,guest]:
            view=self.state(token)['state'];self.assertEqual(len(view['narrativeView']['objectives']),1)
            self.assertNotIn('PRIVATE-GOAL',str(view));self.assertNotIn('PRIVATE-TITLE',str(view))
        exported=self.request('/api/export',{},self.token)
        self.action('import',campaign=exported)
        self.assertEqual(self.state()['state']['narrativeView']['objectives'],after['state']['narrativeView']['objectives'])

    def test_adventure_source_is_private_separate_and_not_loaded_for_view_or_dice(self):
        self.action('install_rule_pack',package=document('live-lantern-example'),policy='provided-rules')
        self.action('create_pack_sheet',name='Aria');cid=self.state()['state']['characters'][0]['id']
        guest=self.request('/api/join',{'name':'Luis','invite':self.state()['invite']})['token']
        text='PRIVATE-ADVENTURE-SOURCE: Arda guarda una carta secreta.\r\nEl archivo queda junto al farol.'
        with patch.object(pack_director,'propose',return_value=narrative_reply()) as provider:
            self.action('start_pack_adventure',character=cid,sourceTitle='Aventura privada',sourceText=text,sourcePolicy='provided-adventure')
            self.assertEqual(provider.call_args.args[0]['request']['directorKnowledge']['adventureSource']['fragments'][0]['text'],text)
            me=self.state()['me'];stored=server.STORE.load(me['campaign'])[1]
            self.assertIsNone(stored['adventureSource']);self.assertIsNotNone(stored['adventureSourceRef'])
            with patch.object(server.STORE,'load_adventure_source',side_effect=AssertionError('View/OOC fetched adventure source')):
                for token in [self.token,guest]:self.assertNotIn('PRIVATE-ADVENTURE-SOURCE',str(self.state(token)))
                self.action('talk_pack_adventure',character=cid,mode='ooc',text='Pausa.')
                self.rejected(lambda:self.action('talk_pack_adventure',guest,character=cid,mode='dialogue',text='Hola'),403)
            provider.return_value=narrative_reply('intentar')
            self.action('talk_pack_adventure',character=cid,mode='action',text='Investigo la carta de Arda.')
            self.assertLessEqual(sum(len(f['text'].encode()) for f in provider.call_args.args[0]['request']['directorKnowledge']['adventureSource']['fragments']),8000)
            pending=self.state()['state']['narrativeView']['pending']
            with patch.object(server.STORE,'load_adventure_source',side_effect=Unavailable('Source unavailable')):
                self.action('resolve_pack_request',request=pending['id'],physical={'dice':[3,4]})
                calls=provider.call_count
                self.rejected(lambda:self.action('continue_pack_adventure'),503)
                self.assertEqual(provider.call_count,calls)
        exported=self.request('/api/export',{},self.token)
        self.assertEqual(exported['state']['adventureSource']['text'],text);self.assertIsNone(exported['state']['adventureSourceRef'])
        other=self.request('/api/create',{'title':'Source copy','player':'Eva','ruleset':'rule-pack'})['token']
        self.action('import',other,campaign=exported)
        self.assertEqual(self.request('/api/export',{},other)['state']['adventureSource'],exported['state']['adventureSource'])

    def test_start_source_recovers_after_failed_commit_without_repeating_provider(self):
        cid=self.install();before=self.state()
        body={'id':secrets.token_hex(12),'version':before['version'],'type':'start_pack_adventure','character':cid,
            'sourceTitle':'Aventura propia','sourceText':'PRIVATE-ADVENTURE-SOURCE: Arda espera junto al farol.','sourcePolicy':'provided-adventure'}
        with patch.object(pack_director,'propose',return_value=narrative_reply()) as provider:
            with patch.object(server.STORE,'commit',side_effect=Unavailable('Commit failed after response')):
                with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/action',body,self.token)
                self.assertEqual(error.exception.code,503);error.exception.close()
            self.assertEqual(self.state(),before)
            self.request('/api/action',body,self.token);self.assertEqual(provider.call_count,1)
            self.assertTrue(self.request('/api/action',body,self.token)['duplicate'])
        self.assertEqual(self.request('/api/export',{},self.token)['state']['adventureSource']['text'],body['sourceText'])

    def test_data_defined_creation_validates_choices_deduplicates_dice_and_recovers(self):
        self.action('install_rule_pack',package=document('original-creation-example'),policy='provided-rules')
        with patch('action_randomness.hmac.digest',return_value=(3).to_bytes(32,'big')) as rng:
            self.rejected(lambda:self.action('create_pack_sheet',name='Aria',inputs={'role':'vigía','focus':2}))
            self.assertEqual(rng.call_count,0)
            body=self.action('create_pack_sheet',name='Aria',inputs={'role':'cronista','focus':2})
            self.assertTrue(self.request('/api/action',body,self.token)['duplicate']);self.assertEqual(rng.call_count,1)
            state=self.state()['state'];character=state['characters'][0]
            self.assertEqual(character['sheet']['fields']['talent'],6)
            self.assertEqual(character['creation']['trace']['rolls']['aptitude']['values'],[4])
            self.rejected(lambda:self.action('run_pack_action',character=character['id'],action='generate',inputs={'role':'cronista'}))
            self.assertEqual(rng.call_count,1)
        exported=self.request('/api/export',{},self.token)
        other=self.request('/api/create',{'title':'Creation recovery','player':'Eva','ruleset':'rule-pack'})['token']
        with patch('action_randomness.hmac.digest',side_effect=AssertionError('Import generated another character')):
            self.action('import',other,campaign=exported)
        recovered=self.state(other)['state']['characters'][0]
        self.assertEqual(recovered['sheet']['fields'],character['sheet']['fields'])
        self.assertEqual(recovered['creation'],character['creation'])

    def test_generic_director_requests_engine_dice_and_continues_from_confirmed_state(self):
        self.action('install_rule_pack',package=document('live-lantern-example'),policy='provided-rules')
        self.action('create_pack_sheet',name='Aria');character=self.state()['state']['characters'][0]['id']
        guest=self.request('/api/join',{'name':'Luis','invite':self.state()['invite']})['token']
        with patch.object(pack_director,'propose',return_value=narrative_reply()) as provider:
            self.rejected(lambda:self.action('start_pack_adventure',guest,character=character),403)
            body=self.action('start_pack_adventure',character=character)
            self.assertTrue(self.request('/api/action',body,self.token)['duplicate']);self.assertEqual(provider.call_count,1)
            self.assertNotIn('PRIVATE-DIRECTOR',str(self.state(guest)))
            self.assertNotIn('narrative',self.state()['state'])
            self.action('talk_pack_adventure',character=character,text='Pausa fuera de personaje.',mode='ooc')
            self.assertEqual(provider.call_count,1)
            self.rejected(lambda:self.action('talk_pack_adventure',guest,character=character,text='Actúo por Aria.',mode='action'),403)
            provider.return_value=narrative_reply('intentar')
            with patch('action_randomness.hmac.digest',side_effect=AssertionError('Narration rolled')):
                self.action('talk_pack_adventure',character=character,text='Investigo el farol.',mode='action')
            request=self.state()['state']['narrativeView']['pending']
            self.assertEqual(self.state()['state']['characters'][0]['sheet']['fields']['energy'],3)
            self.rejected(lambda:self.action('resolve_pack_request',guest,request=request['id']),403)
            self.rejected(lambda:self.action('resolve_pack_request',request=request['id'],physical={'dice':[7,1]}))
            with patch('action_randomness.hmac.digest',return_value=(3).to_bytes(32,'big')) as rng:
                body=self.action('resolve_pack_request',request=request['id'])
                self.assertTrue(self.request('/api/action',body,self.token)['duplicate']);self.assertEqual(rng.call_count,2)
            self.assertEqual(provider.call_count,2)
            provider.return_value=narrative_reply(narration='Tras el resultado confirmado se distingue una marca.')
            body=self.action('continue_pack_adventure')
            self.assertTrue(self.request('/api/action',body,self.token)['duplicate']);self.assertEqual(provider.call_count,3)
            observed=provider.call_args.args[0]['request']['confirmedResult']
            self.assertEqual(observed['trace']['rolls']['dice']['values'],[4,4])
            self.assertEqual(observed['trace']['changes']['energy']['after'],2)
            self.rejected(lambda:self.action('continue_pack_adventure'))
            self.assertEqual(provider.call_count,3)
        exported=self.request('/api/export',{},self.token)
        with patch('action_randomness.hmac.digest',side_effect=AssertionError('Copy rolled')):
            self.action('import',campaign=exported)
        self.assertEqual(self.state()['state']['characters'][0]['sheet']['fields']['energy'],2)

    def test_director_response_survives_failed_confirmation_without_another_call(self):
        self.action('install_rule_pack',package=document('live-lantern-example'),policy='provided-rules')
        self.action('create_pack_sheet',name='Aria');character=self.state()['state']['characters'][0]['id']
        body={'id':secrets.token_hex(12),'version':self.state()['version'],'type':'start_pack_adventure','character':character}
        with patch.object(pack_director,'propose',return_value=narrative_reply()) as provider:
            with patch.object(server.STORE,'commit',side_effect=Unavailable('Simulated outage after narration')):
                self.rejected(lambda:self.request('/api/action',body,self.token),503)
            self.request('/api/action',body,self.token)
            self.assertTrue(self.request('/api/action',body,self.token)['duplicate']);self.assertEqual(provider.call_count,1)
        self.assertEqual(self.state()['state']['narrativeView']['revision'],1)

    def test_undeclared_movement_is_captured_and_rejected_again_without_another_call(self):
        import io,json
        import rule_preparation_attempt as attempts
        cid=self.install()
        with patch.object(pack_director,'propose',return_value=narrative_reply()):self.action('start_pack_adventure',character=cid)
        before=self.state();body={'id':secrets.token_hex(12),'version':before['version'],'type':'talk_pack_adventure',
            'character':cid,'mode':'action','text':'Declaro intentar para investigar la marca.'}
        answer=narrative_reply('attempt',narration='Aria se acerca al mostrador. Arda espera los dados.')
        raw=json.dumps({'stop_reason':'end_turn','content':[{'type':'text','text':json.dumps(answer)}],'usage':{'input_tokens':100,'output_tokens':100}}).encode()
        original=pack_director.propose;prepared=[]
        def transport(request,response_observer=None):
            prepared.append(request)
            with patch.object(pack_director.urllib.request,'urlopen',return_value=io.BytesIO(raw)):
                return original(request,response_observer=response_observer)
        with patch.object(pack_director,'propose',side_effect=transport) as provider:
            for n in range(2):
                with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/action',body,self.token)
                self.assertEqual(error.exception.code,400)
                self.assertIn('antes de resolverla',error.exception.read().decode());error.exception.close()
                self.assertEqual(self.state(),before);self.assertEqual(provider.call_count,1)
                diagnostic=self.request('/api/rule-pack/preparation-attempt?requestSha256='+prepared[0]['sha256'],token=self.token)
                self.assertEqual(diagnostic['phase'],'captured')
                attempts.forget(server.STORE,before['me']['campaign'],attempts.key(before['me']['id'],prepared[0]['sha256']))

    def test_ownership_and_package_replacement_reject_before_randomness(self):
        cid=self.install()
        guest=self.request('/api/join',{'name':'Luis','invite':self.state()['invite']})['token']
        with patch('action_randomness.hmac.digest',side_effect=AssertionError('Rejected operation rolled')):
            self.rejected(lambda:self.action('run_pack_action',guest,character=cid,action='attempt'),403)
            self.rejected(lambda:self.action('install_rule_pack',package=document('cairn-saves'),policy='provided-rules'))
            self.rejected(lambda:self.action('run_pack_action',character=cid,action='attempt',physical={'pool':[7,1]}))

    def test_import_replays_saved_results_and_rejects_tampering(self):
        cid=self.install()
        self.action('run_pack_action',character=cid,action='attempt',physical={'pool':[3,4]})
        exported=self.request('/api/export',{},self.token)
        other=self.request('/api/create',{'title':'Recovery','player':'Eva','ruleset':'rule-pack'})['token']
        with patch('action_randomness.hmac.digest',side_effect=AssertionError('Recovery rolled')):
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
        with patch.object(campaign,'MAX_MESSAGES',2),patch('action_randomness.hmac.digest',side_effect=AssertionError('Full history rolled')):
            with self.assertRaises(RulePackError):
                campaign.execute_action(original,{'type':'run_pack_action','character':original['characters'][0]['id'],'action':'attempt'},me)
        self.assertEqual(original,before)

    def test_preparation_is_private_deduplicated_and_requires_separate_installation(self):
        raw=authoring_fixture.request();raw['document']['pages'][0]['text']+=' PRIVATE-SOURCE-FRAGMENT'
        prepared=authoring.prepare_input(raw);report=authoring.validate_reply(prepared,authoring_fixture.reply(prepared))
        guest=self.request('/api/join',{'name':'Luis','invite':self.state()['invite']})['token']
        with patch.object(authoring,'propose',return_value=report) as provider:
            self.rejected(lambda:self.action('prepare_rule_pack',guest,request=raw),403)
            body=self.action('prepare_rule_pack',request=raw)
            self.assertTrue(self.request('/api/action',body,self.token)['duplicate'])
            self.rejected(lambda:self.action('prepare_rule_pack',request=raw))
            self.assertEqual(provider.call_count,1)
            self.assertNotIn('PRIVATE-SOURCE-FRAGMENT',str(self.state(guest)))
            self.assertNotIn('authoring',self.state(guest)['state'])
            self.assertNotIn('authoringWorkspace',self.state(guest)['state'])
            state=self.state()['state'];self.assertIsNone(state['package'])
            self.assertEqual(campaign.preparation_record(state)['report']['sourceVerification'],'unverified')
            self.rejected(lambda:self.action('install_prepared_rule_pack',preparation='stale',policy='provided-rules'))
            self.action('install_prepared_rule_pack',preparation=prepared['sha256'],policy='draft')
            self.rejected(lambda:self.action('create_pack_sheet',name='Aria'))
            self.action('install_prepared_rule_pack',preparation=prepared['sha256'],policy='provided-rules')
            self.action('create_pack_sheet',name='Aria')
            exported=self.request('/api/export',{},self.token)
            self.action('import',campaign=exported)
            self.assertEqual(provider.call_count,1)

    def test_preparation_recovers_after_failed_commit_and_private_capture_is_removed(self):
        raw=authoring_fixture.request();prepared=authoring.prepare_input(raw)
        report=authoring.validate_reply(prepared,authoring_fixture.reply(prepared))
        guest=self.request('/api/join',{'name':'Luis','invite':self.state()['invite']})['token']
        body={'id':secrets.token_hex(12),'version':self.state()['version'],'type':'prepare_rule_pack','request':raw}
        path='/api/rule-pack/preparation-attempt?requestSha256='+prepared['sha256']
        with patch.object(authoring,'propose',return_value=report) as provider:
            with patch.object(server.STORE,'commit',side_effect=Unavailable('Simulated persistence outage')):
                self.rejected(lambda:self.request('/api/action',body,self.token),503)
            saved=self.request(path,token=self.token)
            self.assertEqual(saved['phase'],'captured');self.assertEqual(saved['request'],prepared['request'])
            self.assertEqual(saved['response']['value'],report)
            with patch.object(server.STORE,'read_rule_preparation',side_effect=AssertionError('Guest accessed private capture')):
                with self.assertRaises(urllib.error.HTTPError) as error:self.request(path,token=guest)
                self.assertEqual(error.exception.code,403);error.exception.close()
            # Drop the process-local fallback: the persisted response must suffice.
            import rule_preparation_attempt as attempts
            me=server.STORE.identity(self.token)
            attempts.forget(server.STORE,me['campaign'],attempts.key(me['id'],prepared['sha256']))
            self.request('/api/action',body,self.token)
            self.assertTrue(self.request('/api/action',body,self.token)['duplicate'])
            self.assertEqual(provider.call_count,1)
            # A delayed request with an old snapshot cannot reserve a second paid call.
            with self.assertRaises(Conflict):
                server.STORE.begin_rule_preparation(me['campaign'],attempts.key(me['id'],prepared['sha256']),me['id'],prepared)
        with self.assertRaises(urllib.error.HTTPError) as error:self.request(path,token=self.token)
        self.assertEqual(error.exception.code,404);error.exception.close()
        self.assertEqual(campaign.preparation_record(self.state()['state'])['report'],report)

    def test_uncertain_preparation_does_not_retry_with_a_new_action_id(self):
        raw=authoring_fixture.request()
        with patch.object(authoring,'propose',side_effect=RulePackError('Unknown provider outcome')) as provider:
            self.rejected(lambda:self.action('prepare_rule_pack',request=raw))
            self.rejected(lambda:self.action('prepare_rule_pack',request=raw),409)
            self.assertEqual(provider.call_count,1)

    def test_blocked_or_failed_preparation_never_installs_rules(self):
        raw=authoring_fixture.request()
        with patch.object(authoring,'propose',side_effect=RulePackError('Invalid model output')) as provider:
            self.rejected(lambda:self.action('prepare_rule_pack',request=raw));self.assertEqual(provider.call_count,1)
        raw['scope']='Una mecánica no soportada'
        prepared=authoring.prepare_input(raw)
        blocked=authoring.validate_reply(prepared,{'status':'unsupported','packageJson':'','examples':[],
            'issues':[{'kind':'unsupported','message':'La operación no está soportada.','sources':[prepared['sources'][0]['id']]}]})
        with patch.object(authoring,'propose',return_value=blocked):self.action('prepare_rule_pack',request=raw)
        self.assertIsNone(self.state()['state']['package'])
        self.rejected(lambda:self.action('install_prepared_rule_pack',preparation=prepared['sha256'],policy='provided-rules'))
        exported=self.request('/api/export',{},self.token)
        with patch.object(authoring,'propose',side_effect=AssertionError('Recovery called model')):self.action('import',campaign=exported)

    def test_composition_preview_is_stateless_and_install_is_atomic_and_owned(self):
        base,additional=composition_blocks()
        self.action('install_rule_pack',package=base)
        guest=self.request('/api/join',{'name':'Luis','invite':self.state()['invite']})['token']
        with patch.object(server,'repository',side_effect=AssertionError('Preview accessed storage')):
            preview=self.request('/api/rule-pack/compose',{'packages':[base,additional],'version':'1.1.0'})
        parameters={'additional':[additional],'versionTarget':'1.1.0','baseSha256':self.state()['state']['package']['sha256'],
            'expectedSha256':preview['provenance']['packageSha256'],'policy':'draft'}
        with patch.object(authoring,'propose',side_effect=AssertionError('Composition called AI')),patch('action_randomness.hmac.digest',side_effect=AssertionError('Composition rolled')):
            self.rejected(lambda:self.action('compose_rule_pack',guest,**parameters),403)
            self.rejected(lambda:self.action('compose_rule_pack',**(parameters|{'baseSha256':'stale'})))
            self.rejected(lambda:self.action('compose_rule_pack',**(parameters|{'expectedSha256':'stale'})))
            body=self.action('compose_rule_pack',**parameters)
            self.assertTrue(self.request('/api/action',body,self.token)['duplicate'])
            self.action('install_rule_pack',package=self.state()['state']['package']['document'],policy='provided-rules')
            self.assertEqual(self.state()['state']['package']['composition'],preview['provenance'])
            self.action('create_pack_sheet',name='Aria');cid=self.state()['state']['characters'][0]['id']
            self.action('run_pack_action',character=cid,action='use_reserve')
            self.action('run_pack_action',character=cid,action='attempt',physical={'pool':[3,4]})
            self.assertEqual(self.state()['state']['characters'][0]['sheet']['fields']['reserve'],1)
            exported=self.request('/api/export',{},self.token);self.action('import',campaign=exported)
            self.assertEqual(self.state()['state']['package']['composition'],preview['provenance'])
            altered=copy.deepcopy(exported);altered['state']['package']['composition']['inputs'][0]['sha256']='bad'
            self.rejected(lambda:self.action('import',campaign=altered))
            self.rejected(lambda:self.action('compose_rule_pack',**parameters))

    def test_composition_conflicts_do_not_replace_campaign_rules(self):
        base,additional=composition_blocks();self.action('install_rule_pack',package=base)
        additional['fields']['energy']['initial']=2
        before=self.state()
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.request('/api/rule-pack/compose',{'packages':[base,additional],'version':'1.1.0'})
        self.assertEqual(error.exception.code,400);error.exception.close();self.assertEqual(self.state(),before)

    def test_legacy_preparation_copy_keeps_its_original_source_scheme(self):
        raw=authoring_fixture.request();prepared=authoring.prepare_input(raw,authoring.LEGACY_SOURCE_SCHEME)
        report=authoring.validate_reply(prepared,authoring_fixture.reply(prepared))
        exported=self.request('/api/export',{},self.token)
        exported['state']['authoring']={'request':raw,'sha256':prepared['sha256'],'report':report}
        with patch.object(authoring,'propose',side_effect=AssertionError('Legacy copy called provider')):
            self.action('import',campaign=exported)
            self.action('install_prepared_rule_pack',preparation=prepared['sha256'],policy='provided-rules')
            self.action('create_pack_sheet',name='Aria')
        self.assertEqual(self.state()['state']['package']['document']['sources'],prepared['sources'])

    def test_preparation_workspace_retains_old_block_and_shares_text(self):
        first=authoring_fixture.request();second=copy.deepcopy(first);second['scope']='Otro bloque de reglas'
        def propose(prepared,response_observer=None):return authoring.validate_reply(prepared,authoring_fixture.reply(prepared))
        with patch.object(authoring,'propose',side_effect=propose) as provider:
            self.action('prepare_rule_pack',request=first);self.action('prepare_rule_pack',request=second)
            self.rejected(lambda:self.action('prepare_rule_pack',request=first))
            self.assertEqual(provider.call_count,2)
            state=self.state()['state'];workspace=state['authoringWorkspace']
            self.assertIsNone(state['authoring']);self.assertEqual(len(workspace['blocks']),2)
            self.assertEqual(len(workspace['sources']),1);self.assertEqual(len(workspace['texts']),1)
            exported=self.request('/api/export',{},self.token)
            self.action('import',campaign=exported)
            older=authoring.prepare_input(first)['sha256']
            self.action('install_prepared_rule_pack',preparation=older,policy='provided-rules')
            self.assertEqual(provider.call_count,2)
            altered=copy.deepcopy(exported);key=next(iter(altered['state']['authoringWorkspace']['texts']))
            altered['state']['authoringWorkspace']['texts'][key]='Changed original'
            self.rejected(lambda:self.action('import',campaign=altered))

    def test_preparation_workspace_reserves_capacity_before_provider(self):
        import rule_preparation_workspace as workspaces
        with patch.object(workspaces,'MAX_BYTES',100),patch.object(authoring,'propose',side_effect=AssertionError('Capacity failure called provider')):
            self.rejected(lambda:self.action('prepare_rule_pack',request=authoring_fixture.request()))

    def test_failed_new_block_preserves_previous_preparation(self):
        raw=authoring_fixture.request();prepared=authoring.prepare_input(raw)
        report=authoring.validate_reply(prepared,authoring_fixture.reply(prepared))
        with patch.object(authoring,'propose',return_value=report):self.action('prepare_rule_pack',request=raw)
        other=copy.deepcopy(raw);other['scope']='Different requested block'
        with patch.object(authoring,'propose',side_effect=RulePackError('Rejected proposal')):
            self.rejected(lambda:self.action('prepare_rule_pack',request=other))
        self.assertEqual(self.state()['state']['authoringWorkspace']['latest'],prepared['sha256'])

    def test_legacy_preparation_moves_into_workspace_only_after_success(self):
        raw=authoring_fixture.request();prepared=authoring.prepare_input(raw,authoring.LEGACY_SOURCE_SCHEME)
        report=authoring.validate_reply(prepared,authoring_fixture.reply(prepared))
        exported=self.request('/api/export',{},self.token)
        exported['state'].pop('authoringWorkspace',None)
        exported['state']['authoring']={'request':raw,'sha256':prepared['sha256'],'report':report}
        self.action('import',campaign=exported)
        other=copy.deepcopy(raw);other['scope']='Nuevo bloque';current=authoring.prepare_input(other)
        with patch.object(authoring,'propose',return_value=authoring.validate_reply(current,authoring_fixture.reply(current))):
            self.action('prepare_rule_pack',request=other)
        state=self.state()['state'];self.assertIsNone(state['authoring'])
        self.assertEqual(len(state['authoringWorkspace']['blocks']),2);self.assertEqual(len(state['authoringWorkspace']['texts']),1)
        self.assertEqual(campaign.preparation_record(state,prepared['sha256'])['report'],report)

    def test_workspace_cache_protocol_omits_payload_and_never_fetches_for_guest(self):
        raw=authoring_fixture.request();prepared=authoring.prepare_input(raw)
        with patch.object(authoring,'propose',return_value=authoring.validate_reply(prepared,authoring_fixture.reply(prepared))):self.action('prepare_rule_pack',request=raw)
        state=self.state();reference=state['state']['authoringWorkspaceRef'];self.assertIsNotNone(reference)
        with patch.object(server.STORE,'load_rule_workspace',side_effect=AssertionError('Known workspace fetched')):
            response=self.request('/api/state?workspace='+reference['sha256'],token=self.token)
            self.assertEqual(response['workspaceUnchanged'],reference['sha256']);self.assertIsNone(response['state']['authoringWorkspace'])
        exported=self.request('/api/export',{},self.token)
        self.assertIsNone(exported['state']['authoringWorkspaceRef']);self.assertTrue(exported['state']['authoringWorkspace']['blocks'])
        guest=self.request('/api/join',{'name':'Luis','invite':state['invite']})['token']
        with patch.object(server.STORE,'load_rule_workspace',side_effect=AssertionError('Guest fetched private workspace')):
            self.assertNotIn('authoringWorkspaceRef',self.state(guest)['state'])
        forged=copy.deepcopy(exported);forged['state']['authoringWorkspace']=None;forged['state']['authoringWorkspaceRef']=reference
        self.rejected(lambda:self.action('import',campaign=forged))

    def test_unavailable_sources_preserve_play_and_never_export_an_incomplete_copy(self):
        raw=authoring_fixture.request();prepared=authoring.prepare_input(raw)
        with patch.object(authoring,'propose',return_value=authoring.validate_reply(prepared,authoring_fixture.reply(prepared))):self.action('prepare_rule_pack',request=raw)
        self.action('install_prepared_rule_pack',preparation=prepared['sha256'],policy='provided-rules');self.action('create_pack_sheet',name='Aria')
        current=self.state();cid=current['state']['characters'][0]['id']
        with patch.object(server.STORE,'load_rule_workspace',side_effect=Unavailable('Private sources unavailable')) as fetch:
            unavailable=self.state();self.assertTrue(unavailable['workspaceUnavailable'])
            calls=fetch.call_count
            self.request('/api/action',{'id':secrets.token_hex(12),'version':unavailable['version'],'type':'run_pack_action','character':cid,'action':'attempt','physical':{'pool':[3,4]}},self.token)
            self.assertEqual(fetch.call_count,calls)
            after=self.state();self.assertEqual(after['state']['characters'][0]['sheet']['fields']['energy'],2)
            self.assertEqual(after['state']['authoringWorkspaceRef'],current['state']['authoringWorkspaceRef'])
            with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/export',{},self.token)
            self.assertEqual(error.exception.code,503);error.exception.close()


class RulePackWaitressTests(RulePackServerTests):
    @classmethod
    def setUpClass(cls):
        cls.environment=patch.dict(os.environ,{'ANTHROPIC_API_KEY':'fixture-never-sent'});cls.environment.start()
        cls.registration=patch.dict(rulesets.SYSTEMS,{'rule-pack':{'id':'rule-pack','name':'Generic test','status':'experimental'}})
        cls.registration.start()
        test_render.ProductionServerTests.setUpClass.__func__(cls)

    @classmethod
    def tearDownClass(cls):
        try:test_render.ProductionServerTests.tearDownClass.__func__(cls)
        finally:cls.registration.stop();cls.environment.stop()
