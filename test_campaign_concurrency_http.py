"""Concurrent real HTTP requests with a blocked, simulated director."""
import secrets
import threading
import unittest
import urllib.error
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import server
import test_campaign_world_http as transport
from test_character_builder import choices


class CampaignConcurrencyHTTPTests(unittest.TestCase):
    setUpClass=classmethod(transport.CampaignWorldHTTPTests.setUpClass.__func__)
    tearDownClass=classmethod(transport.CampaignWorldHTTPTests.tearDownClass.__func__)
    setUp=transport.CampaignWorldHTTPTests.setUp
    request=transport.CampaignWorldHTTPTests.request
    state=transport.CampaignWorldHTTPTests.state
    action=transport.CampaignWorldHTTPTests.action

    def exercise(self,mode):
        self.action('create_character',choices=choices())
        before=self.state()
        body={'id':secrets.token_hex(12),'version':before['version'],'type':'start_adventure',
              'moduleId':'la-carta-perdida','captureContract':'pf-director-action-1'}
        entered=threading.Event();release=threading.Event();second_done=threading.Event()
        if mode=='independent':
            other=self.request('/api/create',{'title':'Otra mesa','player':'Luis'})['token']
            second={'id':secrets.token_hex(12),'version':self.state(other)['version'],
                    'type':'create_character','choices':choices()}
        else:
            other=self.token
            second=body if mode=='duplicate' else {'id':secrets.token_hex(12),'version':before['version'],
                'type':'talk','kind':'ooc','text':'Comentario concurrente','director':False}
        def reply(*args,**kwargs):
            entered.set()
            if not release.wait(10):raise AssertionError('Director fixture was not released')
            return {'narration':'La posada sigue tranquila.','proposals':[],
                    'memory':{'summary':'La carta sigue perdida.','preparation':'Preparación privada.'}}
        def send_second():
            try:return self.request('/api/action',second,other)
            finally:second_done.set()
        with patch.object(server,'ai_reply',side_effect=reply) as provider,ThreadPoolExecutor(max_workers=2) as pool:
            first=pool.submit(self.request,'/api/action',body)
            try:
                self.assertTrue(entered.wait(5),'The first request did not reach the director')
                following=pool.submit(send_second)
                if mode=='independent':self.assertTrue(second_done.wait(3),'Another campaign was blocked by the director')
                else:self.assertFalse(second_done.wait(.3),'Same-campaign request escaped serialization')
            finally:release.set()
            first.result(timeout=10)
            if mode=='stale':
                with self.assertRaises(urllib.error.HTTPError) as error:following.result(timeout=10)
                self.assertEqual(error.exception.code,409);error.exception.close()
            else:
                result=following.result(timeout=10)
                if mode=='duplicate':self.assertTrue(result['duplicate'])
            self.assertEqual(provider.call_count,1)
        after=self.state()
        self.assertEqual(after['version'],before['version']+1)
        self.assertEqual(len([m for m in after['state']['messages'] if m.get('kind')=='director']),1)
        self.assertFalse(any(m.get('text')=='Comentario concurrente' for m in after['state']['messages']))
        if mode=='independent':self.assertEqual(len(self.state(other)['state']['characters']),1)

    def test_unrelated_campaign_can_commit_while_director_waits(self):self.exercise('independent')
    def test_same_campaign_stale_action_waits_then_conflicts(self):self.exercise('stale')
    def test_same_campaign_duplicate_waits_without_second_provider_call(self):self.exercise('duplicate')
