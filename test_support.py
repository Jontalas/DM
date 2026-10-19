"""Doble explícito SOLO para pruebas; nunca importado por el servidor."""
import copy
import secrets
import threading
import os
from firebase_store import Conflict, FirestoreStore, digest, words


class TestStore:
    __test__=False
    def __init__(self):
        self.campaigns={};self.sessions={};self.members={};self.invites={};self.actions={};self.pages={};self.lock=threading.RLock()
    def health(self):pass
    def create(self,title,state,name):
        cid=secrets.token_hex(12);pid=secrets.token_hex(8);token=secrets.token_hex(32);invite=secrets.token_hex(24)
        self.campaigns[cid]=({'id':cid,'title':title,'invite':invite,'version':0},copy.deepcopy(state))
        me={'id':pid,'name':name,'host':1,'campaign':cid};self.sessions[digest(token)]=me;self.members[cid]=[me];self.invites[invite]=cid
        return token
    def join(self,invite,name):
        with self.lock:
            if invite not in self.invites:raise ValueError('Invitación no válida')
            cid=self.invites[invite];token=secrets.token_hex(32);me={'id':secrets.token_hex(8),'name':name,'host':0,'campaign':cid}
            self.sessions[digest(token)]=me;self.members[cid].append(me);self.campaigns[cid][0]['version']+=1
            return token
    def identity(self,token):
        if digest(token) not in self.sessions:raise PermissionError('Sesión desconocida')
        return copy.deepcopy(self.sessions[digest(token)])
    def metadata(self,cid):return copy.deepcopy(self.campaigns[cid][0])
    def load(self,cid):return copy.deepcopy(self.campaigns[cid])
    def players(self,cid):return [{k:v for k,v in p.items() if k!='campaign'} for p in self.members[cid]]
    def completed(self,cid,aid,actor,fingerprint):
        marker=self.actions.get((cid,aid))
        if marker and marker!=(actor,fingerprint):raise Conflict('Identificador reutilizado')
        return bool(marker)
    def commit(self,cid,aid,actor,fingerprint,version,state,title=None):
        with self.lock:
            if self.completed(cid,aid,actor,fingerprint):return True
            if self.campaigns[cid][0]['version']!=version:raise Conflict('Estado antiguo')
            meta=copy.deepcopy(self.campaigns[cid][0]);meta['version']+=1
            if title is not None:meta['title']=title
            self.campaigns[cid]=(meta,copy.deepcopy(state));self.actions[cid,aid]=(actor,fingerprint)
            return False
    def index_book(self,book,pages):self.pages[book]=copy.deepcopy(pages)
    def counts(self):return {b:len(self.pages.get(b,[])) for b in ['reglas','bestiario','trey']}
    def search(self,query,book=None):
        terms=set(words(query));result=[]
        for key,pages in self.pages.items():
            if book and key!=book:continue
            result.extend({'book':key,**page} for page in pages if terms.intersection(words(page['text'])))
        return result[:5]


def make_store():
    if os.environ.get('FIRESTORE_EMULATOR_HOST'):
        store=FirestoreStore.from_environment();store.prefix='tests_'+secrets.token_hex(6)
    else:store=TestStore()
    store.index_book('reglas',[{'page':194,'text':'Texto de prueba: diagonales y movimiento.'}])
    return store
