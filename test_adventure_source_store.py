import os
import unittest
from unittest.mock import patch
import adventure_source
import rule_pack_campaign as campaign
from test_support import make_store
from firebase_store import FirestoreStore,Unavailable


@unittest.skipUnless(os.environ.get('FIRESTORE_EMULATOR_HOST'),'Requiere emulador oficial; no usa Firebase real')
class AdventureSourceStoreTests(unittest.TestCase):
    def setUp(self):
        self.store=make_store();state=campaign.initial_state({})
        state['adventureSource']=adventure_source.create('Aventura propia','Texto privado original de Arda.','provided-adventure')
        token=self.store.create('Adventure source test',state,'Ana');self.me=self.store.identity(token);self.cid=self.me['campaign']
        self.ref=self.store.load(self.cid)[1]['adventureSourceRef']

    def cold(self):
        store=FirestoreStore.from_environment();store.prefix=self.store.prefix;return store

    def test_cold_recovery_cache_mutability_and_campaign_isolation(self):
        other=self.cold();record=other.load_adventure_source(self.cid,self.ref);record['text']='Changed locally'
        self.assertEqual(other.load_adventure_source(self.cid,self.ref)['text'],'Texto privado original de Arda.')
        with self.assertRaises(Unavailable):other.load_adventure_source('another-campaign',self.ref)
        for n in range(12):other._cache_adventure('scope-'+str(n),self.ref,adventure_source.create('Otro','Texto','provided-adventure'))
        self.assertLessEqual(len(other._adventure_cache),8)

    def test_mechanical_commit_does_not_fetch_or_stage_original_and_corruption_is_rejected(self):
        row,state=self.store.load(self.cid)
        with patch.object(self.store,'load_adventure_source',side_effect=AssertionError('Gameplay fetched source')),patch.object(self.store,'_stage_adventure_source',side_effect=AssertionError('Gameplay restaged source')):
            state['goal']='Actualización local'
            self.store.commit(self.cid,'mechanical-action',self.me['id'],'signature',row['version'],state)
        self.store.campaign(self.cid).collection('adventureSources').document(self.ref['sha256']).update({'data':b'broken'})
        with self.assertRaises(Unavailable):self.cold().load_adventure_source(self.cid,self.ref)
