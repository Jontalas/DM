"""Persistencia exclusiva en Cloud Firestore. Sin fallback local en producción."""
import hashlib
import json
import os
import re
import secrets
import threading
import time
import unicodedata
import zlib
from collections import OrderedDict

BOOKS = {'trey': 'Trey.pdf', 'reglas': 'Pathfinder_en_escastellano_subido para_elgrimorio.pdf', 'bestiario': 'bestiario pathfinder spanish [Unlocked by www.freemypdf.com].pdf'}
CHUNK_BYTES = 192 * 1024
MAX_STATE_BYTES = 16 * 1024 * 1024
BOOK_BATCH_PAGES = 20


class Conflict(ValueError): pass
class Unavailable(RuntimeError): pass


def digest(value): return hashlib.sha256(value.encode()).hexdigest()


def words(text):
    text=''.join(c for c in unicodedata.normalize('NFD',text.lower()) if unicodedata.category(c)!='Mn')
    stop={'que','para','como','una','los','las','del','con','por','hay','puedo','tiene','esta','sus','desde','este','sin','son','mas'}
    return list(dict.fromkeys(w for w in re.findall(r'\w{3,}',text) if w not in stop))


def encode_state(state):
    raw=json.dumps(state,ensure_ascii=False,separators=(',',':'),sort_keys=True).encode()
    if len(raw)>MAX_STATE_BYTES: raise ValueError('La campaña supera el límite operativo de 16 MiB; exporta y divide la campaña')
    packed=zlib.compress(raw)
    return [packed[i:i+CHUNK_BYTES] for i in range(0,len(packed),CHUNK_BYTES)]


def firebase_clients():
    from google.cloud import firestore
    from google.oauth2 import service_account
    from google.auth.credentials import AnonymousCredentials
    project=os.environ.get('FIREBASE_PROJECT_ID')
    if not project: raise Unavailable('Configura FIREBASE_PROJECT_ID y las credenciales de Firebase en el servidor')
    options={}
    if os.environ.get('FIRESTORE_EMULATOR_HOST'):
        if os.environ.get('RENDER'): raise Unavailable('El emulador Firestore no se permite en Render')
        options['credentials']=AnonymousCredentials()
    elif os.environ.get('FIREBASE_SERVICE_ACCOUNT_JSON'):
        try: options['credentials']=service_account.Credentials.from_service_account_info(json.loads(os.environ['FIREBASE_SERVICE_ACCOUNT_JSON']))
        except (ValueError,KeyError) as exc: raise Unavailable('FIREBASE_SERVICE_ACCOUNT_JSON no contiene una cuenta de servicio válida') from exc
    # Otherwise the official client uses GOOGLE_APPLICATION_CREDENTIALS / ADC.
    return firestore.Client(project=project,**options),options.get('credentials')


class FirestoreStore:
    def __init__(self, client, credentials=None):
        self.client=client;self.credentials=credentials
        self._health_until=0
        self._health_lock=threading.Lock()
        self._reader=None
        self._reader_lock=threading.Lock()
        self._workspace_cache=OrderedDict()
        self._adventure_cache=OrderedDict()
        self._workspace_lock=threading.RLock()
        self.prefix=os.environ.get('FIREBASE_COLLECTION_PREFIX','cronicas')
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,60}',self.prefix): raise ValueError('Prefijo Firebase inválido')

    @classmethod
    def from_environment(cls): return cls(*firebase_clients())
    def collection(self,name): return self.client.collection(self.prefix+'_'+name)
    def campaign(self,cid): return self.collection('campaigns').document(cid)

    def health(self):
        # A successful missing-document lookup also proves API/credentials availability.
        # Render probes frequently. Share a short-lived successful result across threads.
        with self._health_lock:
            if time.monotonic()<self._health_until:return
            self.collection('system').document('health').get(timeout=5)
            self._health_until=time.monotonic()+60

    def _stage(self,cid,state):
        from google.cloud import firestore
        if state.get('ruleset')=='rule-pack':
            from rule_workspace_asset import detach
            state,asset=detach(state)
            if asset is not None:self._stage_rule_workspace(cid,asset)
            import adventure_source
            state,asset=adventure_source.detach(state)
            if asset is not None:self._stage_adventure_source(cid,asset)
        chunks=encode_state(state);sid=secrets.token_hex(16)
        # Keep each write request well below Firestore's 10 MiB request limit.
        for start in range(0,len(chunks),20):
            batch=self.client.batch()
            for i in range(start,min(start+20,len(chunks))):
                batch.create(self.campaign(cid).collection('snapshots').document(f'{sid}-{i}'),{'data':chunks[i],'createdAt':firestore.SERVER_TIMESTAMP})
            batch.commit()
        return {'snapshot':sid,'chunks':len(chunks)}

    def _cache_workspace(self,cid,reference,raw):
        with self._workspace_lock:
            key=(cid,reference['sha256']);self._workspace_cache[key]=raw;self._workspace_cache.move_to_end(key)
            while len(self._workspace_cache)>8:self._workspace_cache.popitem(last=False)

    def _fetch_rule_workspace(self,cid,reference):
        from rule_workspace_asset import decode
        from google.api_core.exceptions import GoogleAPICallError
        try:snap=self.campaign(cid).collection('ruleWorkspaces').document(reference['sha256']).get(timeout=10,retry=None)
        except GoogleAPICallError as error:raise Unavailable('No se pueden consultar las preparaciones privadas ahora') from error
        if not snap.exists:raise Unavailable('Faltan las fuentes privadas; conserva la copia antes de corregir la campaña')
        try:return decode(reference,snap.to_dict()['data'])
        except (KeyError,ValueError,TypeError) as error:raise Unavailable('Las preparaciones privadas no están íntegras') from error

    def load_rule_workspace(self,cid,reference):
        from rule_workspace_asset import validate_ref
        validate_ref(reference);key=(cid,reference['sha256'])
        with self._workspace_lock:
            raw=self._workspace_cache.get(key)
            if raw is not None:self._workspace_cache.move_to_end(key)
            else:
                raw=self._fetch_rule_workspace(cid,reference);self._cache_workspace(cid,reference,raw)
        return json.loads(raw)

    def _stage_rule_workspace(self,cid,asset):
        from google.cloud import firestore
        from google.api_core.exceptions import AlreadyExists
        reference=asset['reference'];key=(cid,reference['sha256'])
        with self._workspace_lock:
            if key in self._workspace_cache:return
        ref=self.campaign(cid).collection('ruleWorkspaces').document(reference['sha256'])
        try:ref.create({'data':asset['packed'],'createdAt':firestore.SERVER_TIMESTAMP})
        except AlreadyExists:
            raw=self._fetch_rule_workspace(cid,reference)
            self._cache_workspace(cid,reference,raw);return
        self._cache_workspace(cid,reference,asset['raw'])

    def _cache_adventure(self,cid,ref,record):
        with self._workspace_lock:
            key=(cid,ref['sha256']);self._adventure_cache[key]=record;self._adventure_cache.move_to_end(key)
            while len(self._adventure_cache)>8:self._adventure_cache.popitem(last=False)

    def load_adventure_source(self,cid,reference):
        import adventure_source
        from google.api_core.exceptions import GoogleAPICallError
        adventure_source.validate_ref(reference);key=(cid,reference['sha256'])
        with self._workspace_lock:
            if key in self._adventure_cache:
                record=self._adventure_cache[key]
                if adventure_source.reference(record)!=reference:raise Unavailable('Referencia de aventura incompatible')
                self._adventure_cache.move_to_end(key);return json.loads(json.dumps(record))
            try:snap=self.campaign(cid).collection('adventureSources').document(reference['sha256']).get(timeout=10,retry=None)
            except GoogleAPICallError as error:raise Unavailable('No se puede recuperar la fuente privada de aventura ahora') from error
            if not snap.exists:raise Unavailable('Falta la fuente privada de aventura; conserva las copias originales')
            try:record=adventure_source.decode(reference,snap.to_dict()['data'])
            except (ValueError,KeyError,TypeError) as error:raise Unavailable('La fuente privada de aventura no está íntegra') from error
            self._cache_adventure(cid,reference,record);return json.loads(json.dumps(record))

    def _stage_adventure_source(self,cid,asset):
        from google.cloud import firestore
        from google.api_core.exceptions import AlreadyExists
        import adventure_source
        ref=asset['reference'];key=(cid,ref['sha256'])
        with self._workspace_lock:
            if key in self._adventure_cache:return
        target=self.campaign(cid).collection('adventureSources').document(ref['sha256'])
        try:target.create({'data':asset['packed'],'createdAt':firestore.SERVER_TIMESTAMP})
        except AlreadyExists:self.load_adventure_source(cid,ref);return
        self._cache_adventure(cid,ref,adventure_source.decode(ref,asset['packed']))

    def _decode(self,cid,meta):
        refs=[self.campaign(cid).collection('snapshots').document(f"{meta['snapshot']}-{i}") for i in range(meta['chunks'])]
        docs={snap.id:snap for snap in self.client.get_all(refs)}
        try: packed=b''.join(docs[ref.id].to_dict()['data'] for ref in refs)
        except (KeyError,TypeError) as exc: raise Unavailable('La instantánea de campaña está incompleta') from exc
        return json.loads(zlib.decompress(packed))

    def metadata(self,cid):
        snap=self.campaign(cid).get()
        if not snap.exists: raise ValueError('Campaña inexistente')
        return {'id':cid,**snap.to_dict()}

    def load(self,cid):
        meta=self.metadata(cid)
        return meta,self._decode(cid,meta)

    def create(self,title,state,name):
        cid=secrets.token_urlsafe(12);token=secrets.token_urlsafe(32);pid=secrets.token_urlsafe(10);invite=secrets.token_urlsafe(24)
        snapshot=self._stage(cid,state)
        person={'campaign':cid,'id':pid,'name':name[:80],'host':1}
        batch=self.client.batch()
        batch.create(self.campaign(cid),{'title':title[:120],'invite':invite,'version':0,**snapshot})
        batch.create(self.collection('sessions').document(digest(token)),person)
        batch.create(self.campaign(cid).collection('members').document(pid),person)
        batch.create(self.collection('invites').document(digest(invite)),{'campaign':cid})
        batch.commit()
        return token

    def join(self,invite,name):
        from google.cloud import firestore
        token=secrets.token_urlsafe(32);pid=secrets.token_urlsafe(10)
        @firestore.transactional
        def commit(tx):
            invitation=self.collection('invites').document(digest(invite)).get(transaction=tx)
            if not invitation.exists: raise ValueError('Invitación no válida')
            cid=invitation.to_dict()['campaign'];ref=self.campaign(cid);meta=ref.get(transaction=tx)
            if not meta.exists: raise ValueError('Campaña inexistente')
            person={'campaign':cid,'id':pid,'name':str(name)[:80],'host':0}
            tx.create(self.collection('sessions').document(digest(token)),person)
            tx.create(ref.collection('members').document(pid),person)
            tx.update(ref,{'version':meta.to_dict()['version']+1})
        commit(self.client.transaction())
        return token

    def identity(self,token):
        if not token: raise PermissionError('Sesión desconocida. Vuelve a entrar con la invitación')
        snap=self.collection('sessions').document(digest(token)).get()
        if not snap.exists: raise PermissionError('Sesión desconocida. Vuelve a entrar con la invitación')
        return snap.to_dict()

    def players(self,cid):
        return [{k:v for k,v in s.to_dict().items() if k!='campaign'} for s in self.campaign(cid).collection('members').stream()]

    def _check_marker(self,data,actor,fingerprint):
        if data['actor']!=actor or data['fingerprint']!=fingerprint:
            raise Conflict('El identificador ya pertenece a otra acción')
        return True

    def completed(self,cid,aid,actor,fingerprint):
        snap=self.campaign(cid).collection('actions').document(digest(aid)).get()
        return self._check_marker(snap.to_dict(),actor,fingerprint) if snap.exists else False

    def begin_rule_preparation(self,cid,identifier,actor,prepared,allow_create=True):
        from google.cloud import firestore
        from google.api_core.exceptions import AlreadyExists
        from rule_preparation_attempt import check_attempt,key,pack,unpack
        from model_config import model_name
        from rule_pack_authoring import PROMPT
        if identifier!=key(actor,prepared['sha256']):raise ValueError('Identificador de intento inválido')
        ref=self.campaign(cid).collection('rulePreparationAttempts').document(identifier)
        data={'actor':actor,'requestSha256':prepared['sha256'],'sourceScheme':prepared['sourceScheme'],
            'phase':'started','inputData':pack(prepared['request']),'createdAt':firestore.SERVER_TIMESTAMP}
        if allow_create:
            data.update({'model':model_name(),'promptSha256':prepared.get('promptSha256',hashlib.sha256(PROMPT.encode()).hexdigest())})
            try:ref.create(data);return {**data,'fresh':True}
            except AlreadyExists:pass
        snapshot=ref.get()
        if not snapshot.exists:return None
        existing=snapshot.to_dict()
        if existing.get('phase')=='confirmed':raise Conflict('Esta preparación ya fue confirmada; no se repetirá la inferencia')
        check_attempt(existing,actor,prepared['sha256'])
        from rule_pack_authoring import canonical
        if canonical(unpack(existing['inputData']))!=canonical(prepared['request']):raise Conflict('La fuente original del intento no coincide')
        return {**existing,'fresh':False}

    def save_rule_preparation_response(self,cid,identifier,actor,request_sha,data):
        from rule_preparation_attempt import key,unpack
        if identifier!=key(actor,request_sha):raise ValueError('Identificador de intento inválido')
        unpack(data)
        self.campaign(cid).collection('rulePreparationAttempts').document(identifier).update({'responseData':data,'phase':'captured'})

    def read_rule_preparation(self,cid,actor,request_sha):
        from rule_preparation_attempt import key,check_attempt
        if not isinstance(request_sha,str) or not re.fullmatch('[a-f0-9]{64}',request_sha):raise ValueError('Huella de preparación inválida')
        snapshot=self.campaign(cid).collection('rulePreparationAttempts').document(key(actor,request_sha)).get(timeout=10,retry=None)
        if not snapshot.exists:return None
        data=snapshot.to_dict()
        if data.get('phase')=='confirmed':return None
        check_attempt(data,actor,request_sha);return data

    def action_random_seed(self,cid,aid,actor,fingerprint,version):
        from google.api_core.exceptions import AlreadyExists
        ref=self.campaign(cid).collection('ruleActionRandomness').document(digest(aid))
        data={'actor':actor,'fingerprint':fingerprint,'version':version,'seed':secrets.token_bytes(32)}
        try:ref.create(data);return data['seed']
        except AlreadyExists:pass
        existing=ref.get().to_dict()
        if existing is None or existing.get('phase')=='confirmed':raise Conflict('Esta tirada ya fue confirmada; no se generarán dados de nuevo')
        if any(existing.get(key)!=data[key] for key in ('actor','fingerprint','version')):
            raise Conflict('El identificador de tirada pertenece a otra acción')
        seed=existing.get('seed')
        if not isinstance(seed,bytes) or len(seed)!=32:raise Unavailable('La reserva de dados no está íntegra')
        return seed

    def check_action_random_seed(self,cid,aid,actor,fingerprint,version):
        existing=self.campaign(cid).collection('ruleActionRandomness').document(digest(aid)).get().to_dict()
        if existing is None:return None
        if existing.get('phase')=='confirmed' or any(existing.get(key)!=value for key,value in [('actor',actor),('fingerprint',fingerprint),('version',version)]):
            raise Conflict('La solicitud conserva otra reserva de dados o ya está confirmada')
        seed=existing.get('seed')
        if not isinstance(seed,bytes) or len(seed)!=32:raise Unavailable('La reserva de dados no está íntegra')
        return seed

    def commit(self,cid,aid,actor,fingerprint,version,state,title=None,preparation_key=None,randomness=False,randomness_key=None):
        from google.cloud import firestore
        from google.api_core.exceptions import AlreadyExists, FailedPrecondition
        if randomness_key is not None and (randomness is not True or not isinstance(randomness_key,str) or not re.fullmatch('pending:[a-f0-9]{64}',randomness_key)):
            raise ValueError('Clave de confirmación de dados inválida')
        # Optimistic CAS avoids holding read locks while concurrent clients commit.
        # The timestamp precondition and marker creation belong to the SAME atomic batch.
        ref=self.campaign(cid);marker=ref.collection('actions').document(digest(aid))
        previous=marker.get()
        if previous.exists:return self._check_marker(previous.to_dict(),actor,fingerprint)
        meta=ref.get()
        if not meta.exists:raise ValueError('Campaña inexistente')
        if meta.to_dict()['version']!=version:raise Conflict('La mesa ha cambiado. Revisa tu acción antes de enviarla')
        staged=self._stage(cid,state)
        update={'version':version+1,**staged}
        if title is not None:update['title']=str(title)[:120]
        batch=self.client.batch()
        batch.update(ref,update,option=firestore.LastUpdateOption(meta.update_time))
        batch.create(marker,{'actor':actor,'fingerprint':fingerprint,'version':version+1})
        if randomness:
            batch.set(ref.collection('ruleActionRandomness').document(digest(aid if randomness_key is None else randomness_key)),{'phase':'confirmed'})
        if preparation_key is not None:
            batch.set(ref.collection('rulePreparationAttempts').document(preparation_key),
                {'actor':actor,'phase':'confirmed'})
        try:batch.commit()
        except (AlreadyExists,FailedPrecondition):
            previous=marker.get()
            if previous.exists:return self._check_marker(previous.to_dict(),actor,fingerprint)
            raise Conflict('La mesa ha cambiado. Revisa tu acción antes de enviarla') from None
        return False

    def counts(self):
        return {key:(self.collection('manuals').document(key).get().to_dict() or {}).get('pages',0) for key in BOOKS}

    def search(self,query,book=None):
        from google.cloud.firestore_v1.base_query import FieldFilter
        tokens=words(query)[:12]
        if not tokens:return []
        if book and book not in BOOKS: raise ValueError('Libro desconocido')
        results=[]
        for key in [book] if book else BOOKS:
            ref=self.collection('manuals').document(key);meta=ref.get().to_dict()
            if not meta or not meta.get('activeIndex'):continue
            pages=ref.collection('indexes').document(meta['activeIndex']).collection('pages')
            for snap in pages.where(filter=FieldFilter('tokens','array_contains_any',tokens)).limit(50).stream():
                data=snap.to_dict();text=data['text'];score=len(set(tokens).intersection(words(text)))
                results.append({'book':key,'page':data['page'],'text':text,'score':score})
        results.sort(key=lambda r:(-r['score'],r['book'],r['page']))
        return [{k:v for k,v in r.items() if k!='score'} for r in results[:5]]

    def index_book(self,book,pages):
        if book not in BOOKS:raise ValueError('Libro desconocido')
        if not isinstance(pages,list) or not pages or any(type(p.get('page'))!=int or p['page']<1 or not isinstance(p.get('text'),str) for p in pages):
            raise ValueError('Índice inválido')
        sid=secrets.token_hex(16);ref=self.collection('manuals').document(book);collection=ref.collection('indexes').document(sid).collection('pages')
        def commit_pages(group):
            from google.api_core.exceptions import InvalidArgument
            batch=self.client.batch()
            for page in group:batch.set(collection.document(str(page['page'])),{**page,'tokens':words(page['text'])})
            try:
                batch.commit()
            except InvalidArgument as exc:
                # Firestore also counts token index entries toward transaction size.
                # Split only this size error; permission and validation errors must surface.
                if 'transaction too big' not in str(exc).lower():raise
                if len(group)==1:
                    raise ValueError(f'La página {group[0]["page"]} de {book} supera el tamaño permitido por Firestore') from exc
                middle=len(group)//2
                commit_pages(group[:middle])
                commit_pages(group[middle:])
        for start in range(0,len(pages),BOOK_BATCH_PAGES):
            commit_pages(pages[start:start+BOOK_BATCH_PAGES])
        ref.set({'activeIndex':sid,'pages':len(pages)})

    def open_book(self,book):
        from google.cloud import storage
        from google.api_core.exceptions import NotFound
        bucket=os.environ.get('FIREBASE_STORAGE_BUCKET')
        if not bucket:raise FileNotFoundError('Configura FIREBASE_STORAGE_BUCKET e instala los PDF en Firebase Storage')
        client=storage.Client(project=self.client.project,credentials=self.credentials)
        blob=client.bucket(bucket).blob(f'manuals/{book}/original.pdf')
        try:blob.reload()
        except NotFound as exc:raise FileNotFoundError('Manual no instalado en Firebase Storage') from exc
        return blob.open('rb',chunk_size=256*1024),blob.size

    def upload_book(self,book,path):
        from google.cloud import storage
        bucket=os.environ.get('FIREBASE_STORAGE_BUCKET')
        if not bucket:raise ValueError('Configura FIREBASE_STORAGE_BUCKET')
        client=storage.Client(project=self.client.project,credentials=self.credentials)
        client.bucket(bucket).blob(f'manuals/{book}/original.pdf').upload_from_filename(str(path),content_type='application/pdf')

    def reader_assets(self):
        from book_pages import ReaderAssets
        from google.cloud import storage
        from google.api_core.exceptions import NotFound
        with self._reader_lock:
            if self._reader is None:
                name=os.environ.get('FIREBASE_STORAGE_BUCKET')
                if not name:raise FileNotFoundError('Lector por páginas sin configurar')
                bucket=storage.Client(project=self.client.project,credentials=self.credentials).bucket(name)
                def download(path):
                    try:return bucket.blob(path).download_as_bytes(timeout=30)
                    except NotFound as exc:raise FileNotFoundError('Manual pendiente de preparación para lectura por páginas') from exc
                self._reader=ReaderAssets(download)
            return self._reader
