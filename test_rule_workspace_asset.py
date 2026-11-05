import copy
import json
import os
import unittest
import zlib
from unittest.mock import patch
import rule_workspace_asset as assets
import rule_pack_campaign as campaign
import rule_preparation_workspace as workspaces
from test_rule_preparation_workspace import record
from rule_pack_runtime import RulePackError
from firebase_store import FirestoreStore,Unavailable,Conflict
from test_support import make_store


def state_with_workspace():
    state=campaign.initial_state({});state['authoringWorkspace']=workspaces.add(workspaces.empty(),record())
    return state


class WorkspaceAssetTests(unittest.TestCase):
    def test_detach_roundtrip_is_immutable_and_snapshot_has_no_source_material(self):
        state=state_with_workspace();before=copy.deepcopy(state);light,asset=assets.detach(state)
        self.assertEqual(state,before);self.assertIsNone(light['authoringWorkspace'])
        self.assertNotIn('examples',json.dumps(light));self.assertNotIn('textSha256',json.dumps(light))
        restored=json.loads(assets.decode(light['authoringWorkspaceRef'],asset['packed']))
        self.assertEqual(restored,state['authoringWorkspace'])
        self.assertEqual(assets.detach(light),(light,None))

    def test_integrity_truncation_size_and_external_reference_reject(self):
        state=state_with_workspace();light,asset=assets.detach(state);reference=asset['reference']
        for packed in (b'broken',asset['packed'][:-4],asset['packed']+b'extra',zlib.compress(b'x'*(workspaces.MAX_BYTES+1))):
            with self.assertRaises(RulePackError):assets.decode(reference,packed)
        with self.assertRaises(RulePackError):assets.decode(reference|{'sha256':'a'*64},asset['packed'])
        with self.assertRaises(RulePackError):campaign.validate_restored(light)

    def test_source_budget_does_not_make_valid_gameplay_backup_unrestorable(self):
        state=state_with_workspace();state['goal']='g'*2000
        private=len(campaign._canonical(state['authoringWorkspace']).encode())
        game=len(campaign._canonical({k:v for k,v in state.items() if k not in ('authoring','authoringWorkspace')}).encode())
        self.assertGreater(len(campaign._canonical(state).encode()),max(private,game)+1)
        with patch.object(campaign,'MAX_BYTES',max(private,game)+1):campaign._size(state)


@unittest.skipUnless(os.environ.get('FIRESTORE_EMULATOR_HOST'),'Requiere emulador oficial; no usa Firebase real')
class WorkspaceAssetEmulatorTests(unittest.TestCase):
    def setUp(self):
        self.store=make_store();self.token=self.store.create('Private workspace test',state_with_workspace(),'Ana')
        self.me=self.store.identity(self.token);self.cid=self.me['campaign']

    def cold(self):
        other=FirestoreStore.from_environment();other.prefix=self.store.prefix;return other

    def test_cold_recovery_and_warm_cache_do_not_share_mutable_data_or_campaigns(self):
        row,state=self.store.load(self.cid);reference=state['authoringWorkspaceRef'];self.assertIsNone(state['authoringWorkspace'])
        other=self.cold()
        with patch.object(other,'_fetch_rule_workspace',wraps=other._fetch_rule_workspace) as fetch:
            first=other.load_rule_workspace(self.cid,reference);first['texts'].clear()
            self.assertTrue(other.load_rule_workspace(self.cid,reference)['texts']);self.assertEqual(fetch.call_count,1)
        with self.assertRaises(Unavailable):other.load_rule_workspace('another-campaign',reference)

    def test_game_commit_and_replay_do_not_read_or_write_the_private_asset(self):
        row,state=self.store.load(self.cid)
        with patch.object(self.store,'_stage_rule_workspace',side_effect=AssertionError('Gameplay restaged sources')),patch.object(self.store,'_fetch_rule_workspace',side_effect=AssertionError('Gameplay fetched sources')):
            state['goal']='Changed game metadata'
            self.assertFalse(self.store.commit(self.cid,'game-action',self.me['id'],'signature',row['version'],state))
            self.assertTrue(self.store.commit(self.cid,'game-action',self.me['id'],'signature',row['version'],state))
        stored=self.store.load(self.cid)[1]
        self.assertEqual(stored['authoringWorkspaceRef'],state['authoringWorkspaceRef']);self.assertIsNone(stored['authoringWorkspace'])

    def test_failed_asset_stage_leaves_campaign_and_action_marker_unchanged(self):
        row,state=self.store.load(self.cid);before=copy.deepcopy(state)
        state['authoringWorkspace']=self.store.load_rule_workspace(self.cid,state['authoringWorkspaceRef'])
        from test_rule_pack_authoring import request
        raw=request();raw['scope']='New prepared block';state['authoringWorkspace']=workspaces.add(state['authoringWorkspace'],record(raw))
        with patch.object(self.store,'_stage_rule_workspace',side_effect=OSError('Storage unavailable')):
            with self.assertRaises(OSError):self.store.commit(self.cid,'failed-action',self.me['id'],'signature',row['version'],state)
        self.assertEqual(self.store.load(self.cid)[1],before)
        self.assertFalse(self.store.completed(self.cid,'failed-action',self.me['id'],'signature'))

    def test_cache_is_bounded_and_corrupt_cold_data_is_not_reused(self):
        row,state=self.store.load(self.cid);reference=state['authoringWorkspaceRef']
        self.store.campaign(self.cid).collection('ruleWorkspaces').document(reference['sha256']).update({'data':b'corrupted'})
        with self.assertRaises(Unavailable):self.cold().load_rule_workspace(self.cid,reference)
        for n in range(12):self.store._cache_workspace('scope-'+str(n),reference,b'{}')
        self.assertLessEqual(len(self.store._workspace_cache),8)


if __name__=='__main__':unittest.main()
