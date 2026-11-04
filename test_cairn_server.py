"""Real common HTTP path, with experimental availability injected ONLY in tests."""
import copy
import unittest
import urllib.error
from unittest.mock import patch
import rulesets
import server
import test_server
import test_render
from systems import cairn_creator,cairn_adventure

DESCRIPTOR={'id':'cairn-1e','name':'Cairn 1e (test only)','status':'experimental'}


class CairnServerTests(unittest.TestCase):
    request=test_server.IntegrationTests.request
    state=test_server.IntegrationTests.state
    action=test_server.IntegrationTests.action

    @classmethod
    def setUpClass(cls):
        cls.registration=patch.dict(rulesets.SYSTEMS,{'cairn-1e':DESCRIPTOR});cls.registration.start()
        test_server.IntegrationTests.setUpClass.__func__(cls)

    @classmethod
    def tearDownClass(cls):
        try:test_server.IntegrationTests.tearDownClass.__func__(cls)
        finally:cls.registration.stop()

    def setUp(self):
        self.token=self.request('/api/create',{'title':'Cairn test fixture','player':'Ana','ruleset':'cairn-1e'})['token']

    def test_common_transaction_deduplicates_creator_randomness_and_recovers_originals(self):
        with patch.object(cairn_creator.secrets,'randbelow',return_value=0) as rng:
            body=self.action('begin_character',nameTable='female-names')
            self.assertEqual(rng.call_count,35)
            before=self.state()
            self.assertTrue(self.request('/api/action',body,self.token)['duplicate'])
            with self.assertRaises(urllib.error.HTTPError) as error:self.action('begin_character',nameTable='male-names')
            error.exception.close();self.assertEqual(rng.call_count,35)
            self.assertEqual(self.state(),before)
            chosen=self.action('choose_bonus',table='tools')
            self.assertEqual(rng.call_count,36)
            self.assertTrue(self.request('/api/action',chosen,self.token)['duplicate'])
            self.assertEqual(rng.call_count,36)
        restored=self.state();owner=restored['me']['id'];draft=restored['state']['creationDrafts'][owner]
        self.assertEqual(draft['bonus'],{'table':'tools','raw':1})
        self.assertEqual(draft['core'],before['state']['creationDrafts'][owner]['core'])
        self.assertNotIn('board',restored['state']);self.assertNotIn('tokens',restored['state'])

    def confirmed_character(self,token=None):
        with patch.object(cairn_creator.secrets,'randbelow',return_value=0):
            self.action('begin_character',token,nameTable='female-names')
            self.action('choose_bonus',token,table='tools')
        return self.action('confirm_character',token,choices={'weapons':{'weapons':'Dagger'}})

    def test_confirmation_is_server_calculated_owned_and_replay_safe(self):
        with patch.object(cairn_creator.secrets,'randbelow',return_value=0):
            self.action('begin_character',nameTable='female-names');self.action('choose_bonus',table='tools')
        before=self.state()
        with patch.object(cairn_creator.secrets,'randbelow',side_effect=AssertionError('Confirmation rerolled')):
            with self.assertRaises(urllib.error.HTTPError) as error:
                self.action('confirm_character',choices={'weapons':{'weapons':'Dagger'},'abilities':{'STR':18}})
            error.exception.close();self.assertEqual(self.state(),before)
            body=self.action('confirm_character',choices={'weapons':{'weapons':'Dagger'}})
            self.assertTrue(self.request('/api/action',body,self.token)['duplicate'])
            with self.assertRaises(urllib.error.HTTPError) as error:
                self.action('confirm_character',choices={'weapons':{'weapons':'Dagger'}})
            error.exception.close()
        result=self.state();character=result['state']['characters'][0]
        self.assertEqual(len(result['state']['characters']),1)
        self.assertEqual(character['owner'],result['me']['id']);self.assertEqual(character['abilities']['STR'],3)
        self.assertTrue(character['creation']['complete']);self.assertFalse(result['state']['creationDrafts'])
        self.assertEqual(character['creation']['draft']['core'],before['state']['creationDrafts'][result['me']['id']]['core'])

    def test_cairn_scene_save_injury_rest_and_import_use_common_atomic_actions(self):
        self.confirmed_character();character=self.state()['state']['characters'][0]
        with patch.object(server,'ai_reply',side_effect=AssertionError('Scene mechanics called PF model')):
            self.action('start_cairn_adventure',character=character['id'])
            self.action('choose_route',route='pasarela')
            request=self.state()['state']['adventureView']['pending']['id']
            with patch.object(cairn_adventure.secrets,'randbelow',return_value=3) as rng:
                body=self.action('resolve_save',request=request,physical=20)
                self.assertEqual(rng.call_count,1)
                self.assertTrue(self.request('/api/action',body,self.token)['duplicate']);self.assertEqual(rng.call_count,1)
            hurt=self.state();self.assertEqual(hurt['state']['characters'][0]['abilities']['DEX'],0)
            self.assertTrue(hurt['state']['characters'][0]['status']['paralyzed'])
            exported=self.request('/api/export',{},self.token)
            self.action('import',campaign=exported)
            self.assertEqual(self.state()['state']['characters'][0]['abilities']['DEX'],0)
            self.action('rest_and_recover');self.assertEqual(self.state()['state']['adventureView']['elapsedDays'],7)
            with patch.object(cairn_adventure.secrets,'randbelow',side_effect=AssertionError('Safe path rolled')):
                self.action('choose_route',route='sendero')
        self.assertTrue(self.state()['state']['adventureView']['completed'])
        self.assertNotIn('adventure',self.state()['state'])

    def test_export_import_validates_characters_and_reassigns_them_without_recalculation(self):
        self.confirmed_character();exported=self.request('/api/export',{},self.token)
        tampered=copy.deepcopy(exported);tampered['state']['characters'][0]['abilities']['STR']=18
        before=self.state()
        with self.assertRaises(urllib.error.HTTPError) as error:self.action('import',campaign=tampered)
        error.exception.close();self.assertEqual(self.state(),before)
        target=self.request('/api/create',{'title':'Restored','player':'Nueva','ruleset':'cairn-1e'})['token']
        self.action('import',target,campaign=exported)
        restored=self.state(target);character=restored['state']['characters'][0]
        self.assertEqual(character['id'],exported['state']['characters'][0]['id'])
        self.assertEqual(character['owner'],restored['me']['id'])
        self.assertEqual(character['creation']['draft']['owner'],restored['me']['id'])
        self.assertEqual(character['abilities'],exported['state']['characters'][0]['abilities'])
        guest=self.request('/api/join',{'name':'Guest','invite':restored['invite']})['token']
        self.assertNotIn('creation',self.state(guest)['state']['characters'][0])

    def test_import_keeps_multiple_drafts_and_recovery_never_replaces_an_active_draft(self):
        guest=self.request('/api/join',{'name':'Guest','invite':self.state()['invite']})['token']
        with patch.object(cairn_creator.secrets,'randbelow',return_value=0):
            self.action('begin_character',nameTable='female-names');self.action('begin_character',guest,nameTable='male-names')
        exported=self.request('/api/export',{},self.token)
        self.action('import',campaign=exported)
        state=self.state();archive=state['state']['importedDrafts'];self.assertEqual(len(archive),2)
        first,second=list(archive)
        with self.assertRaises(urllib.error.HTTPError) as error:self.action('recover_imported_draft',guest,draft=first)
        self.assertEqual(error.exception.code,403);error.exception.close()
        with patch.object(cairn_creator.secrets,'randbelow',side_effect=AssertionError('Recovery rerolled')):
            self.action('recover_imported_draft',draft=first)
            before=self.state()
            with self.assertRaises(urllib.error.HTTPError) as error:self.action('recover_imported_draft',draft=second)
            error.exception.close();self.assertEqual(self.state(),before)
        recovered=self.state()['state']['creationDrafts'][state['me']['id']]
        self.assertEqual(recovered['core'],archive[first]['core'])
        self.assertEqual(len(self.state()['state']['importedDrafts']),1)

    def test_drafts_are_private_even_from_host_and_client_cannot_select_another_owner(self):
        guest=self.request('/api/join',{'invite':self.state()['invite'],'name':'Luis'})['token']
        with patch.object(cairn_creator.secrets,'randbelow',return_value=0):
            self.action('begin_character',nameTable='female-names')
            self.action('begin_character',guest,nameTable='male-names')
        host_state=self.state();guest_state=self.state(guest)
        self.assertEqual(set(host_state['state']['creationDrafts']),{host_state['me']['id']})
        self.assertEqual(set(guest_state['state']['creationDrafts']),{guest_state['me']['id']})
        with patch.object(cairn_creator.secrets,'randbelow',side_effect=AssertionError('Unauthorized RNG')):
            with self.assertRaises(urllib.error.HTTPError) as error:
                self.action('choose_bonus',guest,table='tools',owner=host_state['me']['id'])
            self.assertEqual(error.exception.code,400);error.exception.close()

    def test_local_resources_do_not_read_firebase_and_keep_license(self):
        with patch.object(server,'repository',side_effect=AssertionError('Resource fetched database')):
            data=self.request('/api/system-resources?system=cairn-1e')
        self.assertEqual(data['tables']['license'],'CC-BY-SA-4.0')
        self.assertEqual(data['items']['Sling']['damageDie'],4)
        self.assertEqual(data['tables']['tables']['armor'][19],'Plate')

    def test_pathfinder_and_provider_operations_cannot_run_in_cairn(self):
        before=self.state()
        with patch.object(server,'ai_reply',side_effect=AssertionError('Called Pathfinder provider')):
            for kind in ('start_adventure','request_check','oracle','talk'):
                with self.assertRaises(urllib.error.HTTPError) as error:self.action(kind,text='Algo')
                self.assertEqual(error.exception.code,400);error.exception.close()
            with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/rules',{'q':'Consulta'},self.token)
            self.assertEqual(error.exception.code,400);error.exception.close()
        self.assertEqual(self.state(),before)
        exported=self.request('/api/export',{},self.token)
        self.assertEqual(exported['state']['ruleset'],'cairn-1e')
        other=copy.deepcopy(exported);other['state']['ruleset']='pathfinder-1e'
        with self.assertRaises(urllib.error.HTTPError) as error:self.action('import',campaign=other)
        self.assertEqual(error.exception.code,400);error.exception.close()


class CairnProductionTests(CairnServerTests):
    @classmethod
    def setUpClass(cls):
        cls.registration=patch.dict(rulesets.SYSTEMS,{'cairn-1e':DESCRIPTOR});cls.registration.start()
        test_render.ProductionServerTests.setUpClass.__func__(cls)

    @classmethod
    def tearDownClass(cls):
        try:test_render.ProductionServerTests.tearDownClass.__func__(cls)
        finally:cls.registration.stop()
