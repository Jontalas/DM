import copy
import secrets
import unittest
import urllib.error
from unittest.mock import patch
import server
from firebase_store import FirestoreStore,Unavailable
import test_pf_ceasefire_http as truce_http


class TruceNightHTTPTests(unittest.TestCase):
    setUpClass=classmethod(truce_http.CeasefireHTTPTests.setUpClass.__func__)
    tearDownClass=classmethod(truce_http.CeasefireHTTPTests.tearDownClass.__func__)
    setUp=truce_http.CeasefireHTTPTests.setUp
    request=truce_http.CeasefireHTTPTests.request
    state=truce_http.CeasefireHTTPTests.state
    action=truce_http.CeasefireHTTPTests.action
    prepare_truce=truce_http.CeasefireHTTPTests.prepare_truce

    def test_zero_hp_night_commit_retry_duplicate_copy_and_guard_truce_binding(self):
        self.prepare_truce(version='1.9.0')
        for _ in range(4):
            with patch('game_randomness.draw',side_effect=[19,1,4]):self.action('turn')
        self.assertEqual(self.state()['state']['characters'][0]['hp'],0)
        self.action('accept_pf_ceasefire');before=self.state()
        self.assertIsNone(before['state']['pfNightRestView']['reason'])
        body={'id':secrets.token_hex(12),'version':before['version'],'type':'rest_pf_night'}
        with patch.object(server.STORE,'commit',side_effect=Unavailable('Interrupted truce night')):
            with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/action',body)
        self.assertEqual(error.exception.code,503);error.exception.close();self.assertEqual(self.state(),before)
        previous=server.STORE
        if isinstance(previous,FirestoreStore):
            server.STORE=FirestoreStore.from_environment();server.STORE.prefix=previous.prefix
        try:
            with patch.object(server,'ai_reply',side_effect=AssertionError('Rest called provider')),patch('game_randomness.draw',side_effect=AssertionError('Rest rolled')):
                self.request('/api/action',body);after=self.state()
                self.assertTrue(self.request('/api/action',body)['duplicate']);self.assertEqual(self.state(),after)
            self.assertEqual([c['hp'] for c in after['state']['characters']],[1,2])
            exported=self.request('/api/export',{});self.action('import',campaign=exported)
            self.assertEqual(self.state()['state']['characters'],after['state']['characters'])
            forged=copy.deepcopy(exported);forged['state']['pfNightRest']['start']['ceasefireSha256']='0'*64
            baseline=self.state()
            with self.assertRaises(urllib.error.HTTPError) as error:self.action('import',campaign=forged)
            self.assertEqual(error.exception.code,400);error.exception.close();self.assertEqual(self.state(),baseline)
            self.action('continue_pf_encounter');self.assertEqual(self.state()['state']['boardScenes']['current'],'patio')
            self.assertEqual([c['hp'] for c in self.state()['state']['characters']],[1,2])
        finally:server.STORE=previous
