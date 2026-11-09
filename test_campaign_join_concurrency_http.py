"""Joining during a simulated paid response must preserve its confirmation."""
import copy
import secrets
import threading
import unittest
import urllib.error
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import server
from firebase_store import FirestoreStore,Unavailable
import test_campaign_world_http as transport
from test_character_builder import choices


class CampaignJoinConcurrencyHTTPTests(unittest.TestCase):
    setUpClass=classmethod(transport.CampaignWorldHTTPTests.setUpClass.__func__)
    tearDownClass=classmethod(transport.CampaignWorldHTTPTests.tearDownClass.__func__)
    setUp=transport.CampaignWorldHTTPTests.setUp
    request=transport.CampaignWorldHTTPTests.request
    state=transport.CampaignWorldHTTPTests.state
    action=transport.CampaignWorldHTTPTests.action

    def test_join_waits_for_response_confirmation_and_retry_stays_duplicate(self):
        self.action('create_character',choices=choices());before=self.state()
        body={'id':secrets.token_hex(12),'version':before['version'],'type':'start_adventure',
              'moduleId':'la-carta-perdida','captureContract':'pf-director-action-1'}
        entered=threading.Event();release=threading.Event();joined=threading.Event()
        def reply(*args,**kwargs):
            entered.set()
            if not release.wait(10):raise AssertionError('Director fixture was not released')
            return {'narration':'La posada sigue tranquila.','proposals':[],
                    'memory':{'summary':'La carta sigue perdida.','preparation':'PRIVATE-DIRECTOR-PREPARATION'}}
        def send():
            try:self.request('/api/action',body);return 200
            except urllib.error.HTTPError as error:
                status=error.code;error.close();return status
        def join():
            try:return self.request('/api/join',{'name':'Luis','invite':before['invite']})['token']
            finally:joined.set()
        with patch.object(server,'ai_reply',side_effect=reply) as provider,ThreadPoolExecutor(max_workers=2) as pool:
            pending=pool.submit(send)
            try:
                self.assertTrue(entered.wait(5));joining=pool.submit(join)
                joined_early=joined.wait(.5)
            finally:release.set()
            status=pending.result(timeout=10);guest=joining.result(timeout=10)
            self.assertEqual(status,200,'Joining invalidated the response that was already requested')
            self.assertFalse(joined_early,'Joining escaped the campaign action lock')
            self.assertTrue(self.request('/api/action',body)['duplicate']);self.assertEqual(provider.call_count,1)
        after=self.state();self.assertEqual(after['version'],before['version']+2)
        self.assertEqual(len([m for m in after['state']['messages'] if m.get('kind')=='director']),1)
        public=self.state(guest);self.assertEqual(public['version'],after['version'])
        self.assertNotIn('PRIVATE-DIRECTOR-PREPARATION',str(public))
        self.assertEqual(len(public['players']),2)

    def test_changed_invitation_mapping_is_rechecked_before_membership_write(self):
        before=self.state()
        with patch.object(server.STORE,'invited_campaign',return_value='another-campaign'):
            with self.assertRaises(urllib.error.HTTPError) as error:
                self.request('/api/join',{'name':'Luis','invite':before['invite']})
        self.assertEqual(error.exception.code,409);error.exception.close()
        self.assertEqual(self.state(),before)
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.request('/api/join',{'name':'Luis','invite':'missing-invitation'})
        self.assertEqual(error.exception.code,400);error.exception.close()
        self.assertEqual(self.state(),before);self.assertEqual(server.CAMPAIGN_LOCKS._entries,{})

    def test_other_campaign_join_does_not_wait_for_busy_campaign(self):
        other=self.request('/api/create',{'title':'Otra campaña','player':'Luis'})['token']
        invite=self.state(other)['invite'];self.action('create_character',choices=choices());before=self.state()
        entered=threading.Event();release=threading.Event()
        def reply(*args,**kwargs):
            entered.set()
            if not release.wait(10):raise AssertionError('Director fixture was not released')
            return {'narration':'La posada sigue tranquila.','proposals':[],
                    'memory':{'summary':'La carta sigue perdida.','preparation':'Preparación privada.'}}
        body={'id':secrets.token_hex(12),'version':before['version'],'type':'start_adventure',
              'moduleId':'la-carta-perdida','captureContract':'pf-director-action-1'}
        with patch.object(server,'ai_reply',side_effect=reply) as provider,ThreadPoolExecutor(max_workers=2) as pool:
            pending=pool.submit(self.request,'/api/action',body)
            try:
                self.assertTrue(entered.wait(5))
                joining=pool.submit(self.request,'/api/join',{'name':'Eva','invite':invite})
                guest=joining.result(timeout=3)['token']
                self.assertEqual(len(self.state(guest)['players']),2)
            finally:release.set()
            pending.result(timeout=10);self.assertEqual(provider.call_count,1)

    def test_captured_response_after_failed_commit_survives_later_join_and_cold_retry(self):
        self.action('create_character',choices=choices());before=self.state()
        # Existing campaigns have no stateVersion until their next membership/game write.
        me=server.STORE.identity(self.token)
        if isinstance(server.STORE,FirestoreStore):
            from google.cloud import firestore
            server.STORE.campaign(me['campaign']).update({'stateVersion':firestore.DELETE_FIELD})
        else:server.STORE.campaigns[me['campaign']][0].pop('stateVersion',None)
        body={'id':secrets.token_hex(12),'version':before['version'],'type':'start_adventure',
              'moduleId':'la-carta-perdida','captureContract':'pf-director-action-1'}
        reply={'narration':'La posada sigue tranquila.','proposals':[],
               'memory':{'summary':'La carta sigue perdida.','preparation':'PRIVATE-CAPTURE'}}
        with patch.object(server,'ai_reply',return_value=reply) as provider:
            with patch.object(server.STORE,'commit',side_effect=Unavailable('Interrupted confirmation')):
                with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/action',body)
            self.assertEqual(error.exception.code,503);error.exception.close();self.assertEqual(provider.call_count,1)
        self.assertEqual(self.state(),before)
        guest=self.request('/api/join',{'name':'Luis','invite':before['invite']})['token']
        previous=server.STORE
        if isinstance(previous,FirestoreStore):
            server.STORE=FirestoreStore.from_environment();server.STORE.prefix=previous.prefix
        try:
            with patch.object(server,'ai_reply',side_effect=AssertionError('Captured response was billed again')):
                self.request('/api/action',body);self.assertTrue(self.request('/api/action',body)['duplicate'])
            after=self.state();self.assertEqual(after['version'],before['version']+2)
            self.assertEqual(len([m for m in after['state']['messages'] if m.get('kind')=='director']),1)
            self.assertNotIn('PRIVATE-CAPTURE',str(self.state(guest)))
            # A subsequent game action must still invalidate an old declaration.
            self.action('talk',kind='ooc',text='Una nueva decisión.',director=False)
            changed={**body,'id':secrets.token_hex(12)}
            with patch.object(server,'ai_reply',side_effect=AssertionError('Stale action reached provider')):
                with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/action',changed)
            self.assertEqual(error.exception.code,409);error.exception.close()
        finally:server.STORE=previous

    def test_reserved_dice_after_failed_commit_survive_join_with_original_body_and_seed(self):
        before=self.state();candidate=[]
        body={'id':secrets.token_hex(12),'version':before['version'],'type':'roll','n':2,
              'sides':20,'modifier':3,'label':'Tirada técnica','source':'Prueba de persistencia'}
        def interrupted(*args,**kwargs):
            candidate.append(copy.deepcopy(args[5]));raise Unavailable('Interrupted roll confirmation')
        with patch.object(server,'ai_reply',side_effect=AssertionError('Dice called provider')):
            with patch.object(server.STORE,'commit',side_effect=interrupted):
                with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/action',body)
            self.assertEqual(error.exception.code,503);error.exception.close();self.assertEqual(self.state(),before)
            self.request('/api/join',{'name':'Luis','invite':before['invite']})
            previous=server.STORE
            if isinstance(previous,FirestoreStore):
                server.STORE=FirestoreStore.from_environment();server.STORE.prefix=previous.prefix
            try:
                self.request('/api/action',body);after=self.state()
                self.assertEqual(after['state']['messages'][-1]['text'],candidate[0]['messages'][-1]['text'])
                self.assertTrue(self.request('/api/action',body)['duplicate']);self.assertEqual(self.state(),after)
            finally:server.STORE=previous

    def test_fresh_stale_decisions_after_join_do_not_reserve_provider_or_dice(self):
        self.action('create_character',choices=choices());before=self.state()
        self.request('/api/join',{'name':'Luis','invite':before['invite']});after_join=self.state()
        actions=[{'type':'start_adventure','moduleId':'la-carta-perdida','captureContract':'pf-director-action-1'},
                 {'type':'roll','n':1,'sides':20},
                 {'type':'spend','benefit':'ayuda','consent':True,'interpretation':'Consentimiento anterior'}]
        with (patch.object(server,'ai_reply',side_effect=AssertionError('Stale decision called provider')),
              patch.object(server.STORE,'begin_rule_preparation',side_effect=AssertionError('Stale decision reserved provider')),
              patch.object(server.STORE,'action_random_seed',side_effect=AssertionError('Stale decision reserved dice'))):
            for action in actions:
                body={'id':secrets.token_hex(12),'version':before['version'],**action}
                with self.subTest(action=action['type']),self.assertRaises(urllib.error.HTTPError) as error:
                    self.request('/api/action',body)
                self.assertEqual(error.exception.code,409);error.exception.close()
                self.assertEqual(self.state(),after_join)

    def test_previous_writer_state_change_is_not_mistaken_for_membership_only(self):
        before=self.state();body={'id':secrets.token_hex(12),'version':before['version'],'type':'roll','n':1,'sides':20}
        with patch.object(server.STORE,'commit',side_effect=Unavailable('Interrupted dice')):
            with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/action',body)
        self.assertEqual(error.exception.code,503);error.exception.close()
        store=server.STORE;cid=store.identity(self.token)['campaign'];row,state=store.load(cid)
        state['notes']='Changed by previous server writer'
        if isinstance(store,FirestoreStore):
            staged=store._stage(cid,state)
            store.campaign(cid).update({'version':row['version']+1,**staged})
        else:
            row['version']+=1;row['snapshot']='previous-writer-state';store.campaigns[cid]=(row,state)
        # The new join must repair the snapshot binding rather than carry the old stateVersion forward.
        self.request('/api/join',{'name':'Luis','invite':before['invite']});changed=self.state()
        with patch.object(server,'ai_reply',side_effect=AssertionError('Old roll called provider')):
            with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/action',body)
        self.assertEqual(error.exception.code,409);error.exception.close()
        self.assertEqual(self.state(),changed);self.assertEqual(changed['state']['notes'],'Changed by previous server writer')
