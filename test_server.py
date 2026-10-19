"""Pruebas HTTP reales. El adaptador de IA se sustituye solo en esta prueba."""
import json, secrets, threading, unittest, urllib.request, urllib.error
from pathlib import Path
import server
from test_support import make_store
from unittest.mock import patch

class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.oldStore=server.STORE;server.STORE=make_store();server.initialize()
        cls.http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler); cls.url='http://127.0.0.1:'+str(cls.http.server_port)
        cls.thread=threading.Thread(target=cls.http.serve_forever,daemon=True);cls.thread.start()
    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown();cls.http.server_close();server.STORE=cls.oldStore
    def request(self,path,body=None,token=''):
        req=urllib.request.Request(self.url+path,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json','Authorization':'Bearer '+token})
        with urllib.request.urlopen(req) as r:return json.load(r)
    def setUp(self):
        self.token=self.request('/api/create',{'title':'Prueba','player':'Ana'})['token']
    def state(self,token=None):return self.request('/api/state',token=token or self.token)
    def action(self,type,token=None,**data):
        state=self.state(token); body={'id':secrets.token_hex(12),'version':state['version'],'type':type,**data}
        self.request('/api/action',body,token or self.token);return body
    def test_shared_identity_and_permissions(self):
        guest=self.request('/api/join',{'name':'Luis','invite':self.state()['invite']})['token'];self.action('character',character={'name':'Aria'})
        self.action('talk',guest,text='Hola',director=False,kind='dialogue');state=self.state();self.assertEqual(state['state']['messages'][-1]['speaker'],'Luis')
        cid=state['state']['characters'][0]['id']
        with self.assertRaises(urllib.error.HTTPError) as e:self.action('move',guest,character=cid,path=[[1,0]],acknowledge=True)
        self.assertEqual(e.exception.code,403)
        self.action('talk',text='Secreto',kind='private',director=False)
        self.assertFalse(any(m['text']=='Secreto' for m in self.state(guest)['state']['messages']))
    def test_deduplication_and_stale_write(self):
        body=self.action('roll',n=1,sides=20,modifier=2,physical=[14]);before=self.state()
        response=self.request('/api/action',body,self.token);self.assertTrue(response['duplicate']);self.assertEqual(before['version'],self.state()['version'])
        body['id']='new-action'
        with self.assertRaises(urllib.error.HTTPError) as e:self.request('/api/action',body,self.token)
        self.assertEqual(e.exception.code,409)
    def test_persistent_recovery_and_export(self):
        self.action('character',character={'name':'Aria'});self.action('oracle',question='¿Hay luz?',uncertain=True,physical=[8,4,1])
        before=self.state();server.initialize();after=self.state();self.assertEqual(before['state'],after['state'])
        exported=self.request('/api/export',{},self.token);self.action('scene',location='Ruinas');self.action('import',campaign=exported);self.assertEqual(self.state()['state']['scene'],1)
    def test_real_ai_unavailable_does_not_create_fake_reply(self):
        old=server.os.environ.pop('ANTHROPIC_API_KEY',None)
        try:
            before=self.state()
            with self.assertRaises(urllib.error.HTTPError):self.action('talk',text='Inicio',director=True)
            self.assertEqual(before['state'],self.state()['state'])
        finally:
            if old:server.os.environ['ANTHROPIC_API_KEY']=old
    def test_ai_adapter_contract_with_explicit_test_fixture(self):
        original=server.ai_reply
        try:
            server.ai_reply=lambda *a,**k:{'narration':'Respuesta de prueba de integración; no es IA real.','proposals':[]}
            self.action('character',character={'name':'Aria'});self.action('talk',text='Busco a la posadera',director=True)
            self.assertEqual(self.state()['state']['messages'][-1]['kind'],'director')
        finally:server.ai_reply=original
    def test_confirmed_ai_action_replay_does_not_call_provider_again(self):
        with patch.object(server,'ai_reply',return_value={'narration':'Fixture; no es IA real','proposals':[]}) as provider:
            body=self.action('talk',text='Exploro',director=True)
            self.assertTrue(self.request('/api/action',body,self.token)['duplicate'])
            self.assertEqual(provider.call_count,1)
    def test_reference_search_page(self):
        results=self.request('/api/search?q=diagonales&book=reglas',token=self.token)
        self.assertTrue(any(int(r['page'])==194 for r in results))
        self.assertIn('diagonal',next(r['text'] for r in results if int(r['page'])==194).lower())

    def test_requested_check_is_atomic_replay_safe_and_owned(self):
        guest=self.request('/api/join',{'name':'Luis','invite':self.state()['invite']})['token']
        self.action('character',guest,character={'name':'Aria','saves':[5,2,1]})
        cid=self.state()['state']['characters'][0]['id']
        with patch.object(server,'ai_reply') as provider:
            self.action('request_check',character=cid,checkKind='save',key='fort',dc=15,reason='Resistir')
            request=self.state()['state']['pending'][0]['check']['id']
            with patch('engine.dice',return_value=[10]) as rng:
                body=self.action('check',guest,request=request)
                self.assertTrue(self.request('/api/action',body,guest)['duplicate']);self.assertEqual(rng.call_count,1)
            provider.assert_not_called()
        state=self.state()['state'];self.assertEqual(state['pending'],[])
        self.assertEqual(state['messages'][-1]['check']['total'],15)
        self.assertTrue(state['messages'][-1]['check']['success'])
        with self.assertRaises(urllib.error.HTTPError):self.action('check',guest,request=request)

    def test_director_checks_validate_ownership_deduplicate_and_fallback(self):
        guest=self.request('/api/join',{'name':'Luis','invite':self.state()['invite']})['token']
        self.action('character',character={'name':'Anfitrión'})
        self.action('character',guest,character={'name':'Aria'})
        host_id,guest_id=[c['id'] for c in self.state()['state']['characters']]
        suggestion={'character':guest_id,'kind':'ability','key':'str','dc':15,'reason':'CD adjudicada: abrir la puerta'}
        result={'narration':'Fixture: intenta abrir la puerta; espera la tirada.','proposals':[],
            'checks':[suggestion,{**suggestion,'character':host_id},{**suggestion,'kind':'skill','key':'No preparada'}]}
        with patch.object(server,'ai_reply',return_value=result) as provider:
            self.action('talk',guest,character=guest_id,text='Intento abrir la puerta',director=True)
            self.assertEqual(provider.call_args.kwargs['check_actors'],[guest_id])
            self.action('talk',guest,character=guest_id,text='Espero mi tirada',director=True)
        pending=self.state()['state']['pending'];requests=[p for p in pending if p.get('check')]
        self.assertEqual(len(requests),1);self.assertEqual(requests[0]['check']['character'],guest_id)
        self.assertEqual(len([p for p in pending if not p.get('check')]),4)
        self.assertIn('Claude',requests[0]['source'])

    def test_private_reader_pages_and_etag_require_auth_even_with_cached_page(self):
        from test_reader_support import fixture_reader
        reader=fixture_reader()
        with patch.object(server,'READER',reader),patch.object(server,'open_book') as original:
            info=self.request('/api/book-info?book=reglas',token=self.token)
            path='/book-pages/reglas/'+info['revision']+'/1.jpg'
            req=urllib.request.Request(self.url+path,headers={'Authorization':'Bearer '+self.token})
            with urllib.request.urlopen(req) as response:
                body=response.read();etag=response.headers['ETag']
                self.assertTrue(body.startswith(b'\xff\xd8'));self.assertEqual(response.headers['Content-Type'],'image/jpeg')
                self.assertIn('private',response.headers['Cache-Control'])
            req.add_header('If-None-Match',etag)
            with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(req)
            self.assertEqual(error.exception.code,304);error.exception.close()
            with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(self.url+path)
            self.assertEqual(error.exception.code,401);error.exception.close()
            with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/book-info?book=reglas')
            self.assertEqual(error.exception.code,401);error.exception.close()
            original.assert_not_called()
    def test_combat_state_shared_after_assisted_damage(self):
        guest=self.request('/api/join',{'name':'Luis','invite':self.state()['invite']})['token']
        self.action('character',character={'name':'Aria'});cid=self.state()['state']['characters'][0]['id']
        self.action('combat');self.action('move',character=cid,path=[[1,0]],acknowledge=True)
        self.action('manual',reason='Ataque resuelto',resolution='d20 y daño físicos verificados por anfitrión',reference='Resolución de prueba',character=cid,hpDelta=-3,resources='Poción gastada',actionCost='standard')
        public=self.state(guest)['state'];self.assertEqual(public['characters'][0]['hp'],7);self.assertEqual(public['characters'][0]['x'],1);self.assertEqual(public['characters'][0]['resources'],'Poción gastada');self.assertTrue(public['board']['spent'][cid]['standard'])

    def test_automatic_attack_persists_and_replay_never_rolls_or_calls_ai(self):
        guest=self.request('/api/join',{'name':'Luis','invite':self.state()['invite']})['token']
        profile={'flatAc':12,'criticalMin':20,'multiplier':2}
        self.action('character',character={'name':'Aria','owner':self.state(guest)['me']['id'],
            'initiative':100,'attack':4,'damage':'1d6+2','ac':14,'meleeProfile':profile})
        self.action('character',character={'name':'Bandido','enemy':True,'initiative':-100,'maxHp':20,
            'ac':14,'damage':'1d6','meleeProfile':profile})
        self.action('combat');a,b=self.state()['state']['characters']
        with patch('engine.dice',side_effect=[[12],[4]]) as dice,patch.object(server,'ai_reply') as ai:
            body=self.action('attack',guest,character=a['id'],target=b['id'])
            after=self.state(guest)
            self.assertEqual(after['state']['characters'][1]['hp'],14)
            self.assertTrue(after['state']['board']['spent'][a['id']]['standard'])
            self.assertTrue(self.request('/api/action',body,guest)['duplicate'])
            self.assertEqual(dice.call_count,2);ai.assert_not_called()
        self.assertEqual(self.state()['version'],after['version'])
        with patch('engine.dice') as dice:
            with self.assertRaises(urllib.error.HTTPError) as error:
                self.action('attack',guest,character=a['id'],target=b['id'])
            self.assertEqual(error.exception.code,400);error.exception.close();dice.assert_not_called()
        self.assertEqual(self.state(guest)['state'],after['state'])

    def test_enemy_turn_is_one_atomic_action_without_ai_and_replay_is_safe(self):
        guest=self.request('/api/join',{'name':'Luis','invite':self.state()['invite']})['token']
        profile={'flatAc':12,'criticalMin':20,'multiplier':2}
        self.action('character',character={'name':'Aria','owner':self.state(guest)['me']['id'],
            'initiative':100,'attack':4,'damage':'1d6+2','ac':14,'maxHp':20,'meleeProfile':profile})
        self.action('character',character={'name':'Bandido','enemy':True,'initiative':-100,
            'attack':4,'ac':14,'damage':'1d6+2','meleeProfile':profile})
        self.action('combat',automateEnemies=True)
        before=self.state(guest)
        with patch('engine.dice',side_effect=[[12],[4]]) as dice,patch.object(server,'ai_reply') as ai:
            body=self.action('turn',guest);after=self.state(guest)
            self.assertEqual(after['version'],before['version']+1)
            self.assertEqual(after['state']['characters'][0]['hp'],14)
            self.assertEqual(after['state']['board']['round'],2)
            self.assertTrue(self.request('/api/action',body,guest)['duplicate'])
            self.assertEqual(dice.call_count,2);ai.assert_not_called()
        self.assertEqual(self.state(guest)['state'],after['state'])
        before=self.state(guest)
        with self.assertRaises(urllib.error.HTTPError) as error:self.action('automation',guest,enabled=False)
        self.assertEqual(error.exception.code,403);error.exception.close()
        self.assertEqual(self.state(guest)['version'],before['version'])

if __name__=='__main__':unittest.main()
