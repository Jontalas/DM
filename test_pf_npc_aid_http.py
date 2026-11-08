import copy
import hashlib
import secrets
import unittest
import urllib.error
from unittest.mock import patch
import server
from firebase_store import FirestoreStore,Unavailable
import test_pf_night_rest_http as transport
from test_character_builder import choices
from rule_pack_authoring import canonical


class NPCFirstAidHTTPTests(unittest.TestCase):
    setUpClass=classmethod(transport.NightRestHTTPTests.setUpClass.__func__)
    tearDownClass=classmethod(transport.NightRestHTTPTests.tearDownClass.__func__)
    setUp=transport.NightRestHTTPTests.setUp
    request=transport.NightRestHTTPTests.request
    state=transport.NightRestHTTPTests.state
    action=transport.NightRestHTTPTests.action

    def prepare(self):
        self.action('create_character',choices=choices());actor=self.state()['state']['characters'][0]['id']
        self.action('enter_pf_encounter',encounter='patio-del-peaje',encounterVersion='1.14.0',character=actor)
        with patch('game_randomness.draw',side_effect=[20,1]),patch('game_randomness.initiative_tie',return_value=0):self.action('choose_pf_encounter',choice='combat')
        for _ in range(4):
            with patch('game_randomness.draw',side_effect=[19,1,4]):self.action('turn')
        self.assertEqual(self.state()['state']['characters'][0]['hp'],0)
        return actor,self.state()['state']['characters'][1]['id']

    def test_failed_commit_replays_npc_aid_stabilization_and_hourly_dice_with_one_atomic_commit(self):
        actor,npc=self.prepare();before=self.state()
        body={'id':secrets.token_hex(12),'version':before['version'],'type':'attack','character':actor,'target':npc,
            'physical':{'attack':[12],'confirmation':[],'damage':[1]}}
        with patch.object(server,'ai_reply',side_effect=AssertionError('Medical episode called provider')),patch.object(server,'search',side_effect=AssertionError('Medical episode searched sources')):
            with patch.object(server.STORE,'commit',side_effect=Unavailable('Interrupted NPC aid')) as failed:
                with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/action',body)
                self.assertEqual(error.exception.code,503);error.exception.close()
                self.assertEqual(failed.call_count,1)
            attempted=copy.deepcopy(failed.call_args.args[5]);self.assertTrue(failed.call_args.kwargs['randomness']);self.assertEqual(self.state(),before)
            self.assertGreaterEqual(attempted['pfEncounter']['npcAidEpisode']['end']['attempts'],1)
            previous=server.STORE
            if isinstance(previous,FirestoreStore):server.STORE=FirestoreStore.from_environment();server.STORE.prefix=previous.prefix
            try:
                with patch.object(server.STORE,'commit',wraps=server.STORE.commit) as commit:
                    self.request('/api/action',body);self.assertEqual(commit.call_count,1)
                after=self.state();self.assertTrue(self.request('/api/action',body)['duplicate']);self.assertEqual(self.state(),after)
                for key in ('characters','board','pfEncounter','worldTime'):self.assertEqual(after['state'][key],attempted[key])
                strip_time=lambda messages:[{key:value for key,value in message.items() if key!='time'} for message in messages]
                self.assertEqual(strip_time(after['state']['messages']),strip_time(attempted['messages']))
                self.action('import',campaign=self.request('/api/export',{}));self.assertEqual(self.state()['state']['pfEncounter'],after['state']['pfEncounter'])
                baseline=self.state();forged=self.request('/api/export',{});receipt=forged['state']['pfEncounter']['npcAidEpisode'];receipt['start']['helper']['heal']=20
                marker=hashlib.sha256(canonical(receipt).encode()).hexdigest()
                for message in forged['state']['messages']:
                    if 'npcAidSha256' in message:message['npcAidSha256']=marker
                with self.assertRaises(urllib.error.HTTPError) as error:self.action('import',campaign=forged)
                self.assertEqual(error.exception.code,400);error.exception.close();self.assertEqual(self.state(),baseline)
            finally:server.STORE=previous
