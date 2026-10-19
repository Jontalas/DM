import copy
import io
import json
import os
import secrets
import unittest
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch, Mock
from engine import initial_state
from firebase_store import FirestoreStore,Conflict,Unavailable,CHUNK_BYTES,encode_state,words
from test_support import make_store
import claude_dm


class ClaudeTests(unittest.TestCase):
    def state(self):
        state=initial_state({});state['secrets']='SECRET-DM';state['private']={'owner':'SECRET-PLAYER'}
        state['messages']=[{'kind':'private','speaker':'Ana','text':'PRIVATE-MESSAGE','visibility':'private'}]
        return state
    def response(self,stop='end_turn',narration='La posadera se acerca.'):
        return io.BytesIO(json.dumps({'stop_reason':stop,'content':[{'type':'text','text':json.dumps({'narration':narration,'proposals':[]})}]}).encode())
    def test_native_haiku_request_and_privacy(self):
        with patch.dict(os.environ,{'ANTHROPIC_API_KEY':'fake-test-key','ANTHROPIC_MODEL':claude_dm.DEFAULT_MODEL}),patch('claude_dm.urllib.request.urlopen',return_value=self.response()) as call:
            result=claude_dm.ai_reply(self.state(),'Hablo con la posadera',[{'book':'reglas','page':194,'text':'Fixture de fuente'}])
            request=call.call_args.args[0];body=json.loads(request.data)
            self.assertEqual(request.full_url,'https://api.anthropic.com/v1/messages')
            self.assertEqual(request.get_header('X-api-key'),'fake-test-key')
            self.assertEqual(body['model'],claude_dm.DEFAULT_MODEL);self.assertIn('output_config',body)
            self.assertNotIn('SECRET-DM',request.data.decode());self.assertNotIn('SECRET-PLAYER',request.data.decode());self.assertNotIn('PRIVATE-MESSAGE',request.data.decode())
            self.assertEqual(result['narration'],'La posadera se acerca.')
    def test_no_key_no_fake_reply(self):
        with patch.dict(os.environ,{},clear=True),patch('claude_dm.urllib.request.urlopen') as call:
            with self.assertRaisesRegex(ValueError,'ANTHROPIC_API_KEY'):claude_dm.ai_reply(self.state(),'Inicio',[])
            call.assert_not_called()
    def test_truncated_and_refused_output_rejected(self):
        for stop in ['max_tokens','refusal']:
            with self.subTest(stop=stop),patch.dict(os.environ,{'ANTHROPIC_API_KEY':'fake'}),patch('claude_dm.urllib.request.urlopen',return_value=self.response(stop)):
                with self.assertRaises(ValueError):claude_dm.ai_reply(self.state(),'Inicio',[])
    def test_error_does_not_expose_provider_body_or_key(self):
        error=urllib.error.HTTPError('https://api.anthropic.com/v1/messages',429,'error',{},io.BytesIO(b'private-debug-body'))
        with patch.dict(os.environ,{'ANTHROPIC_API_KEY':'fake-secret'}),patch('claude_dm.urllib.request.urlopen',side_effect=error):
            with self.assertRaisesRegex(ValueError,'HTTP 429') as ctx:claude_dm.ai_reply(self.state(),'Inicio',[])
            self.assertNotIn('fake-secret',str(ctx.exception));self.assertNotIn('private-debug-body',str(ctx.exception))
    def test_non_haiku_model_rejected(self):
        with patch.dict(os.environ,{'ANTHROPIC_MODEL':'claude-sonnet-5-5'}):
            with self.assertRaises(ValueError):claude_dm.model_name()


class EncodingTests(unittest.TestCase):
    def test_health_reuses_only_recent_success_and_checks_again_after_expiry(self):
        client=Mock();store=FirestoreStore(client)
        read=client.collection.return_value.document.return_value.get
        with patch('firebase_store.time.monotonic',return_value=100):
            store.health();store.health()
        self.assertEqual(read.call_count,1)
        read.side_effect=PermissionError('Denied')
        with patch('firebase_store.time.monotonic',return_value=161):
            with self.assertRaises(PermissionError):store.health()
            with self.assertRaises(PermissionError):store.health()
        self.assertEqual(read.call_count,3)
    def test_spanish_token_normalization(self):self.assertEqual(words('¿Qué información hay? Información y Percepción'),['informacion','percepcion'])
    def test_missing_firebase_has_no_sqlite_fallback(self):
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaises(Unavailable):FirestoreStore.from_environment()
    def test_large_state_is_chunked_below_document_limit(self):
        chunks=encode_state({'text':secrets.token_hex(900000)})
        self.assertGreater(len(chunks),1);self.assertTrue(all(len(chunk)<=CHUNK_BYTES for chunk in chunks))


@unittest.skipUnless(os.environ.get('FIRESTORE_EMULATOR_HOST'),'Requiere emulador oficial de Firestore; no usa Firebase real')
class FirestoreEmulatorTests(unittest.TestCase):
    def setUp(self):
        self.store=make_store();self.token=self.store.create('Fixture',initial_state({}),'Ana');self.me=self.store.identity(self.token);self.cid=self.me['campaign']
    def another_client(self):
        other=FirestoreStore.from_environment();other.prefix=self.store.prefix;return other
    def test_fresh_client_recovers_confirmed_state_and_hashed_session(self):
        row,state=self.store.load(self.cid);state['notes']='Escena confirmada'
        self.store.commit(self.cid,'a1',self.me['id'],'signature',row['version'],state)
        other=self.another_client();self.assertEqual(other.load(self.cid)[1]['notes'],'Escena confirmada')
        self.assertEqual(other.identity(self.token)['id'],self.me['id'])
        self.assertFalse(self.store.collection('sessions').document(self.token).get().exists)
    def test_direct_client_read_denied_by_firestore_rules(self):
        url='http://'+os.environ['FIRESTORE_EMULATOR_HOST']+'/v1/projects/'+os.environ['FIREBASE_PROJECT_ID']+'/databases/(default)/documents/'+self.store.campaign(self.cid).path
        with self.assertRaises(urllib.error.HTTPError) as ctx:urllib.request.urlopen(url)
        self.assertEqual(ctx.exception.code,403);ctx.exception.close()
    def test_two_clients_same_version_only_one_commit(self):
        row,state=self.store.load(self.cid);barrier=Barrier(2)
        def commit(number):
            other=self.another_client();candidate=copy.deepcopy(state);candidate['notes']=str(number);barrier.wait()
            try:other.commit(self.cid,'action'+str(number),self.me['id'],str(number),row['version'],candidate);return 'ok'
            except Conflict:return 'conflict'
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(commit,[1,2]))
        self.assertEqual(sorted(results),['conflict','ok']);self.assertEqual(self.store.metadata(self.cid)['version'],1)
        markers=list(self.store.campaign(self.cid).collection('actions').stream())
        self.assertEqual(len(markers),1)
        saved=self.store.load(self.cid)[1]
        self.assertEqual(markers[0].to_dict()['fingerprint'],saved['notes'])
    def test_timestamp_precondition_rejects_changed_metadata_atomically(self):
        row,state=self.store.load(self.cid);state['notes']='Must not be committed'
        stage=self.store._stage
        def change_after_read(cid,candidate):
            self.another_client().campaign(cid).update({'title':'Changed concurrently'})
            return stage(cid,candidate)
        with patch.object(self.store,'_stage',side_effect=change_after_read):
            with self.assertRaises(Conflict):
                self.store.commit(self.cid,'precondition',self.me['id'],'signature',row['version'],state)
        meta,saved=self.store.load(self.cid)
        self.assertEqual(meta['version'],row['version']);self.assertEqual(meta['title'],'Changed concurrently')
        self.assertNotEqual(saved['notes'],state['notes'])
        self.assertFalse(self.store.completed(self.cid,'precondition',self.me['id'],'signature'))
    def test_same_action_concurrent_deduplication(self):
        row,state=self.store.load(self.cid);barrier=Barrier(2)
        def commit(_):
            other=self.another_client();barrier.wait();return other.commit(self.cid,'same-action',self.me['id'],'same-signature',row['version'],state)
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(commit,[1,2]))
        self.assertEqual(sorted(results),[False,True]);self.assertEqual(self.store.metadata(self.cid)['version'],1)
    def test_marker_reuse_with_different_payload_is_rejected(self):
        row,state=self.store.load(self.cid);self.store.commit(self.cid,'id',self.me['id'],'signature',row['version'],state)
        with self.assertRaises(Conflict):self.store.completed(self.cid,'id',self.me['id'],'other-signature')
    def test_state_larger_than_one_megabyte_roundtrip(self):
        row,state=self.store.load(self.cid);state['notes']=secrets.token_hex(700000)
        self.store.commit(self.cid,'large',self.me['id'],'large',row['version'],state)
        other=self.another_client();meta,loaded=other.load(self.cid)
        self.assertGreater(meta['chunks'],1);self.assertEqual(loaded,state)


if __name__=='__main__':unittest.main()
