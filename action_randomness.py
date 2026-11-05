"""Replay server dice from a private seed reserved before the first draw."""
import hmac


class ActionRandomness:
    def __init__(self,store,campaign,action,actor,fingerprint,version):
        self.store=store;self.campaign=campaign;self.action=action
        self.actor=actor;self.fingerprint=fingerprint;self.version=version
        self.seed=None;self.counter=0

    def __call__(self,sides):
        if type(sides)!=int or not 2<=sides<=1000000:raise ValueError('Dado fuera del límite operativo')
        if self.seed is None:
            self.seed=self.store.action_random_seed(self.campaign,self.action,self.actor,self.fingerprint,self.version)
        # Rejection sampling avoids modulo bias. The stream is bound to this
        # exact request/version, private to the server, and stable after restart.
        limit=(1<<256)-((1<<256)%sides)
        while True:
            value=int.from_bytes(hmac.digest(self.seed,f'{self.counter}:{sides}'.encode(),'sha256'),'big')
            self.counter+=1
            if value<limit:return value%sides+1
