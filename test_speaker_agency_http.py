import unittest
import urllib.error
from unittest.mock import patch
import server
import test_pf_night_rest_http as transport
from test_character_builder import choices


class SpeakerAgencyHTTPTests(unittest.TestCase):
    setUpClass=classmethod(transport.NightRestHTTPTests.setUpClass.__func__)
    tearDownClass=classmethod(transport.NightRestHTTPTests.tearDownClass.__func__)
    setUp=transport.NightRestHTTPTests.setUp
    request=transport.NightRestHTTPTests.request
    state=transport.NightRestHTTPTests.state
    action=transport.NightRestHTTPTests.action

    def test_other_player_speech_is_rejected_before_provider_or_commit_even_for_host(self):
        guest=self.request('/api/join',{'name':'Luis','invite':self.state()['invite']})['token']
        self.action('create_character',guest,choices=choices());baseline=self.state();actor=baseline['state']['characters'][0]['id']
        for kind in ('action','dialogue'):
            for director in (False,True):
                with self.subTest(kind=kind,director=director),patch.object(server,'ai_reply',side_effect=AssertionError('Unauthorized speech reached provider')) as provider,patch.object(server.STORE,'commit',wraps=server.STORE.commit) as commit:
                    with self.assertRaises(urllib.error.HTTPError) as error:
                        self.action('talk',character=actor,text='Acepto el trato',kind=kind,director=director)
                    self.assertEqual(error.exception.code,403);error.exception.close();provider.assert_not_called();commit.assert_not_called()
                self.assertEqual(self.state(),baseline)
        self.action('talk',guest,character=actor,text='Elijo esperar',kind='action',director=False)
        self.assertEqual(self.state()['state']['messages'][-1]['speaker'],'Aria · Luis')
        self.action('talk',character=actor,text='Nota administrativa explícita',kind='ooc',director=False)
        self.assertEqual(self.state()['state']['messages'][-1]['kind'],'ooc')

    def test_unconscious_and_dead_speech_rejects_before_search_paid_reservation_or_commit(self):
        self.action('create_character',choices=choices());actor=self.state()['state']['characters'][0]['id']
        for hp in (-1,-14):
            current=self.state()['state']['characters'][0]['hp']
            self.action('manual',character=actor,hpDelta=hp-current,reason='Estado clínico técnico',resolution='Comprobar conversación sin acciones de la ficha')
            before=self.state()
            with patch.object(server,'ai_reply',side_effect=AssertionError('Unconscious speech reached provider')),patch.object(server,'search',side_effect=AssertionError('Unconscious speech searched sources')),patch.object(server.STORE,'begin_rule_preparation',side_effect=AssertionError('Unconscious speech reserved inference')),patch.object(server.STORE,'commit',wraps=server.STORE.commit) as commit:
                for kind in ('action','dialogue'):
                    for character in (actor,None):
                        for director in (False,True):
                            with self.subTest(hp=hp,kind=kind,character=character,director=director),self.assertRaises(urllib.error.HTTPError) as error:self.action('talk',character=character,text='Hablo con la guardiana',kind=kind,director=director)
                            self.assertEqual(error.exception.code,400);error.exception.close();self.assertEqual(self.state(),before)
                commit.assert_not_called()
        for kind in ('ooc','private'):self.action('talk',character=actor,text='Comentario del jugador',kind=kind,director=False)
        self.assertEqual(self.state()['state']['characters'],before['state']['characters'])
