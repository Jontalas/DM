import copy
import json
import secrets
import unittest
import urllib.error
from unittest.mock import patch
import server
from firebase_store import FirestoreStore,Unavailable
import test_pf_night_rest_http as transport


class CompactMemoryHTTPTests(unittest.TestCase):
    setUpClass=classmethod(transport.NightRestHTTPTests.setUpClass.__func__)
    tearDownClass=classmethod(transport.NightRestHTTPTests.tearDownClass.__func__)
    request=transport.NightRestHTTPTests.request
    state=transport.NightRestHTTPTests.state
    action=transport.NightRestHTTPTests.action
    prepare=transport.NightRestHTTPTests.prepare

    def setUp(self):
        configured=patch.dict('os.environ',{'ANTHROPIC_API_KEY':'fixture-never-sent'})
        configured.start();self.addCleanup(configured.stop);transport.NightRestHTTPTests.setUp(self)

    def test_compact_reply_commit_retry_cold_capture_and_guest_privacy_keep_authoritative_facts(self):
        guest=self.request('/api/join',{'name':'Luis','invite':self.state()['invite']})['token']
        self.prepare(version='1.10.0');self.action('continue_pf_encounter');before=self.state()
        actor=before['state']['characters'][0]['id']
        compact={'summary':'La guardiana espera junto a la salida; el registro sigue sin examinar.','preparation':'PRIVATE-COMPACT: la pista sigue pendiente.'}
        result={'narration':'El registro permanece sobre el banco.','proposals':[],'memory':compact}
        body={'id':secrets.token_hex(12),'version':before['version'],'type':'talk','kind':'dialogue','character':actor,'text':'¿Qué se ve junto al banco?','director':True}
        with patch.object(server,'search',return_value=[]),patch.object(server,'ai_reply',return_value=result) as provider:
            with patch.object(server.STORE,'commit',side_effect=Unavailable('Interrupted compact memory')) as failed:
                with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/action',body)
            self.assertEqual(error.exception.code,503);error.exception.close();self.assertEqual(provider.call_count,1)
            attempted=copy.deepcopy(failed.call_args.args[5])
        self.assertEqual(self.state(),before);previous=server.STORE
        if isinstance(previous,FirestoreStore):
            server.STORE=FirestoreStore.from_environment();server.STORE.prefix=previous.prefix
        try:
            with (patch.object(server,'search',return_value=[]),patch.object(server,'ai_reply',side_effect=AssertionError('Compact retry called provider')),
                patch('game_randomness.draw',side_effect=AssertionError('Memory rolled dice'))):
                self.request('/api/action',body);after=self.state();self.assertTrue(self.request('/api/action',body)['duplicate']);self.assertEqual(self.state(),after)
            for key in ('characters','board','location','worldTime','goal','objectives','moduleProgress'):
                self.assertEqual(after['state'][key],before['state'][key]);self.assertEqual(after['state'][key],attempted[key])
            self.assertEqual(after['state']['adventure']['summary'],compact['summary'])
            self.assertEqual(after['state']['adventure']['revision'],before['state']['adventure']['revision']+1)
            self.assertEqual(after['state']['directorMemory'],compact['preparation'])
            self.assertNotIn('PRIVATE-COMPACT',json.dumps(self.state(guest)))
            exported=self.request('/api/export',{});self.action('import',campaign=exported)
            self.assertEqual(self.state()['state']['adventure']['summary'],compact['summary'])
            self.assertEqual(self.state()['state']['directorMemory'],compact['preparation'])
        finally:server.STORE=previous
