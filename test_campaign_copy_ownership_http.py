"""Same-room restoration keeps current member ownership; legacy import stays explicit."""
import copy
import secrets
import unittest
import urllib.error
from unittest.mock import patch
import server
from firebase_store import FirestoreStore,Unavailable
from test_character_builder import choices
import test_group_director_concurrency_http as transport
import test_pf_night_rest_http as empty_transport


class CampaignCopyOwnershipHTTPTests(unittest.TestCase):
    setUpClass=classmethod(transport.GroupDirectorConcurrencyHTTPTests.setUpClass.__func__)
    tearDownClass=classmethod(transport.GroupDirectorConcurrencyHTTPTests.tearDownClass.__func__)
    setUp=transport.GroupDirectorConcurrencyHTTPTests.setUp
    request=transport.GroupDirectorConcurrencyHTTPTests.request
    state=transport.GroupDirectorConcurrencyHTTPTests.state
    action=transport.GroupDirectorConcurrencyHTTPTests.action

    def test_same_campaign_failed_commit_cold_retry_preserves_owners_privacy_and_pending(self):
        self.action('talk',self.guest,kind='private',text='PRIVATE-GUEST-NOTE',director=False)
        self.action('investigate',self.guest,character=self.guest_actor,opportunity='rastro',method='take20')
        self.action('investigate',character=self.host_actor,opportunity='carta')
        saved=self.state();exported=self.request('/api/export',{})
        self.assertEqual(exported['sourceCampaignId'],saved['id'])
        self.assertNotIn('token',exported);self.assertNotIn('invite',exported)
        self.action('talk',kind='ooc',text='Este mensaje posterior no pertenece a la copia.',director=False)
        before=self.state();body={'id':secrets.token_hex(12),'version':before['version'],
                                 'type':'restore_campaign_copy','campaign':exported}
        with (patch.object(server,'ai_reply',side_effect=AssertionError('Copy called provider')),
              patch('game_randomness.draw',side_effect=AssertionError('Copy rolled dice'))):
            with patch.object(server.STORE,'commit',side_effect=Unavailable('Interrupted copy restoration')):
                with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/action',body)
            self.assertEqual(error.exception.code,503);error.exception.close();self.assertEqual(self.state(),before)
            previous=server.STORE
            if isinstance(previous,FirestoreStore):
                server.STORE=FirestoreStore.from_environment();server.STORE.prefix=previous.prefix
            try:
                self.request('/api/action',body);restored=self.state()
                self.assertTrue(self.request('/api/action',body)['duplicate']);self.assertEqual(self.state(),restored)
            finally:server.STORE=previous
        self.assertEqual(restored['state']['characters'],saved['state']['characters'])
        self.assertEqual(restored['state']['pending'],saved['state']['pending'])
        self.assertEqual(restored['state']['moduleProgress'],saved['state']['moduleProgress'])
        guest=self.state(self.guest);self.assertIn('PRIVATE-GUEST-NOTE',str(guest));self.assertNotIn('PRIVATE-HOST-NOTE',str(guest))
        self.assertEqual(guest['state']['characters'],saved['state']['characters'])
        request=saved['state']['pending'][0]['check']['id']
        self.action('check',request=request,method='take20')
        self.assertTrue(self.state(self.guest)['state']['moduleProgress']['completed'])

    def test_legacy_and_other_campaign_import_reassign_but_new_restore_rejects_foreign_origin(self):
        exported=self.request('/api/export',{});other=self.request('/api/create',{'title':'Otra sala','player':'Mara'})['token']
        before=self.state(other)
        with self.assertRaises(urllib.error.HTTPError) as error:self.action('restore_campaign_copy',other,campaign=exported)
        self.assertEqual(error.exception.code,400);error.exception.close();self.assertEqual(self.state(other),before)
        self.action('import',other,campaign=exported);imported=self.state(other)
        self.assertTrue(all(c['owner']==imported['me']['id'] for c in imported['state']['characters']))
        legacy=copy.deepcopy(exported);legacy.pop('sourceCampaignId',None)
        self.action('import',campaign=legacy);imported=self.state()
        self.assertTrue(all(c['owner']==imported['me']['id'] for c in imported['state']['characters']))

    def test_guest_missing_origin_and_unknown_owner_do_not_create_memberships(self):
        exported=self.request('/api/export',{});before=self.state()
        with self.assertRaises(urllib.error.HTTPError) as error:self.action('restore_campaign_copy',self.guest,campaign=exported)
        self.assertEqual(error.exception.code,403);error.exception.close();self.assertEqual(self.state(),before)
        missing=copy.deepcopy(exported);missing.pop('sourceCampaignId',None)
        with self.assertRaises(urllib.error.HTTPError) as error:self.action('restore_campaign_copy',campaign=missing)
        self.assertEqual(error.exception.code,400);error.exception.close();self.assertEqual(self.state(),before)
        changed=copy.deepcopy(exported);next(c for c in changed['state']['characters'] if c['id']==self.guest_actor)['owner']='unknown-former-member'
        self.action('restore_campaign_copy',campaign=changed);after=self.state()
        self.assertEqual(next(c for c in after['state']['characters'] if c['id']==self.guest_actor)['owner'],after['me']['id'])
        self.assertEqual(after['players'],before['players'])

    def test_verified_npc_keeps_director_and_other_ruleset_is_not_advertised_as_supported(self):
        solo=self.request('/api/create',{'title':'Copia con PNJ','player':'Mara'})['token']
        with patch.object(server,'ai_reply',side_effect=AssertionError('Copy scope called provider')):
            self.action('create_character',solo,choices=choices());actor=self.state(solo)['state']['characters'][0]['id']
            self.action('enter_pf_encounter',solo,encounter='patio-del-peaje',encounterVersion='1.15.0',character=actor)
            self.action('choose_pf_encounter',solo,choice='parley');before=self.state(solo)
            exported=self.request('/api/export',{},solo);self.action('restore_campaign_copy',solo,campaign=exported)
        after=self.state(solo);self.assertEqual(after['state']['characters'],before['state']['characters'])
        npc=next(c for c in after['state']['characters'] if c.get('npcCreation'));self.assertEqual(npc['owner'],'director')
        other=self.request('/api/create',{'title':'Otro módulo','player':'Mara','ruleset':'rule-pack'})['token']
        before=self.state(other);exported=self.request('/api/export',{},other)
        with self.assertRaises(urllib.error.HTTPError) as error:self.action('restore_campaign_copy',other,campaign=exported)
        self.assertEqual(error.exception.code,400);error.exception.close();self.assertEqual(self.state(other),before)


class CampaignCopyShapeHTTPTests(unittest.TestCase):
    setUpClass=classmethod(empty_transport.NightRestHTTPTests.setUpClass.__func__)
    tearDownClass=classmethod(empty_transport.NightRestHTTPTests.tearDownClass.__func__)
    setUp=empty_transport.NightRestHTTPTests.setUp
    request=empty_transport.NightRestHTTPTests.request
    state=empty_transport.NightRestHTTPTests.state
    action=empty_transport.NightRestHTTPTests.action

    def test_malformed_copies_leave_the_current_campaign_unchanged(self):
        changes={
            'terrain-list':lambda s:s['board'].update(terrain=[]),
            'duplicate-character':lambda s:s['characters'].append(copy.deepcopy(s['characters'][0])),
            'missing-abilities':lambda s:s['characters'][0].update(abilities=[]),
            'non-text-name':lambda s:s['characters'][0].update(name=None),
            'non-text-message':lambda s:s.update(messages=[{'kind':'rules','speaker':'Motor','text':{}}]),
            'objectives-object':lambda s:s.update(objectives={}),
            'empty-active-order':lambda s:s['board'].update(active=True,order=[]),
            'unknown-active-character':lambda s:s['board'].update(active=True,order=[{'id':'missing','roll':10,'modifier':0}]),
            'nonfinite-extension':lambda s:s.update(futureExtension={'value':float('nan')}),
        }
        for route in ('import','restore_campaign_copy'):
            for label,mutate in changes.items():
                with self.subTest(route=route,shape=label):
                    self.token=self.request('/api/create',{'player':'Ana'})['token']
                    self.action('create_character',choices=choices())
                    exported=self.request('/api/export',{});mutate(exported['state']);before=self.state()
                    with (patch.object(server,'ai_reply',side_effect=AssertionError('Copy called provider')),
                          patch('game_randomness.draw',side_effect=AssertionError('Copy rolled dice'))):
                        with self.assertRaises(urllib.error.HTTPError) as error:self.action(route,campaign=exported)
                    self.assertEqual(error.exception.code,400);error.exception.close();self.assertEqual(self.state(),before)

    def test_legacy_manual_sheet_and_optional_fields_remain_importable(self):
        self.action('character',character={'name':'Ficha manual','abilities':[10]*6,'maxHp':8,'hp':8})
        exported=self.request('/api/export',{});exported.pop('sourceCampaignId',None)
        exported['state'].pop('directorNotes',None);exported['state'].pop('directorMemory',None)
        original=copy.deepcopy(exported['state']['characters']);self.action('import',campaign=exported)
        self.assertEqual(self.state()['state']['characters'],original)
