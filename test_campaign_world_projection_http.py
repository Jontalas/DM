import copy
import secrets
import unittest
import urllib.error
from unittest.mock import patch
import server
import claude_dm
from firebase_store import FirestoreStore,Unavailable
import test_campaign_world_http as transport
from test_campaign_world_context_selection import full_world
from test_character_builder import choices


class WorldProjectionHTTPTests(unittest.TestCase):
    setUpClass=classmethod(transport.CampaignWorldHTTPTests.setUpClass.__func__)
    tearDownClass=classmethod(transport.CampaignWorldHTTPTests.tearDownClass.__func__)
    setUp=transport.CampaignWorldHTTPTests.setUp
    request=transport.CampaignWorldHTTPTests.request
    state=transport.CampaignWorldHTTPTests.state
    action=transport.CampaignWorldHTTPTests.action
    reply=transport.CampaignWorldHTTPTests.reply

    def prepare(self):
        self.action('create_character',choices=choices());actor=self.state()['state']['characters'][0]['id']
        exported=self.request('/api/export',{});exported['state']['campaignWorld']=full_world();self.action('import',campaign=exported)
        with patch.object(server,'ai_reply',return_value=self.reply({'npcs':[],'places':[],'relationships':[]})):
            self.action('start_adventure',moduleId='la-carta-perdida')
        return actor

    def replay(self,*,historical):
        actor=self.prepare();before=self.state();full=self.request('/api/export',{})['state']['campaignWorld']
        person=copy.deepcopy(full['npcs'][0 if historical else 3]);person['public']='Recuerda el saludo sin perder su preparación privada.'
        result=self.reply({'npcs':[person],'places':[],'relationships':[]})
        body={'id':secrets.token_hex(12),'version':before['version'],'type':'talk','kind':'dialogue','character':actor,
            'text':'Pregunto a Persona 3.','director':True,'captureContract':'pf-director-action-1'}
        original=claude_dm.build_context
        def previous_context(state,*args,**kwargs):
            context=original(state,*args,**kwargs)
            if 'campaignWorld' in state:
                context['directorKnowledge']['campaignWorld']=copy.deepcopy(state['campaignWorld']);context.pop('worldMemorySelection',None)
            return context
        build=patch.object(claude_dm,'build_context',side_effect=previous_context) if historical else patch.object(claude_dm,'build_context',wraps=original)
        with build,patch.object(server,'search',return_value=[]),patch.object(server,'ai_reply',return_value=result) as provider:
            with patch.object(server.STORE,'commit',side_effect=Unavailable('Interrupted projected memory commit')):
                with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/action',body)
            self.assertEqual(error.exception.code,503);error.exception.close();self.assertEqual(provider.call_count,1)
        self.assertEqual(self.state(),before);previous=server.STORE
        if isinstance(previous,FirestoreStore):
            server.STORE=FirestoreStore.from_environment();server.STORE.prefix=previous.prefix
        try:
            with patch.object(server,'search',return_value=[]),patch.object(server,'ai_reply',side_effect=AssertionError('Projection retry called provider')):
                self.request('/api/action',body);after=self.state();self.assertTrue(self.request('/api/action',body)['duplicate']);self.assertEqual(self.state(),after)
            actual=self.request('/api/export',{})['state']['campaignWorld'];expected=copy.deepcopy(full)
            expected['npcs'][0 if historical else 3]=person;expected['revision']+=1
            self.assertEqual(actual,expected)
            for key in ('characters','board','location','worldTime','moduleProgress'):self.assertEqual(after['state'][key],before['state'][key])
            self.action('import',campaign=self.request('/api/export',{}));self.assertEqual(self.request('/api/export',{})['state']['campaignWorld'],expected)
        finally:server.STORE=previous

    def test_projected_response_survives_commit_failure_with_full_unchanged_other_notes(self):self.replay(historical=False)
    def test_previous_complete_capture_replays_without_new_provider_or_restricting_old_notes(self):self.replay(historical=True)
