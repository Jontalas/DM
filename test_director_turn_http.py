import copy
import secrets
import unittest
import urllib.error
from unittest.mock import patch
import server
from firebase_store import FirestoreStore,Unavailable
import test_director_combat_http as melee_transport
from test_adventure import reply


class DeclaredTurnHTTPTests(unittest.TestCase):
    setUpClass=classmethod(melee_transport.DeclaredMeleeHTTPTests.setUpClass.__func__)
    tearDownClass=classmethod(melee_transport.DeclaredMeleeHTTPTests.tearDownClass.__func__)
    setUp=melee_transport.DeclaredMeleeHTTPTests.setUp
    request=melee_transport.DeclaredMeleeHTTPTests.request
    state=melee_transport.DeclaredMeleeHTTPTests.state
    action=melee_transport.DeclaredMeleeHTTPTests.action
    prepare=melee_transport.DeclaredMeleeHTTPTests.prepare

    def test_failed_commit_replays_npc_server_dice_and_paid_turn_intent_after_restart(self):
        actor,target=self.prepare()
        self.action('attack',character=actor,target=target,physical={'attack':[1],'confirmation':[],'damage':[]})
        before=self.state();self.assertTrue(before['state']['board']['spent'][actor]['standard'])
        body={'id':secrets.token_hex(12),'version':before['version'],'type':'talk','kind':'action','character':actor,'text':'Termino mi turno','director':True,'captureContract':'pf-director-action-1'}
        with patch.object(server,'search',return_value=[]),patch.object(server,'ai_reply',return_value=reply(narration='Cedes el turno.',turnEnd={'character':actor})) as provider:
            with patch.object(server.STORE,'commit',side_effect=Unavailable('Interrupted turn')) as failed:
                with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/action',body)
            self.assertEqual(error.exception.code,503);error.exception.close();self.assertEqual(provider.call_count,1)
            attempted=copy.deepcopy(failed.call_args.args[5]);self.assertTrue(failed.call_args.kwargs['randomness'])
        self.assertEqual(self.state(),before);previous=server.STORE
        if isinstance(previous,FirestoreStore):server.STORE=FirestoreStore.from_environment();server.STORE.prefix=previous.prefix
        try:
            with patch.object(server,'search',return_value=[]),patch.object(server,'ai_reply',side_effect=AssertionError('Turn repeated provider')):
                self.request('/api/action',body);after=self.state();self.assertTrue(self.request('/api/action',body)['duplicate']);self.assertEqual(self.state(),after)
            for key in ('characters','board','pfEncounter','worldTime'):self.assertEqual(after['state'][key],attempted[key])
            self.assertEqual([m['combat'] for m in after['state']['messages'] if 'combat' in m],[m['combat'] for m in attempted['messages'] if 'combat' in m])
            self.assertEqual(after['state']['board']['round'],2);self.assertFalse(after['state']['board']['spent'][actor].get('standard'))
            self.action('import',campaign=self.request('/api/export',{}));self.assertEqual(self.state()['state']['characters'],after['state']['characters'])
        finally:server.STORE=previous

    def test_owner_and_action_kind_are_required_and_combined_attack_cannot_end_turn(self):
        guest=self.request('/api/join',{'name':'Luis','invite':self.state()['invite']})['token'];actor,target=self.prepare(guest);before=self.state()
        for kind,token,code in (('action',self.token,403),('dialogue',guest,400),('ooc',guest,400)):
            with patch.object(server,'search',return_value=[]),patch.object(server,'ai_reply',return_value=reply(narration='Fixture',turnEnd={'character':actor})):
                with self.assertRaises(urllib.error.HTTPError) as error:self.action('talk',token,character=actor,kind=kind,text='Termino mi turno',director=True)
                self.assertEqual(error.exception.code,code);error.exception.close();self.assertEqual(self.state(),before)
        with patch.object(server,'search',return_value=[]),patch.object(server,'ai_reply',return_value=reply(narration='Fixture',turnEnd={'character':actor},meleeAttack={'target':target})):
            with self.assertRaises(urllib.error.HTTPError) as error:self.action('talk',guest,character=actor,kind='action',text='Ataco y termino',director=True)
            self.assertEqual(error.exception.code,400);error.exception.close();self.assertEqual(self.state(),before)
