"""Process-local campaign serialization; persistent CAS remains authoritative."""
from contextlib import contextmanager
import threading


class CampaignLocks:
    def __init__(self):
        self._guard=threading.Lock()
        self._entries={}

    @contextmanager
    def hold(self,campaign):
        with self._guard:
            entry=self._entries.setdefault(campaign,[threading.RLock(),0])
            # Count both holders and waiters so a waiting lock cannot be replaced.
            entry[1]+=1
        try:
            with entry[0]:yield
        finally:
            with self._guard:
                entry[1]-=1
                if not entry[1]:del self._entries[campaign]
