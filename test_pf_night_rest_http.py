"""Real HTTP/Waitress and optional Firestore emulator; no provider calls."""
import copy
import json
import secrets
import threading
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch
import server
from firebase_store import FirestoreStore,Unavailable
from test_support import make_store
from test_character_builder import choices


class NightRestHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from waitress.server import create_server
        from wsgi import application
        cls.previous=server.STORE;server.STORE=make_store()
        cls.http=create_server(application,host='127.0.0.1',port=0,threads=4)
        cls.base='http://127.0.0.1:'+str(cls.http.effective_port)
        cls.thread=threading.Thread(target=cls.http.run,daemon=True);cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.http.close();server.STORE=cls.previous

    def request(self,path,body=None,token=None):
        req=urllib.request.Request(self.base+path,data=json.dumps(body).encode() if body is not None else None,
            headers={'Content-Type':'application/json','Authorization':'Bearer '+(token or getattr(self,'token',''))})
        with urllib.request.urlopen(req,timeout=20) as response:return json.load(response)

    def state(self,token=None):return self.request('/api/state',token=token)

    def action(self,action_type,token=None,**data):
        body={'id':secrets.token_hex(12),'version':self.state(token)['version'],'type':action_type,**data}
        self.request('/api/action',body,token);return body

    def setUp(self):self.token=self.request('/api/create',{'title':'Noche técnica','player':'Ana'})['token']

    def prepare(self,token=None,wounded=False,version='1.5.0',armor=None):
        selected=choices()
        if armor:selected['armor']=armor
        self.action('create_character',token,choices=selected)
        actor=self.state(token)['state']['characters'][0]['id']
        self.action('enter_pf_encounter',token,encounter='patio-del-peaje',encounterVersion=version,character=actor)
        if wounded:
            with patch('game_randomness.draw',side_effect=[1,20,18,3]),patch('game_randomness.initiative_tie',return_value=0):
                self.action('choose_pf_encounter',token,choice='combat')
            npc=self.state(token)['state']['characters'][1]['id']
            with patch('game_randomness.draw',side_effect=[20,20,8,8]):self.action('attack',token,character=actor,target=npc)
        else:self.action('choose_pf_encounter',token,choice='parley')

    def test_failed_commit_fresh_client_retry_duplicate_and_copy_preserve_the_same_night(self):
        self.prepare(wounded=True);before=self.state()
        self.assertEqual(before['state']['characters'][0]['hp'],13)
        body={'id':secrets.token_hex(12),'version':before['version'],'type':'rest_pf_night'}
        with patch.object(server.STORE,'commit',side_effect=Unavailable('Interrupted rest commit')):
            with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/action',body)
        self.assertEqual(error.exception.code,503);error.exception.close();self.assertEqual(self.state(),before)
        previous=server.STORE
        if isinstance(previous,FirestoreStore):
            server.STORE=FirestoreStore.from_environment();server.STORE.prefix=previous.prefix
        try:
            with (patch.object(server,'ai_reply',side_effect=AssertionError('Rest called provider')),
                  patch('game_randomness.draw',side_effect=AssertionError('Rest rolled dice'))):
                self.request('/api/action',body);after=self.state()
                self.assertTrue(self.request('/api/action',body)['duplicate']);self.assertEqual(self.state(),after)
            self.assertEqual(after['state']['characters'][0]['hp'],14)
            self.assertNotIn('pfNightRest',after['state']);self.assertTrue(after['state']['pfNightRestView']['completed'])
            exported=self.request('/api/export',{});self.assertIn('pfNightRest',exported['state'])
            exported['state']['pfNightRestView']={'completed':False,'reason':'INJECTED-VIEW'}
            self.action('import',campaign=exported)
            restored=self.state()['state'];self.assertEqual(restored['characters'],after['state']['characters'])
            self.assertTrue(restored['pfNightRestView']['completed'])
            self.assertEqual(restored['worldTime'],after['state']['worldTime'])
            self.action('continue_pf_encounter');self.assertEqual(self.state()['state']['boardScenes']['current'],'patio')
            self.assertEqual(self.state()['state']['characters'][0]['hp'],14)
        finally:server.STORE=previous

    def test_owner_guest_can_sleep_host_cannot_decide_for_them_and_rejected_copies_are_atomic(self):
        guest=self.request('/api/join',{'name':'Luis','invite':self.state()['invite']})['token']
        self.prepare(guest);before=self.state()
        with self.assertRaises(urllib.error.HTTPError) as error:self.action('rest_pf_night')
        self.assertEqual(error.exception.code,403);error.exception.close();self.assertEqual(self.state(),before)
        self.action('rest_pf_night',guest);exported=self.request('/api/export',{})
        for change in ('hp','time','orphan'):
            changed=copy.deepcopy(exported)
            if change=='hp':changed['state']['pfNightRest']['result']['healing']['amount']=99
            elif change=='time':changed['state']['pfNightRest']['result']['seconds']=1
            else:del changed['state']['pfNightRest']
            before=self.state()
            with self.assertRaises(urllib.error.HTTPError) as error:self.action('import',campaign=changed)
            self.assertEqual(error.exception.code,400);error.exception.close();self.assertEqual(self.state(),before)

    def test_global_goal_sleep_and_revisits_survive_copy_and_duplicate_return(self):
        self.prepare(version='1.6.0');self.action('rest_pf_night');self.action('continue_pf_encounter')
        actor=self.state()['state']['characters'][0]['id']
        for clue in ('registro','recibo'):self.action('investigate',character=actor,opportunity=clue,method='take20')
        self.action('travel_scene',exit='almacen')
        for clue in ('bulto','recepcion'):self.action('investigate',character=actor,opportunity=clue,method='take20')
        body=self.action('travel_scene',exit='patio');returned=self.state()
        self.assertTrue(returned['state']['adventureRouteView']['completed'])
        self.assertEqual(returned['state']['boardScenes']['current'],'patio')
        self.assertTrue(self.request('/api/action',body)['duplicate']);self.assertEqual(self.state(),returned)
        exported=self.request('/api/export',{});self.action('import',campaign=exported)
        self.assertEqual(self.state()['state']['worldTime'],returned['state']['worldTime'])
        self.assertTrue(self.state()['state']['adventureRouteView']['completed'])
        altered=copy.deepcopy(exported);altered['state']['adventureRoute']['completion']={'scene':'patio','requires':['recibo']}
        before=self.state()
        with self.assertRaises(urllib.error.HTTPError) as error:self.action('import',campaign=altered)
        self.assertEqual(error.exception.code,400);error.exception.close();self.assertEqual(self.state(),before)

    def test_armor_preparation_failed_commit_recovers_the_same_timing_and_equipment(self):
        self.prepare(wounded=True,version='1.7.0',armor='scale');before=self.state()
        self.assertEqual(before['state']['characters'][0]['hp'],13)
        self.assertEqual(before['state']['pfNightRestView']['armorPlan'],'remove-and-reequip')
        body={'id':secrets.token_hex(12),'version':before['version'],'type':'rest_pf_night','armorPlan':'remove-and-reequip'}
        with patch.object(server.STORE,'commit',side_effect=Unavailable('Interrupted prepared rest')):
            with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/action',body)
        self.assertEqual(error.exception.code,503);error.exception.close();self.assertEqual(self.state(),before)
        previous=server.STORE
        if isinstance(previous,FirestoreStore):
            server.STORE=FirestoreStore.from_environment();server.STORE.prefix=previous.prefix
        try:
            with patch.object(server,'ai_reply',side_effect=AssertionError('Armor preparation called provider')):
                self.request('/api/action',body);after=self.state();self.assertTrue(self.request('/api/action',body)['duplicate'])
            expected=copy.deepcopy(before['state']['characters']);expected[0]['hp']=14
            self.assertEqual(after['state']['characters'],expected)
            self.assertEqual(after['state']['pfNightRestView']['result']['seconds'],29100)
            exported=self.request('/api/export',{});self.action('import',campaign=exported)
            self.assertEqual(self.state()['state']['characters'],expected)
            self.assertEqual(self.state()['state']['worldTime'],after['state']['worldTime'])
        finally:server.STORE=previous

    def test_nullable_optional_encounter_can_be_imported_read_and_replaced_by_a_real_start(self):
        exported=self.request('/api/export',{})
        exported['state'].update(pfEncounter=None,pfNightRest=None,pfContinuation=None)
        self.action('import',campaign=exported);imported=self.state()['state']
        self.assertIsNone(imported['pfEncounter']);self.assertNotIn('pfNightRestView',imported)
        self.prepare(version='1.7.0');self.action('rest_pf_night',armorPlan='keep')
        self.assertTrue(self.state()['state']['pfNightRestView']['completed'])
        inconsistent=self.request('/api/export',{});inconsistent['state']['pfEncounter']=None
        before=self.state()
        with self.assertRaises(urllib.error.HTTPError) as error:self.action('import',campaign=inconsistent)
        self.assertEqual(error.exception.code,400);error.exception.close();self.assertEqual(self.state(),before)
