import copy
import secrets
import unittest
import urllib.error
from unittest.mock import patch
import server
import adventure_goals as goals
from firebase_store import FirestoreStore,Unavailable
import test_group_director_concurrency_http as transport
import test_adventure_chapters_context as chapter_fixture


class SharedAdventureGoalHTTPTests(unittest.TestCase):
    setUpClass=classmethod(transport.GroupDirectorConcurrencyHTTPTests.setUpClass.__func__)
    tearDownClass=classmethod(transport.GroupDirectorConcurrencyHTTPTests.tearDownClass.__func__)
    request=transport.GroupDirectorConcurrencyHTTPTests.request
    state=transport.GroupDirectorConcurrencyHTTPTests.state
    action=transport.GroupDirectorConcurrencyHTTPTests.action

    def setUp(self):
        transport.GroupDirectorConcurrencyHTTPTests.setUp(self)
        self.action('investigate',character=self.host_actor,opportunity='rastro',method='take20')
        self.action('investigate',self.guest,character=self.guest_actor,opportunity='carta',method='take20')
        self.premise='Investigar aquí la historia de Gaspar sin recoger, abrir ni entregar la carta.'

    def propose(self,token=None,premise=None):
        with (patch.object(server,'ai_reply',side_effect=AssertionError('Proposal called provider')),
              patch.object(server.STORE,'begin_rule_preparation',side_effect=AssertionError('Proposal reserved provider'))):
            self.action(goals.PROPOSE,token,premise=self.premise if premise is None else premise)

    def body(self,token=None):
        current=self.state(token);proposal=current['state']['nextAdventureView']['proposal']
        return {'id':secrets.token_hex(12),'version':current['version'],'type':'next_adventure',
                'premise':proposal['premise'],'proposalId':proposal['id'],
                'worldMemoryContract':'structured-world-memory-1','captureContract':'pf-director-action-1'}

    def reply(self,body):
        value=chapter_fixture.reply({'location':self.state()['state']['location'],'adventureChapterTransition':{'premise':body['premise']}})
        value['narration']='El siguiente objetivo espera aquí; cada jugador decide cómo investiga.'
        return value

    def test_final_owner_acceptance_captured_failed_commit_join_cold_retry_and_history(self):
        self.propose();before=self.state();original=self.request('/api/export',{})
        host=before['state']['nextAdventureView'];guest=self.state(self.guest)['state']['nextAdventureView']
        self.assertFalse(host['proposal']['canAccept']);self.assertTrue(guest['proposal']['canAccept'])
        self.assertNotIn(goals.FIELD,before['state']);self.assertNotIn('bindingSha256',str(guest))
        body=self.body(self.guest);value=self.reply(body)
        with patch.object(server,'ai_reply',return_value=value) as provider:
            with patch.object(server.STORE,'commit',side_effect=Unavailable('Interrupted shared chapter confirmation')):
                with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/action',body,self.guest)
            self.assertEqual(error.exception.code,503);error.exception.close();self.assertEqual(provider.call_count,1)
        self.assertEqual(self.state(),before)
        observer=self.request('/api/join',{'name':'Observador','invite':before['invite']})['token']
        previous=server.STORE
        if isinstance(previous,FirestoreStore):
            server.STORE=FirestoreStore.from_environment();server.STORE.prefix=previous.prefix
        try:
            with patch.object(server,'ai_reply',side_effect=AssertionError('Shared chapter billed twice')):
                self.request('/api/action',body,self.guest);after=self.state()
                self.assertTrue(self.request('/api/action',body,self.guest)['duplicate']);self.assertEqual(self.state(),after)
        finally:server.STORE=previous
        self.assertEqual(after['state']['adventureChaptersView']['current'],2)
        for key in ('characters','board','location','worldTime'):self.assertEqual(after['state'][key],before['state'][key])
        self.assertEqual(after['state']['moduleProgress']['discoveries'],[])
        archived=self.request('/api/export',{})['state'];self.assertNotIn(goals.FIELD,archived)
        self.assertEqual(archived['adventureChapters']['completed'][0]['module'],original['state']['adventureModule'])
        accepted=next(m for m in after['state']['messages'] if m.get('chapterGoalAgreement'))
        self.assertEqual(accepted['owner'],self.state(self.guest)['me']['id']);self.assertEqual(accepted['speaker'],'Taro')
        self.assertEqual(set(accepted['chapterGoalAgreement']),{before['me']['id'],self.state(self.guest)['me']['id']})
        self.assertNotIn('PRIVATE',str(self.state(self.guest)));self.assertNotIn('PRIVATE',str(self.state(observer)))

    def test_alternative_self_acceptance_and_observer_never_reserve_provider(self):
        self.propose();old=self.body();before=self.state()
        with (patch.object(server,'ai_reply',side_effect=AssertionError('Unauthorized acceptance called provider')),
              patch.object(server.STORE,'begin_rule_preparation',side_effect=AssertionError('Unauthorized acceptance reserved provider'))):
            with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/action',old)
            self.assertEqual(error.exception.code,403);error.exception.close();self.assertEqual(self.state(),before)
            changed={**old,'id':secrets.token_hex(12),'premise':'Abro la carta por todos.'}
            with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/action',changed,self.guest)
            self.assertEqual(error.exception.code,400);error.exception.close()
            observer=self.request('/api/join',{'name':'Observador','invite':before['invite']})['token']
            with self.assertRaises(urllib.error.HTTPError) as error:self.action(goals.PROPOSE,observer,premise='Elijo por otros.')
            self.assertEqual(error.exception.code,403);error.exception.close()
        self.propose(self.guest,'Averiguar aquí el origen de las placas de la posada.')
        self.assertTrue(self.state()['state']['nextAdventureView']['proposal']['canAccept'])
        self.assertFalse(self.state(self.guest)['state']['nextAdventureView']['proposal']['canAccept'])
        old['version']=self.state()['version'];old['id']=secrets.token_hex(12)
        with patch.object(server,'ai_reply',side_effect=AssertionError('Replaced proposal called provider')):
            with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/action',old)
        self.assertEqual(error.exception.code,400);error.exception.close()

    def test_copy_discards_pending_proposal_instead_of_importing_consent(self):
        self.propose();exported=self.request('/api/export',{});self.assertIn(goals.FIELD,exported['state'])
        exported['state'][goals.FIELD]['acceptedBy']=['host','guest']
        with patch.object(server,'ai_reply',side_effect=AssertionError('Copy used imported consent')):
            self.action('restore_campaign_copy',campaign=exported)
            self.assertIsNone(self.state()['state']['nextAdventureView']['proposal'])
            self.assertNotIn(goals.FIELD,self.request('/api/export',{})['state'])
            self.propose(self.guest);legacy=copy.deepcopy(self.request('/api/export',{}));legacy.pop('sourceCampaignId')
            self.action('import',campaign=legacy);self.assertNotIn(goals.FIELD,self.request('/api/export',{})['state'])

    def test_chat_does_not_require_new_proposal_but_changed_game_situation_does(self):
        self.propose();proposal=self.state(self.guest)['state']['nextAdventureView']['proposal']
        self.action('talk',kind='ooc',text='Comentamos la partida.',director=False)
        self.action('talk',self.guest,kind='private',text='PRIVATE-GUEST-NOTE',director=False)
        current=self.state(self.guest)['state']['nextAdventureView']['proposal']
        self.assertEqual(current['id'],proposal['id']);self.assertTrue(current['canAccept'])
        self.action('journal',worldTime='Una referencia corregida manualmente')
        current=self.state(self.guest)['state']['nextAdventureView']['proposal'];self.assertFalse(current['canAccept'])
        with (patch.object(server,'ai_reply',side_effect=AssertionError('Changed situation called provider')),
              patch.object(server.STORE,'begin_rule_preparation',side_effect=AssertionError('Changed situation reserved provider'))):
            with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/action',self.body(self.guest),self.guest)
        self.assertEqual(error.exception.code,400);error.exception.close()
