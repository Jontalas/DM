import secrets
import unittest
import urllib.error
from unittest.mock import patch
import server
from firebase_store import FirestoreStore,Unavailable
import test_pf_ceasefire_http as truce_http
from test_adventure import reply,memory


class PreparedDecisionHTTPTests(unittest.TestCase):
    setUpClass=classmethod(truce_http.CeasefireHTTPTests.setUpClass.__func__)
    tearDownClass=classmethod(truce_http.CeasefireHTTPTests.tearDownClass.__func__)
    request=truce_http.CeasefireHTTPTests.request
    state=truce_http.CeasefireHTTPTests.state
    action=truce_http.CeasefireHTTPTests.action
    prepare_truce=truce_http.CeasefireHTTPTests.prepare_truce

    def setUp(self):
        configured=patch.dict('os.environ',{'ANTHROPIC_API_KEY':'fixture-never-sent'})
        configured.start();self.addCleanup(configured.stop);truce_http.CeasefireHTTPTests.setUp(self)

    def test_prepared_sleep_does_not_reserve_or_read_dice_after_shared_randomness_wrapper(self):
        self.prepare_truce(version='1.9.0');self.action('accept_pf_ceasefire');actor=self.state()['state']['characters'][0]['id']
        result=reply(narration='El patio permanece tranquilo.',preparedDecision={'action':'sleep-in-light-armor'})
        with patch.object(server,'search',return_value=[]),patch.object(server,'ai_reply',return_value=result),patch.object(server.STORE,'action_random_seed',side_effect=AssertionError('Sleep reserved dice')),patch.object(server.STORE,'check_action_random_seed',side_effect=AssertionError('Sleep read dice')):
            self.action('talk',kind='action',character=actor,text='Duermo con la armadura ligera',director=True)
        self.assertTrue(self.state()['state']['pfNightRestView']['completed'])

    def test_zero_hp_declared_night_recovers_commit_without_second_provider_then_declared_investigation(self):
        self.prepare_truce(version='1.9.0')
        for _ in range(4):
            with patch('game_randomness.draw',side_effect=[19,1,4]):self.action('turn')
        self.action('accept_pf_ceasefire');before=self.state();actor=before['state']['characters'][0]['id']
        body={'id':secrets.token_hex(12),'version':before['version'],'type':'talk','kind':'action','character':actor,'text':'Duermo8h con mi armadura ligera','director':True}
        result=reply(narration='El patio está tranquilo.',preparedDecision={'action':'sleep-in-light-armor'})
        with patch.object(server,'search',return_value=[]),patch.object(server,'ai_reply',return_value=result) as provider:
            with patch.object(server.STORE,'commit',side_effect=Unavailable('Interrupted declared sleep')):
                with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/action',body)
            self.assertEqual(error.exception.code,503);error.exception.close();self.assertEqual(provider.call_count,1)
        self.assertEqual(self.state(),before);previous=server.STORE
        if isinstance(previous,FirestoreStore):
            server.STORE=FirestoreStore.from_environment();server.STORE.prefix=previous.prefix
        try:
            with patch.object(server,'search',return_value=[]),patch.object(server,'ai_reply',side_effect=AssertionError('Declared sleep repeated provider')):
                self.request('/api/action',body);after=self.state();self.assertTrue(self.request('/api/action',body)['duplicate']);self.assertEqual(self.state(),after)
            self.assertEqual([c['hp'] for c in after['state']['characters']],[1,2]);self.assertNotIn('pfContinuation',after['state'])
            exported=self.request('/api/export',{});self.action('import',campaign=exported)
            result=reply(narration='El registro sigue en el banco.',preparedDecision={'action':'investigate-courtyard'},memory=memory(location='NO-CONFIRMADO'))
            with patch.object(server,'search',return_value=[]),patch.object(server,'ai_reply',return_value=result):
                self.action('talk',kind='action',text='Empiezo a investigar el registro del patio',character=actor,director=True)
            state=self.state()['state'];self.assertEqual(state['boardScenes']['current'],'patio')
            self.assertNotEqual(state['location'],'NO-CONFIRMADO');self.assertEqual([c['hp'] for c in state['characters']],[1,2])
        finally:server.STORE=previous

    def test_prepared_armor_owner_and_non_action_guards_are_atomic(self):
        guest=self.request('/api/join',{'name':'Luis','invite':self.state()['invite']})['token']
        self.prepare_truce(guest,version='1.9.0',armor='scale');self.action('accept_pf_ceasefire',guest)
        baseline=self.state();result=reply(narration='Fixture',preparedDecision={'action':'sleep-after-removing-armor'})
        for kind,token,code in (('action',self.token,403),('dialogue',guest,400),('ooc',guest,400)):
            with patch.object(server,'search',return_value=[]),patch.object(server,'ai_reply',return_value=result):
                with self.assertRaises(urllib.error.HTTPError) as error:self.action('talk',token,kind=kind,text='Me quito la cota, duermo y vuelvo a equiparla',director=True)
            self.assertEqual(error.exception.code,code);error.exception.close();self.assertEqual(self.state(),baseline)
        with patch.object(server,'search',return_value=[]),patch.object(server,'ai_reply',return_value=result):
            self.action('talk',guest,kind='action',text='Me quito la cota, duermo sin ella y vuelvo a equiparla',director=True)
        self.assertEqual(self.state()['state']['pfNightRestView']['result']['seconds'],29100)
