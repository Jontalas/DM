import unittest
from campaign_versions import accepts_action


class CampaignVersionsTests(unittest.TestCase):
    def marked(self,**fields):return {'snapshot':'saved-state','stateVersionSnapshot':'saved-state',**fields}

    def test_legacy_requires_exact_version_and_membership_only_can_be_skipped(self):
        self.assertTrue(accepts_action({'version':4},4))
        self.assertFalse(accepts_action({'version':4},3))
        for version in (4,5,6):self.assertTrue(accepts_action(self.marked(version=6,stateVersion=4),version))
        for version in (3,7):self.assertFalse(accepts_action(self.marked(version=6,stateVersion=4),version))

    def test_corrupt_or_noninteger_versions_fail_closed(self):
        for version in (None,True,False,'4',4.0,-1):self.assertFalse(accepts_action({'version':4},version))
        for metadata in ({},{'version':True},{'version':4,'stateVersion':None},{'version':4,'stateVersion':5},
                         {'version':4,'stateVersion':-1},{'version':4,'stateVersion':True}):
            self.assertFalse(accepts_action(self.marked(**metadata),4))

    def test_old_writer_snapshot_change_or_unbound_marker_cannot_authorize_stale_action(self):
        for metadata in ({'version':6,'stateVersion':4},
                         {'version':6,'stateVersion':4,'snapshot':'new-state','stateVersionSnapshot':'old-state'}):
            self.assertFalse(accepts_action(metadata,4));self.assertTrue(accepts_action(metadata,6))
