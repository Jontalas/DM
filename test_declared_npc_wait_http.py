import copy
import secrets
import unittest
import urllib.error
from unittest.mock import patch
import server
from firebase_store import FirestoreStore,Unavailable
import test_pf_npc_wait_http as transport
from test_adventure import reply,memory


class DeclaredNPCWaitHTTPTests(unittest.TestCase):
    setUpClass=classmethod(transport.NPCWaitHTTPTests.setUpClass.__func__)
    tearDownClass=classmethod(transport.NPCWaitHTTPTests.tearDownClass.__func__)
    request=transport.NPCWaitHTTPTests.request
    state=transport.NPCWaitHTTPTests.state
    action=transport.NPCWaitHTTPTests.action
    prepare=transport.NPCWaitHTTPTests.prepare

    def setUp(self):
        configured=patch.dict('os.environ',{'ANTHROPIC_API_KEY':'fixture-never-sent'});configured.start();self.addCleanup(configured.stop)
        transport.NPCWaitHTTPTests.setUp(self)

    def test_cold_retry_keeps_paid_wait_intent_and_every_real_server_recovery_die(self):
        actor,_=self.prepare();before=self.state();body={'id':secrets.token_hex(12),'version':before['version'],'type':'talk','kind':'action','character':actor,'text':'Espero junto a la guardiana a que despierte','director':True,'captureContract':'pf-director-action-1'}
        result=reply(narration='Permaneces junto a la guardiana.',preparedDecision={'action':'wait-for-guard'},memory=memory(location='NO-CONFIRMADO'))
        with patch.object(server,'search',return_value=[]),patch.object(server,'ai_reply',return_value=result) as provider:
            with patch.object(server.STORE,'commit',side_effect=Unavailable('Interrupted declared wait')) as failed:
                with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/action',body)
                self.assertEqual(error.exception.code,503);error.exception.close()
            self.assertEqual(provider.call_count,1);attempted=copy.deepcopy(failed.call_args.args[5]);self.assertTrue(failed.call_args.kwargs['randomness'])
        self.assertEqual(self.state(),before);previous=server.STORE
        if isinstance(previous,FirestoreStore):server.STORE=FirestoreStore.from_environment();server.STORE.prefix=previous.prefix
        try:
            with patch.object(server,'search',return_value=[]),patch.object(server,'ai_reply',side_effect=AssertionError('Wait repeated provider')):
                self.request('/api/action',body);after=self.state();self.assertTrue(self.request('/api/action',body)['duplicate']);self.assertEqual(self.state(),after)
            for key in ('characters','board','pfEncounter','worldTime'):self.assertEqual(after['state'][key],attempted[key])
            self.assertEqual(after['state']['characters'][0],before['state']['characters'][0]);self.assertNotIn('pfContinuation',after['state'])
            self.assertEqual(after['state']['location'],before['state']['location'])
            self.assertEqual([m['recoveryChecks'] for m in after['state']['messages'] if 'npcRecoverySha256' in m],[m['recoveryChecks'] for m in attempted['messages'] if 'npcRecoverySha256' in m])
            self.action('import',campaign=self.request('/api/export',{}));self.assertEqual(self.state()['state']['characters'],after['state']['characters'])
        finally:server.STORE=previous
