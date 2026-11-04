import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts import verify_rule_authoring as verification
import rule_pack_authoring as authoring
import test_rule_pack_authoring as fixture


class AuthoringVerificationTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory(prefix='authoring-verification-',dir=verification.ROOT/'.deps')
        self.addCleanup(self.folder.cleanup);self.session=Path(self.folder.name)/'session.json';self.raw=fixture.request()

    def response(self):
        prepared=authoring.prepare_input(self.raw)
        return json.dumps({'stop_reason':'end_turn','content':[{'type':'text','text':json.dumps(fixture.reply(prepared))}],
            'usage':{'input_tokens':123,'output_tokens':456}}).encode()

    def test_one_attempt_capture_and_replay_without_key_or_transport(self):
        with patch.dict(os.environ,{'ANTHROPIC_API_KEY':'fake-never-persisted'}),patch.object(authoring.urllib.request,'urlopen',return_value=io.BytesIO(self.response())) as call:
            result=verification.verify(self.raw,self.session,live=True);self.assertEqual(call.call_count,1)
        self.assertEqual(result['mode'],'live');self.assertEqual(result['examples'],2)
        saved=self.session.read_text(encoding='utf-8');self.assertNotIn('fake-never-persisted',saved)
        with patch.dict(os.environ,{'ANTHROPIC_API_KEY':''}),patch.object(authoring.urllib.request,'urlopen',side_effect=AssertionError('Replay accessed provider')):
            replay=verification.verify(self.raw,self.session,live=True)
        self.assertEqual(replay['mode'],'replay');self.assertEqual(replay['status'],'candidate');self.assertTrue(replay['samePayload'])
        self.assertEqual(replay['usage'],result['usage'])

    def test_invalid_reply_is_captured_and_replayed_without_billable_retry(self):
        with patch.dict(os.environ,{'ANTHROPIC_API_KEY':'fake'}),patch.object(authoring.urllib.request,'urlopen',return_value=io.BytesIO(b'invalid-json')) as call:
            with self.assertRaises(ValueError):verification.verify(self.raw,self.session,live=True)
            self.assertEqual(call.call_count,1)
        self.assertIn('responseBase64',json.loads(self.session.read_text(encoding='utf-8')))
        with patch.object(authoring.urllib.request,'urlopen',side_effect=AssertionError('Failure retried')):
            with self.assertRaises(ValueError):verification.verify(self.raw,self.session,live=True)

    def test_uncertain_attempt_is_not_repeated_and_other_sources_do_not_overwrite(self):
        with patch.dict(os.environ,{'ANTHROPIC_API_KEY':'fake'}),patch.object(authoring.urllib.request,'urlopen',side_effect=OSError('Transport interrupted')):
            with self.assertRaises(ValueError):verification.verify(self.raw,self.session,live=True)
        before=self.session.read_bytes()
        with patch.object(authoring.urllib.request,'urlopen',side_effect=AssertionError('Uncertain attempt retried')):
            with self.assertRaisesRegex(ValueError,'incierto'):verification.verify(self.raw,self.session,live=True)
            changed=fixture.request();changed['scope']='Different scope'
            with self.assertRaises(ValueError):verification.verify(changed,self.session,live=True)
        self.assertEqual(self.session.read_bytes(),before)

    def test_default_is_offline_missing_key_does_not_reserve_and_paths_are_private(self):
        with patch.dict(os.environ,{'ANTHROPIC_API_KEY':''}),patch.object(authoring.urllib.request,'urlopen',side_effect=AssertionError('Unexpected provider')):
            with self.assertRaises(ValueError):verification.verify(self.raw,self.session)
            with self.assertRaises(ValueError):verification.verify(self.raw,self.session,live=True)
            self.assertFalse(self.session.exists())
            with self.assertRaises(ValueError):verification.verify(self.raw,verification.ROOT/'public-capture.json',live=True)


if __name__=='__main__':unittest.main()
