import threading
import unittest
from campaign_locks import CampaignLocks


class CampaignLocksTests(unittest.TestCase):
    def test_reentrant_exception_releases_and_removes_idle_campaign(self):
        locks=CampaignLocks()
        with self.assertRaisesRegex(ValueError,'fixture'):
            with locks.hold('one'):
                with locks.hold('one'):raise ValueError('fixture')
        self.assertEqual(locks._entries,{})
        with locks.hold('one'):pass
        self.assertEqual(locks._entries,{})

    def test_waiters_share_lock_and_other_campaign_does_not_wait(self):
        locks=CampaignLocks();waiting=threading.Event();entered=threading.Event()
        def follower():
            waiting.set()
            with locks.hold('one'):entered.set()
        with locks.hold('one'):
            thread=threading.Thread(target=follower);thread.start()
            self.assertTrue(waiting.wait(2))
            with locks.hold('two'):self.assertFalse(entered.is_set())
        thread.join(2)
        self.assertFalse(thread.is_alive());self.assertTrue(entered.is_set())
        self.assertEqual(locks._entries,{})
