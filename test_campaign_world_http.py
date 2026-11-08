import copy
import json
import secrets
import unittest
import urllib.error
from unittest.mock import patch
import server
import campaign_world as world
from firebase_store import FirestoreStore,Unavailable
import test_pf_night_rest_http as transport
from test_character_builder import choices
from test_rule_pack_world import npc,place,relationship


class CampaignWorldHTTPTests(unittest.TestCase):
    setUpClass=classmethod(transport.NightRestHTTPTests.setUpClass.__func__)
    tearDownClass=classmethod(transport.NightRestHTTPTests.tearDownClass.__func__)
    request=transport.NightRestHTTPTests.request
    state=transport.NightRestHTTPTests.state
    action=transport.NightRestHTTPTests.action

    def setUp(self):
        configured=patch.dict('os.environ',{'ANTHROPIC_API_KEY':'fixture-never-sent'})
        configured.start();self.addCleanup(configured.stop);transport.NightRestHTTPTests.setUp(self)

    def reply(self,updates):
        return {'narration':'Arda guarda memoria de la conversación, sin descubrir pistas.','proposals':[],
            'memory':{'summary':'La investigación sigue abierta.','preparation':'PRIVATE-PREPARATION'},'worldUpdates':updates}

    def prepare(self):
        guest=self.request('/api/join',{'name':'Luis','invite':self.state()['invite']})['token']
        self.action('create_character',choices=choices());actor=self.state()['state']['characters'][0]['id']
        updates={'npcs':[npc(),npc('oculta',name='SECRET-NAME',known=False,public='')],'places':[place()],'relationships':[]}
        with patch.object(server,'ai_reply',return_value=self.reply(updates)) as provider:
            self.action('start_adventure',moduleId='la-carta-perdida',worldMemoryContract=world.CONTRACT)
        self.assertEqual(provider.call_count,1)
        return actor,guest

    def test_private_memory_durable_retry_duplicate_copy_and_two_sessions(self):
        actor,guest=self.prepare();before=self.state();self.assertEqual(before['state']['campaignWorldView']['revision'],1)
        self.assertNotIn('campaignWorld',before['state']);self.assertNotIn('SECRET-NAME',json.dumps(self.state(guest)))
        self.assertNotIn('PRIVATE',json.dumps(self.state(guest)));self.assertEqual(len(self.state(guest)['state']['campaignWorldView']['npcs']),1)
        updates={'npcs':[npc(public='Arda recuerda vuestro saludo.')],'places':[],'relationships':[relationship()]}
        result=self.reply(updates);body={'id':secrets.token_hex(12),'version':before['version'],'type':'talk','kind':'dialogue','character':actor,'text':'Recuerdo nuestro saludo a Arda.','director':True,'captureContract':'pf-director-action-1'}
        with patch.object(server,'search',return_value=[]),patch.object(server,'ai_reply',return_value=result) as provider:
            with patch.object(server.STORE,'commit',side_effect=Unavailable('Interrupted world commit')):
                with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/action',body)
            self.assertEqual(error.exception.code,503);error.exception.close();self.assertEqual(provider.call_count,1)
        self.assertEqual(self.state(),before);previous=server.STORE
        if isinstance(previous,FirestoreStore):
            server.STORE=FirestoreStore.from_environment();server.STORE.prefix=previous.prefix
        try:
            with patch.object(server,'search',return_value=[]),patch.object(server,'ai_reply',side_effect=AssertionError('World retry called provider')):
                self.request('/api/action',body);after=self.state();self.assertTrue(self.request('/api/action',body)['duplicate']);self.assertEqual(self.state(),after)
            self.assertEqual(after['state']['campaignWorldView']['revision'],2)
            self.assertEqual(after['state']['campaignWorldView']['relationships'][0]['toName'],'Archivo')
            for key in ('characters','board','location','worldTime','goal','objectives','moduleProgress'):self.assertEqual(after['state'][key],before['state'][key])
            self.assertNotIn('PRIVATE',json.dumps(self.state(guest)));exported=self.request('/api/export',{})
            self.assertEqual(exported['state']['campaignWorld']['npcs'][1]['name'],'SECRET-NAME')
            self.action('import',campaign=exported);self.assertEqual(self.state()['state']['campaignWorldView'],after['state']['campaignWorldView'])
            altered=copy.deepcopy(exported);altered['state']['campaignWorld']['npcs'][0]['hp']=100;baseline=self.state()
            with self.assertRaises(urllib.error.HTTPError) as error:self.action('import',campaign=altered)
            self.assertEqual(error.exception.code,400);error.exception.close();self.assertEqual(self.state(),baseline)
        finally:server.STORE=previous

    def test_invalid_contract_and_missing_initial_notes_do_not_change_campaign(self):
        self.action('create_character',choices=choices());before=self.state()
        with patch.object(server,'ai_reply',side_effect=AssertionError('Invalid contract called provider')):
            with self.assertRaises(urllib.error.HTTPError) as error:self.action('start_adventure',moduleId='la-carta-perdida',worldMemoryContract='unknown')
        self.assertEqual(error.exception.code,400);error.exception.close();self.assertEqual(self.state(),before)
        result=self.reply({'npcs':[],'places':[],'relationships':[]});result.pop('worldUpdates')
        with patch.object(server,'ai_reply',return_value=result):
            with self.assertRaises(urllib.error.HTTPError) as error:self.action('start_adventure',moduleId='la-carta-perdida',worldMemoryContract=world.CONTRACT)
        self.assertEqual(error.exception.code,400);error.exception.close();self.assertEqual(self.state(),before)
