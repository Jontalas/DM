"""Mesa de rol: Cloud Firestore, Firebase Storage y Claude Haiku."""
import hashlib
import json
import os
import threading
import time
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from engine import apply_action, initial_state
from firebase_store import BOOKS, FirestoreStore, Conflict, Unavailable
from claude_dm import ai_reply, model_name
import adventure
import adventure_modules
import rulesets
from narrative_text import repair_text

ROOT=Path(__file__).resolve().parent
# Local paths are only for extracting/importing PDF assets, never for databases.
DATA_DIR=Path(os.environ.get('DATA_DIR',str(ROOT/'data')))
INDEX_DIR=Path(os.environ.get('INDEX_DIR',str(DATA_DIR)))
BOOKS_DIR=Path(os.environ.get('BOOKS_DIR',str(Path.home()/'Desktop')))
STORE=None
READER=None  # Explicit test injection only; production obtains private assets from Storage.
LOCK=threading.RLock()


def initialize():
    global STORE
    if STORE is None: STORE=FirestoreStore.from_environment()
    STORE.health()
    model_name()


def repository():
    if STORE is None:raise Unavailable('Firebase sin inicializar. Configura proyecto y credenciales en el servidor')
    return STORE


def reader_assets():
    return READER if READER is not None else repository().reader_assets()


def search(query,book=None):return repository().search(query,book)
def identity(token):return repository().identity(token)
def load(cid):
    row,state=repository().load(cid);rulesets.identify(state)
    return row,state


def view(row,state,me):
    state=json.loads(json.dumps(state))
    module_view=adventure_modules.public_view(state)
    # Repair historical model prose on the copy, preserving originals in storage/export.
    for message in state['messages']:
        if message.get('kind')=='director':message['text']=repair_text(message.get('text',''))
    if state.get('adventure'):state['adventure']['summary']=repair_text(state['adventure'].get('summary',''))
    if state.get('directorMemory'):state['directorMemory']=repair_text(state['directorMemory'])
    state['messages']=[m for m in state['messages'] if m.get('visibility','public')=='public' or me['host'] or m.get('owner')==me['id']]
    if not me['host']:
        state.pop('secrets',None)
        state.pop('directorNotes',None)
        state.pop('directorMemory',None)
        state.pop('adventureModule',None)
    if module_view:state['adventureModuleView']=module_view
    state['private']={k:v for k,v in state.get('private',{}).items() if k==me['id'] or me['host']}
    return {'id':row['id'],'title':row['title'],'version':row['version'],'state':state,'me':me,'players':repository().players(row['id']),'invite':row['invite'] if me['host'] else None}


def open_book(book):
    if book not in BOOKS:raise ValueError('Libro desconocido')
    if os.environ.get('FIREBASE_STORAGE_BUCKET'):return repository().open_book(book)
    if os.environ.get('RENDER'):raise FileNotFoundError('Configura FIREBASE_STORAGE_BUCKET e instala los manuales')
    path=BOOKS_DIR/BOOKS[book]
    return path.open('rb'),path.stat().st_size


def fingerprint(body):
    return hashlib.sha256(json.dumps(body,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()


def queue_investigation(state,body,me):
    spec=adventure_modules.investigation(state,body,me)
    apply_action(state,{'type':'request_check',**{k:v for k,v in spec.items() if k!='opportunity'}},{**me,'host':True})
    state['pending'][-1]['investigation']=spec['opportunity']
    state['pending'][-1]['source']='Investigación de aventura; Percepción: Reglas PDF p.101. CD adjudicada por su autor.'


def execute_action(body,me):
    aid=str(body['id'])
    if not aid or len(aid)>200:raise ValueError('Identificador de acción inválido')
    store=repository();cid=me['campaign'];signature=fingerprint(body)
    with LOCK:
        if store.completed(cid,aid,me['id'],signature):return {'duplicate':True}
        row,state=load(cid)
        if body.get('version')!=row['version']:raise Conflict('La mesa ha cambiado. Revisa tu acción antes de enviarla')
        title=None
        if body['type']=='import':
            if not me['host']:raise PermissionError('Solo el anfitrión importa')
            data=body['campaign']
            if data.get('format')!='cronicas-1':raise ValueError('Formato incompatible')
            state=data['state']
            rulesets.identify(state)
            for key in initial_state({}):
                if key not in state:raise ValueError('Falta '+key)
            for character in state['characters']:character['owner']=me['id']
            adventure_modules.validate_restored(state)
            state['private']={};title=str(data['title'])[:120]
        elif body['type']=='start_adventure':
            premise=adventure.validate_start(state,body,me)
            if type(body.get('structured',False))!=bool:raise ValueError('Modo de aventura inválido')
            if body.get('moduleId') and body.get('module') is not None:raise ValueError('Elige una sola fuente de aventura')
            if body.get('moduleId'):adventure_modules.install(state,adventure_modules.builtin(body['moduleId']))
            elif body.get('module') is not None:adventure_modules.install(state,body['module'])
            if state.get('adventureModule'):premise=state['adventureModule']['premise']
            actors=[c['id'] for c in adventure.ready_characters(state)]
            result=ai_reply(state,premise,[],check_actors=actors,starting=True)
            if result.get('checks') or result.get('investigation'):raise ValueError('La apertura no puede resolver ni solicitar acciones de los personajes')
            if result.get('proposals'):raise ValueError('La apertura requiere una situación dentro de la cobertura disponible')
            if body.get('structured') and not state.get('adventureModule') and result.get('adventureModule') is None:
                raise ValueError('El director no entregó la investigación estructurada solicitada; la campaña no se ha modificado')
            if result.get('adventureModule') is not None:
                if state.get('adventureModule'):raise ValueError('El director no puede sustituir una aventura aportada')
                adventure_modules.install(state,result['adventureModule'])
            adventure.apply_memory(state,result.get('memory'),starting=True)
            state['messages'].append({'kind':'director','speaker':'Director · Claude Haiku','text':result['narration'],
                                      'time':time.time(),'adventureStart':True})
        elif body['type']=='investigate':
            queue_investigation(state,body,me)
            if body.get('method') is not None:
                apply_action(state,{'type':'check','request':state['pending'][-1]['check']['id'],'method':body['method']},me)
        elif body['type']=='continue_adventure' or body['type']=='talk' and body.get('director',True):
            if body['type']=='continue_adventure':
                text=adventure.continuation_request(state,me);refs=[]
            else:
                if body.get('kind')=='private':raise ValueError('Las notas privadas no se envían a Claude')
                # Validate speaker, ownership and content before making a billable call.
                apply_action(state,body,me)
                text=body['text'];refs=search(text)
            actors=[c['id'] for c in state['characters'] if me['host'] or c['owner']==me['id']]
            result=ai_reply(state,text,refs,check_actors=actors)
            if result.get('adventureModule') is not None:raise ValueError('La conversación no puede sustituir la aventura en curso')
            if body['type']=='continue_adventure' and (result.get('checks') or result.get('investigation')):
                raise ValueError('La continuación debe narrar el resultado confirmado, sin solicitar otra prueba')
            if result.get('investigation'):
                if result.get('checks'):raise ValueError('Una investigación utiliza su propia prueba, sin pruebas genéricas adicionales')
                if body.get('kind')=='ooc':raise ValueError('Una intervención fuera de personaje no solicita investigaciones')
                queue_investigation(state,result['investigation'],me)
            if (state.get('adventure') and body.get('kind','action')!='ooc' and not result.get('checks') and not result.get('investigation')
                and not any(p.get('check') for p in state['pending'])):
                adventure.apply_memory(state,result.get('memory'))
            state['messages'].append({'kind':'director','speaker':'Director · Claude Haiku','text':result['narration'],'refs':[{'book':r['book'],'page':r['page']} for r in refs],'time':time.time(),'ooc':body.get('kind')=='ooc'})
            for proposal in result.get('proposals',[])[:5]:
                state['pending'].append({'reason':str(proposal['reason'])[:1000],'source':'Propuesta de Claude Haiku; pendiente de validación humana'})
            for proposal in result.get('checks',[])[:3]:
                try:
                    if proposal['character'] not in actors:raise ValueError('Personaje fuera de los permisos de esta intervención')
                    if any(p.get('check') and all(p['check'].get(k)==proposal[k] for k in ('character','kind','key','dc')) for p in state['pending']):continue
                    apply_action(state,{'type':'request_check','character':proposal['character'],'checkKind':proposal['kind'],'key':proposal['key'],'dc':proposal['dc'],'reason':proposal['reason']},{**me,'host':True})
                    state['pending'][-1]['source']='Solicitud de Claude Haiku; CD propuesta por el director para esta situación'
                except (ValueError,KeyError,TypeError):
                    state['pending'].append({'reason':'Revisar prueba propuesta: '+str(proposal.get('reason','Prueba no válida'))[:500],'source':'El motor no pudo validar la solicitud de Claude; resolución asistida'})
        else:apply_action(state,body,me)
        # Firestore CAS + marker are atomic. A conflict never reruns RNG or the provider.
        duplicate=store.commit(cid,aid,me['id'],signature,row['version'],state,title)
        return {'duplicate':True} if duplicate else {'ok':True}


class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def reply(self,data,status=200):
        raw=json.dumps(data,ensure_ascii=False).encode();self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    def auth(self):return identity(self.headers.get('Authorization','').removeprefix('Bearer '))
    def do_GET(self):
        try:
            url=urlparse(self.path);query=parse_qs(url.query)
            if url.path=='/healthz':
                try:repository().health();self.reply({'status':'ok'})
                except Exception:self.reply({'status':'unavailable'},503)
                return
            if url.path=='/api/status':
                self.reply({'aiConfigured':bool(os.environ.get('ANTHROPIC_API_KEY')),'provider':'Anthropic','model':model_name(),'release':os.environ.get('RENDER_GIT_COMMIT','local'),'directorContract':'generated-links-v4','books':repository().counts(),'storage':'Firebase · Cloud Firestore','hosting':'Render' if os.environ.get('RENDER') else 'local con Firebase remoto'});return
            if url.path=='/api/systems':
                self.reply({'systems':rulesets.catalog()});return
            if url.path=='/api/book-info':
                self.auth()
                try:self.reply(reader_assets().describe(query.get('book',[''])[0]))
                except FileNotFoundError:self.reply({'error':'El manual todavía no está preparado para lectura por páginas'},404)
                return
            if url.path.startswith('/book-pages/'):
                self.auth()  # Authorize before ALL cache hits and conditional responses.
                import re
                match=re.fullmatch(r'/book-pages/(trey|reglas|bestiario)/([a-f0-9]{32})/([1-9][0-9]{0,3})\.(jpg|webp)',url.path)
                if not match:raise ValueError('Página inválida')
                try:raw,etag,mime=reader_assets().image(match[1],match[2],int(match[3]),match[4])
                except FileNotFoundError:self.reply({'error':'Página no disponible; vuelve a abrir el manual'},404);return
                unchanged=self.headers.get('If-None-Match')==etag
                self.send_response(304 if unchanged else 200)
                for name,value in [('Content-Type',mime),('Cache-Control','private, max-age=31536000, immutable'),('Vary','Authorization'),('ETag',etag),('X-Content-Type-Options','nosniff')]:self.send_header(name,value)
                if not unchanged:self.send_header('Content-Length',str(len(raw)))
                self.end_headers()
                if not unchanged:self.wfile.write(raw)
                return
            if url.path=='/api/state':
                me=self.auth();row=repository().metadata(me['campaign'])
                if query.get('version',[''])[0]==str(row['version']):self.reply({'unchanged':True});return
                row,state=load(me['campaign']);self.reply(view(row,state,me));return
            if url.path=='/api/search':
                self.auth();self.reply(search(query.get('q',[''])[0],query.get('book',[None])[0]));return
            if url.path.startswith('/books/'):
                identity(query.get('token',[''])[0]);book=url.path.removeprefix('/books/')
                try:stream,size=open_book(book)
                except FileNotFoundError:self.reply({'error':'Manual no instalado en Firebase Storage'},404);return
                self.send_response(200);self.send_header('Content-Type','application/pdf');self.send_header('Cache-Control','private, no-store');self.send_header('Content-Length',str(size));self.end_headers()
                with stream:
                    while chunk:=stream.read(65536):self.wfile.write(chunk)
                return
            path=ROOT/'static'/('index.html' if url.path=='/' else url.path.lstrip('/'))
            if not path.resolve().is_relative_to((ROOT/'static').resolve()) or not path.is_file():self.reply({'error':'No encontrado'},404);return
            types={'.html':'text/html; charset=utf-8','.css':'text/css','.js':'text/javascript; charset=utf-8'}
            raw=path.read_bytes();self.send_response(200);self.send_header('Content-Type',types.get(path.suffix,'application/octet-stream'));self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
        except PermissionError as exc:self.reply({'error':str(exc)},401)
        except (ValueError,OSError) as exc:self.reply({'error':str(exc)},400)
        except Exception:self.reply({'error':'Firebase no está disponible; no se ha utilizado almacenamiento local'},503)

    def do_POST(self):
        try:
            origin=self.headers.get('Origin')
            if origin and urlparse(origin).netloc!=self.headers.get('Host'):raise PermissionError('Origen no permitido')
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=8_000_000:raise ValueError('Tamaño de petición inválido')
            body=json.loads(self.rfile.read(size));path=urlparse(self.path).path
            if path=='/api/create':
                token=repository().create(str(body.get('title','Nueva crónica')),rulesets.new_campaign(body),str(body.get('player','Anfitrión')))
                self.reply({'token':token});return
            if path=='/api/join':
                self.reply({'token':repository().join(str(body['invite']),str(body['name']))});return
            me=self.auth()
            if path in {'/api/action','/api/import'}:
                if path=='/api/import':body={**body,'type':'import'}
                self.reply(execute_action(body,me));return
            if path=='/api/rules':
                _,state=load(me['campaign']);refs=search(body['q']);result=ai_reply(state,body['q'],refs,True)
                self.reply({'answer':result['narration'],'refs':[{'book':r['book'],'page':r['page']} for r in refs]});return
            if path=='/api/export':
                if not me['host']:raise PermissionError('Solo el anfitrión exporta la campaña completa')
                row,state=load(me['campaign']);self.reply({'format':'cronicas-1','title':row['title'],'state':state});return
            raise ValueError('Operación desconocida')
        except PermissionError as exc:self.reply({'error':str(exc)},403)
        except Conflict as exc:self.reply({'error':str(exc)},409)
        except (ValueError,KeyError,TypeError,IndexError) as exc:self.reply({'error':str(exc)},400)
        except Exception:self.reply({'error':'Firebase no está disponible. Conserva el identificador y reintenta para comprobar si la acción se confirmó'},503)


if __name__=='__main__':
    initialize();host=os.environ.get('HOST','127.0.0.1');port=int(os.environ.get('PORT','8787'))
    print(f'Mesa disponible en http://{host}:{port}',flush=True)
    ThreadingHTTPServer((host,port),Handler).serve_forever()
