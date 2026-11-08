import copy
import json
import secrets
import unittest
import urllib.error
from unittest.mock import patch
import server
import campaign_world
from firebase_store import FirestoreStore,Unavailable
import test_campaign_world_http as transport
import test_adventure_chapters_context as chapter_fixture
from test_character_builder import choices
from test_rule_pack_world import npc


class AdventureChapterHTTPTests(unittest.TestCase):
    setUpClass=classmethod(transport.CampaignWorldHTTPTests.setUpClass.__func__)
    tearDownClass=classmethod(transport.CampaignWorldHTTPTests.tearDownClass.__func__)
    setUp=transport.CampaignWorldHTTPTests.setUp
    request=transport.CampaignWorldHTTPTests.request
    state=transport.CampaignWorldHTTPTests.state
    action=transport.CampaignWorldHTTPTests.action
    reply=transport.CampaignWorldHTTPTests.reply

    def prepare(self,*,guest_owner=False):
        guest=self.request('/api/join',{'name':'Luis','invite':self.state()['invite']})['token']
        owner=guest if guest_owner else None
        self.action('create_character',owner,choices=choices());actor=self.state()['state']['characters'][0]['id']
        with patch.object(server,'ai_reply',return_value=self.reply({'npcs':[npc()],'places':[],'relationships':[]})):
            self.action('start_adventure',moduleId='la-carta-perdida',worldMemoryContract=campaign_world.CONTRACT,captureContract='pf-director-action-1')
        for opportunity in ('rastro','carta'):self.action('investigate',owner,character=actor,opportunity=opportunity,method='take20')
        return actor,guest

    def next_body(self):
        before=self.state();return {'id':secrets.token_hex(12),'version':before['version'],'type':'next_adventure',
            'premise':'Quiero averiguar quién dejó el sello de la archivera aquí.','worldMemoryContract':campaign_world.CONTRACT,'captureContract':'pf-director-action-1'}

    def next_reply(self,body):
        state=self.state()['state'];state['adventureChapterTransition']={'premise':body['premise']}
        return chapter_fixture.reply(state)

    def test_next_chapter_failed_commit_cold_retry_duplicate_secrets_copy_and_clock(self):
        actor,guest=self.prepare();before=self.state();original=self.request('/api/export',{});body=self.next_body();value=self.next_reply(body)
        value['worldUpdates']={'npcs':[npc(public='Arda recuerda la carta y el objetivo nuevo.')],'places':[],'relationships':[]}
        with patch.object(server,'ai_reply',return_value=value) as provider:
            with patch.object(server.STORE,'commit',side_effect=Unavailable('Interrupted chapter commit')):
                with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/action',body)
            self.assertEqual(error.exception.code,503);error.exception.close();self.assertEqual(provider.call_count,1)
        self.assertEqual(self.state(),before);previous=server.STORE
        if isinstance(previous,FirestoreStore):
            server.STORE=FirestoreStore.from_environment();server.STORE.prefix=previous.prefix
        try:
            with patch.object(server,'ai_reply',side_effect=AssertionError('Chapter retry called provider')),patch('game_randomness.draw',side_effect=AssertionError('Chapter rolled')):
                self.request('/api/action',body);after=self.state();self.assertTrue(self.request('/api/action',body)['duplicate']);self.assertEqual(self.state(),after)
            for key in ('characters','board','worldTime','private','secrets','directorNotes'):self.assertEqual(after['state'].get(key),before['state'].get(key))
            self.assertEqual(after['state']['adventureChaptersView']['current'],2);self.assertTrue(after['state']['adventureChaptersView']['clockUncertain'])
            self.assertEqual(after['state']['moduleProgress']['searchActions'],0);self.assertFalse(after['state']['moduleProgress']['completed'])
            self.assertEqual(after['state']['adventureModule']['premise'],body['premise'])
            self.assertEqual(after['state']['adventureModule']['location'],before['state']['location'])
            self.assertEqual(len([m for m in after['state']['messages'] if m.get('adventureChapterStart')]),1)
            self.assertEqual(len([m for m in after['state']['messages'] if m.get('kind')=='action' and body['premise'] in m['text']]),1)
            self.assertNotIn('PRIVATE',json.dumps(self.state(guest)));self.assertNotIn('adventureChapters',after['state'])
            exported=self.request('/api/export',{});entry=exported['state']['adventureChapters']['completed'][0]
            self.assertEqual(entry['module'],original['state']['adventureModule']);self.assertEqual(entry['progress'],original['state']['moduleProgress'])
            self.action('import',campaign=exported);self.assertEqual(self.state()['state']['adventureChaptersView'],after['state']['adventureChaptersView'])
            for opportunity in ('search-1','search-2'):self.action('investigate',character=actor,opportunity=opportunity,method='take20')
            self.assertTrue(self.state()['state']['moduleProgress']['completed']);self.assertIsNone(self.state()['state']['nextAdventureView']['reason'])
            for case in ('history','marker','unfinished-transition'):
                altered=copy.deepcopy(self.request('/api/export',{}))
                if case=='history':altered['state']['adventureChapters']['completed'][0]['summary']='Alterado'
                elif case=='marker':altered['state']['messages']=[m for m in altered['state']['messages'] if 'adventureChapterStart' not in m]
                else:altered['state']['adventureChapterTransition']={'format':'unfinished'}
                baseline=self.state()
                with self.subTest(case=case),self.assertRaises(urllib.error.HTTPError) as error:self.action('import',campaign=altered)
                self.assertEqual(error.exception.code,400);error.exception.close();self.assertEqual(self.state(),baseline)
        finally:server.STORE=previous

    def test_model_cannot_teleport_in_new_chapter_or_replace_original_after_rejection(self):
        self.prepare();before=self.state();body=self.next_body();value=self.next_reply(body);value['generatedAdventure']['location']='Un bosque lejano'
        with patch.object(server,'ai_reply',return_value=value):
            with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/action',body)
        self.assertEqual(error.exception.code,400);error.exception.close();self.assertEqual(self.state(),before)

    def test_host_cannot_choose_for_guest_and_guest_does_not_gain_campaign_preparation_permissions(self):
        _,guest=self.prepare(guest_owner=True);before=self.state();body=self.next_body()
        with patch.object(server,'ai_reply',side_effect=AssertionError('Unauthorized chapter called provider')):
            for token in (None,guest):
                with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/action',body,token)
                self.assertEqual(error.exception.code,403);error.exception.close();self.assertEqual(self.state(),before)

    def test_archive_capacity_is_explained_in_view_before_form_or_provider(self):
        self.prepare();before=self.state();body=self.next_body()
        with patch('adventure_chapters.MAX_ARCHIVE_BYTES',100),patch.object(server,'ai_reply',side_effect=AssertionError('Full archive called provider')):
            self.assertIn('límite',self.state()['state']['nextAdventureView']['reason'])
            with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/action',body)
            self.assertEqual(error.exception.code,400);error.exception.close()
        self.assertEqual(self.state(),before)
