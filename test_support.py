"""Doble explícito SOLO para pruebas; nunca importado por el servidor."""
import copy
import secrets
import threading
import os
from firebase_store import Conflict, FirestoreStore, digest, words
from campaign_versions import state_version


class TestStore:
    __test__=False
    def __init__(self):
        self.campaigns={};self.sessions={};self.members={};self.invites={};self.actions={};self.pages={};self.workspaces={};self.preparations={};self.lock=threading.RLock()
    def health(self):pass
    def create(self,title,state,name):
        cid=secrets.token_hex(12);pid=secrets.token_hex(8);token=secrets.token_hex(32);invite=secrets.token_hex(24)
        state=self._light_state(cid,state)
        self.campaigns[cid]=({'id':cid,'title':title,'invite':invite,'version':0,'stateVersion':0,
                            'snapshot':'state-0','stateVersionSnapshot':'state-0'},copy.deepcopy(state))
        me={'id':pid,'name':name,'host':1,'campaign':cid};self.sessions[digest(token)]=me;self.members[cid]=[me];self.invites[invite]=cid
        return token
    def invited_campaign(self,invite):
        if invite not in self.invites:raise ValueError('Invitación no válida')
        return self.invites[invite]
    def join(self,invite,name,*,campaign=None):
        with self.lock:
            if invite not in self.invites:raise ValueError('Invitación no válida')
            cid=self.invites[invite]
            if campaign is not None and cid!=campaign:raise Conflict('La invitación ha cambiado; vuelve a entrar')
            token=secrets.token_hex(32);me={'id':secrets.token_hex(8),'name':name,'host':0,'campaign':cid}
            self.sessions[digest(token)]=me;self.members[cid].append(me)
            meta=self.campaigns[cid][0];meta['stateVersion']=state_version(meta)
            meta['stateVersionSnapshot']=meta['snapshot'];meta['version']+=1
            return token
    def identity(self,token):
        if digest(token) not in self.sessions:raise PermissionError('Sesión desconocida')
        return copy.deepcopy(self.sessions[digest(token)])
    def metadata(self,cid):return copy.deepcopy(self.campaigns[cid][0])
    def load(self,cid):return copy.deepcopy(self.campaigns[cid])
    def _light_state(self,cid,state):
        if state.get('ruleset')!='rule-pack':return state
        from rule_workspace_asset import detach
        light,asset=detach(state)
        if asset is not None:self.workspaces[cid,asset['reference']['sha256']]=asset['packed']
        import adventure_source
        light,asset=adventure_source.detach(light)
        if asset is not None:
            if not hasattr(self,'adventure_sources'):self.adventure_sources={}
            self.adventure_sources[cid,asset['reference']['sha256']]=asset['packed']
        return light
    def load_adventure_source(self,cid,reference):
        import adventure_source
        return adventure_source.decode(reference,self.adventure_sources[cid,reference['sha256']])
    def load_rule_workspace(self,cid,reference):
        import json
        from rule_workspace_asset import decode
        return json.loads(decode(reference,self.workspaces[cid,reference['sha256']]))
    def players(self,cid):return [{k:v for k,v in p.items() if k!='campaign'} for p in self.members[cid]]
    def completed(self,cid,aid,actor,fingerprint):
        marker=self.actions.get((cid,aid))
        if marker and marker!=(actor,fingerprint):raise Conflict('Identificador reutilizado')
        return bool(marker)
    def begin_rule_preparation(self,cid,identifier,actor,prepared,allow_create=True):
        from rule_preparation_attempt import check_attempt,key,pack,unpack,input_request,inputs_match
        if identifier!=key(actor,prepared['sha256']):raise ValueError('Identificador de intento inválido')
        original=input_request(prepared)
        with self.lock:
            existing=self.preparations.get((cid,identifier))
            if existing is None:
                if not allow_create:return None
                existing={'actor':actor,'requestSha256':prepared['sha256'],'sourceScheme':prepared['sourceScheme'],'phase':'started','inputData':pack(original)}
                import hashlib
                from model_config import model_name
                from rule_pack_authoring import PROMPT
                existing.update({'model':model_name(),'promptSha256':prepared.get('promptSha256',hashlib.sha256(PROMPT.encode()).hexdigest())})
                self.preparations[cid,identifier]=existing
                return {**copy.deepcopy(existing),'fresh':True}
            if existing.get('phase')=='confirmed':raise Conflict('Preparación ya confirmada')
            check_attempt(existing,actor,prepared['sha256'])
            if not inputs_match(unpack(existing['inputData']),original,existing['sourceScheme'],prepared['sourceScheme']):raise Conflict('Otra fuente')
            return {**copy.deepcopy(existing),'fresh':False}
    def save_rule_preparation_response(self,cid,identifier,actor,request_sha,data):
        from rule_preparation_attempt import key,unpack
        if identifier!=key(actor,request_sha):raise ValueError('Identificador de intento inválido')
        unpack(data)
        with self.lock:self.preparations[cid,identifier].update({'responseData':data,'phase':'captured'})
    def read_rule_preparation(self,cid,actor,request_sha):
        from rule_preparation_attempt import key,check_attempt
        import re
        if not isinstance(request_sha,str) or not re.fullmatch('[a-f0-9]{64}',request_sha):raise ValueError('Huella de preparación inválida')
        data=self.preparations.get((cid,key(actor,request_sha)))
        if data is not None and data.get('phase')=='confirmed':return None
        if data is not None:check_attempt(data,actor,request_sha)
        return copy.deepcopy(data)
    def action_random_seed(self,cid,aid,actor,fingerprint,version):
        with self.lock:
            if not hasattr(self,'randomness'):self.randomness={}
            existing=self.randomness.setdefault((cid,aid),{'actor':actor,'fingerprint':fingerprint,'version':version,'seed':secrets.token_bytes(32)})
            if existing.get('phase')=='confirmed' or any(existing.get(k)!=v for k,v in [('actor',actor),('fingerprint',fingerprint),('version',version)]):
                raise Conflict('Reserva de dados incompatible o confirmada')
            return existing['seed']
    def check_action_random_seed(self,cid,aid,actor,fingerprint,version):
        with self.lock:
            existing=getattr(self,'randomness',{}).get((cid,aid))
            if existing is None:return None
            if existing.get('phase')=='confirmed' or any(existing.get(k)!=v for k,v in [('actor',actor),('fingerprint',fingerprint),('version',version)]):
                raise Conflict('Reserva de dados incompatible o confirmada')
            return existing['seed']
    def commit(self,cid,aid,actor,fingerprint,version,state,title=None,preparation_key=None,randomness=False,randomness_key=None):
        import re
        if randomness_key is not None and (randomness is not True or not isinstance(randomness_key,str) or not re.fullmatch('pending:[a-f0-9]{64}',randomness_key)):
            raise ValueError('Clave de confirmación de dados inválida')
        with self.lock:
            if self.completed(cid,aid,actor,fingerprint):return True
            if self.campaigns[cid][0]['version']!=version:raise Conflict('Estado antiguo')
            meta=copy.deepcopy(self.campaigns[cid][0]);meta['version']+=1;meta['stateVersion']=meta['version']
            meta['snapshot']='state-'+str(meta['version']);meta['stateVersionSnapshot']=meta['snapshot']
            if title is not None:meta['title']=title
            self.campaigns[cid]=(meta,copy.deepcopy(self._light_state(cid,state)));self.actions[cid,aid]=(actor,fingerprint)
            if preparation_key is not None:self.preparations[cid,preparation_key]={'actor':actor,'phase':'confirmed'}
            if randomness:self.randomness[cid,aid if randomness_key is None else randomness_key]={'phase':'confirmed'}
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
