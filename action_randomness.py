"""Replay server dice from a private seed reserved before the first draw."""
import hmac
import re


class ActionRandomness:
    def __init__(self,store,campaign,action,actor,fingerprint,version,reservation=None):
        self.store=store;self.campaign=campaign;self.action=action
        self.actor=actor;self.fingerprint=fingerprint;self.version=version
        self.seed=None;self.counter=0
        self.reservation_key=action
        self.scoped=reservation is not None
        if reservation is not None:
            if not isinstance(reservation,dict) or set(reservation)!={'key','fingerprint','version'} or not isinstance(reservation['key'],str) or not re.fullmatch('pending:[a-f0-9]{64}',reservation['key']) or not isinstance(reservation['fingerprint'],str) or not re.fullmatch('[a-f0-9]{64}',reservation['fingerprint']) or type(reservation['version'])!=int or reservation['version']!=0:
                raise ValueError('Descriptor de reserva de dados inválido')
            self.reservation_key=reservation['key'];self.fingerprint=reservation['fingerprint'];self.version=0

    def verify_if_unused(self):
        # A retry must not bypass an existing server stream by replacing it
        # with physical/no dice. No reservation is created by this check.
        if self.scoped and self.seed is None:
            self.store.check_action_random_seed(self.campaign,self.reservation_key,self.actor,self.fingerprint,self.version)

    def __call__(self,sides):
        if type(sides)!=int or not 2<=sides<=1000000:raise ValueError('Dado fuera del límite operativo')
        if self.seed is None:
            self.seed=self.store.action_random_seed(self.campaign,self.reservation_key,self.actor,self.fingerprint,self.version)
        # Rejection sampling avoids modulo bias. The stream is bound to this
        # exact request/version, private to the server, and stable after restart.
        limit=(1<<256)-((1<<256)%sides)
        while True:
            value=int.from_bytes(hmac.digest(self.seed,f'{self.counter}:{sides}'.encode(),'sha256'),'big')
            self.counter+=1
            if value<limit:return value%sides+1
