"""Two owners, real HTTP/emulator, simulated director and private state."""
import secrets
import threading
import unittest
import urllib.error
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import server
import test_campaign_world_http as transport
from test_character_builder import choices
from firebase_store import Unavailable


class GroupDirectorConcurrencyHTTPTests(unittest.TestCase):
    setUpClass=classmethod(transport.CampaignWorldHTTPTests.setUpClass.__func__)
    tearDownClass=classmethod(transport.CampaignWorldHTTPTests.tearDownClass.__func__)
    request=transport.CampaignWorldHTTPTests.request
    state=transport.CampaignWorldHTTPTests.state
    action=transport.CampaignWorldHTTPTests.action

    def setUp(self):
        configured=patch.dict('os.environ',{'ANTHROPIC_API_KEY':'fixture-never-sent'})
        configured.start();self.addCleanup(configured.stop)
        self.token=self.request('/api/create',{'title':'Dos propietarios','player':'Ana','mode':'online'})['token']
        self.guest=self.request('/api/join',{'name':'Luis','invite':self.state()['invite']})['token']
        self.action('create_character',choices={**choices(),'name':'Liria'})
        self.action('create_character',self.guest,choices={**choices(),'name':'Taro'})
        self.action('start_adventure',moduleId='la-carta-perdida',openingContract='authored-opening-1',
                    captureContract='pf-authored-opening-1',worldMemoryContract='structured-world-memory-1')
        self.action('talk',kind='private',text='PRIVATE-HOST-NOTE',director=False)
        self.host_actor=next(c['id'] for c in self.state()['state']['characters'] if c['name']=='Liria')
        self.guest_actor=next(c['id'] for c in self.state()['state']['characters'] if c['name']=='Taro')

    def body(self,actor,text):
        return {'id':secrets.token_hex(12),'version':self.state()['version'],'type':'talk','kind':'dialogue',
                'character':actor,'text':text,'director':True,'captureContract':'pf-director-action-1'}

    def reply(self,text):
        return {'narration':text,'proposals':[],
                'memory':{'summary':'La carta sigue perdida; nadie la ha recogido.','preparation':'PRIVATE-DIRECTOR-MEMORY'},
                'worldUpdates':{'npcs':[],'places':[],'relationships':[]}}

    def test_two_owners_wait_then_review_stale_intent_without_duplicate_inference(self):
        first=self.body(self.host_actor,'Saludo a Gaspar desde la barra.')
        second=self.body(self.guest_actor,'Pregunto a Gaspar por la posada.')
        entered=threading.Event();release=threading.Event();second_done=threading.Event()
        def reply(*args,**kwargs):
            entered.set()
            if not release.wait(10):raise AssertionError('Director fixture was not released')
            return self.reply('Gaspar devuelve el saludo sin mover a los personajes.')
        def send_second():
            try:return self.request('/api/action',second,self.guest)
            finally:second_done.set()
        with (patch.object(server,'search',return_value=[]),patch.object(server,'ai_reply',side_effect=reply) as provider,
              ThreadPoolExecutor(max_workers=2) as pool):
            pending=pool.submit(self.request,'/api/action',first)
            try:
                self.assertTrue(entered.wait(5));following=pool.submit(send_second)
                self.assertFalse(second_done.wait(.3))
            finally:release.set()
            pending.result(timeout=10)
            with self.assertRaises(urllib.error.HTTPError) as error:following.result(timeout=10)
            self.assertEqual(error.exception.code,409);error.exception.close();self.assertEqual(provider.call_count,1)
        guest=self.state(self.guest);self.assertNotIn('PRIVATE',str(guest))
        self.assertFalse(any(m.get('text')==second['text'] for m in guest['state']['messages']))
        # This is a new, explicit decision after reading the updated state, not an automatic retry.
        reviewed={**second,'id':secrets.token_hex(12),'version':guest['version']}
        with patch.object(server,'search',return_value=[]),patch.object(server,'ai_reply',return_value=self.reply('Gaspar responde sobre la posada.')) as provider:
            self.request('/api/action',reviewed,self.guest)
            self.assertTrue(self.request('/api/action',reviewed,self.guest)['duplicate']);self.assertEqual(provider.call_count,1)
        host=self.state();guest=self.state(self.guest)
        self.assertEqual(host['version'],guest['version']);self.assertEqual(host['state']['characters'],guest['state']['characters'])
        self.assertEqual(len([m for m in guest['state']['messages'] if m.get('kind')=='director']),2)
        self.assertEqual(len([m for m in guest['state']['messages'] if m.get('text')==second['text']]),1)
        self.assertNotIn('PRIVATE',str(guest));self.assertIn('PRIVATE-HOST-NOTE',str(host))

    def test_guest_cannot_use_hosts_character_or_read_private_pending_capture(self):
        body=self.body(self.host_actor,'Saludo a Gaspar sin recoger la carta.');before=self.state()
        with patch.object(server,'search',return_value=[]),patch.object(server,'ai_reply',return_value=self.reply('Gaspar devuelve el saludo.')) as provider:
            with patch.object(server.STORE,'commit',side_effect=Unavailable('Interrupted confirmation')):
                with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/action',body)
            self.assertEqual(error.exception.code,503);error.exception.close();self.assertEqual(provider.call_count,1)
        self.assertEqual(self.state(),before)
        with patch.object(server,'ai_reply',side_effect=AssertionError('Guest reused private host capture')):
            with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/action',body,self.guest)
            self.assertEqual(error.exception.code,403);error.exception.close()
            with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/rule-pack/preparation-attempt?requestSha256='+'a'*64,token=self.guest)
            self.assertEqual(error.exception.code,403);error.exception.close()
            self.request('/api/action',body);self.assertTrue(self.request('/api/action',body)['duplicate'])
        guest=self.state(self.guest);self.assertNotIn('PRIVATE',str(guest))
        self.assertEqual(len([m for m in guest['state']['messages'] if m.get('kind')=='director']),1)

    def test_only_owner_chooses_search_and_both_owners_share_completed_investigation(self):
        before=self.state()
        with patch.object(server,'ai_reply',side_effect=AssertionError('Prepared investigation called provider')):
            with self.assertRaises(urllib.error.HTTPError) as error:
                self.action('investigate',character=self.guest_actor,opportunity='rastro',method='take20')
            self.assertEqual(error.exception.code,403);error.exception.close();self.assertEqual(self.state(),before)
            self.action('investigate',self.guest,character=self.guest_actor,opportunity='rastro',method='take20')
            self.action('investigate',character=self.host_actor,opportunity='carta',method='take20')
        host=self.state();guest=self.state(self.guest)
        self.assertTrue(host['state']['moduleProgress']['completed'])
        self.assertEqual(host['state']['moduleProgress'],guest['state']['moduleProgress'])
        self.assertEqual([d['character'] for d in host['state']['moduleProgress']['discoveries']],[self.guest_actor,self.host_actor])
        self.assertNotIn('PRIVATE',str(guest))

    def test_host_cannot_resolve_guests_pending_search_or_choose_its_method(self):
        self.action('investigate',self.guest,character=self.guest_actor,opportunity='rastro')
        before=self.state();pending=before['state']['pending'][0]['check']['id']
        with (patch.object(server,'ai_reply',side_effect=AssertionError('Search called provider')),
              patch('game_randomness.draw',side_effect=AssertionError('Unauthorized search rolled dice'))):
            for method in ('roll','take10','take20'):
                with self.subTest(method=method),self.assertRaises(urllib.error.HTTPError) as error:
                    self.action('check',request=pending,method=method)
                self.assertEqual(error.exception.code,403);error.exception.close();self.assertEqual(self.state(),before)
            self.action('check',self.guest,request=pending,method='take20')
        result=self.state(self.guest)['state']['moduleProgress']['discoveries'][0]
        self.assertEqual(result['character'],self.guest_actor)
