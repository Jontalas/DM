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

ROOT=Path(__file__).resolve().parent
# Local paths are only for extracting/importing PDF assets, never for databases.
DATA_DIR=Path(os.environ.get('DATA_DIR',str(ROOT/'data')))
INDEX_DIR=Path(os.environ.get('INDEX_DIR',str(DATA_DIR)))
BOOKS_DIR=Path(os.environ.get('BOOKS_DIR',str(Path.home()/'Desktop')))
STORE=None
LOCK=threading.RLock()


def initialize():
    global STORE
    if STORE is None: STORE=FirestoreStore.from_environment()
    STORE.health()
    model_name()


def repository():
    if STORE is None:raise Unavailable('Firebase sin inicializar. Configura proyecto y credenciales en el servidor')
    return STORE


def search(query,book=None):return repository().search(query,book)
def identity(token):return repository().identity(token)
def load(cid):return repository().load(cid)


def view(row,state,me):
    state=json.loads(json.dumps(state))
    state['messages']=[m for m in state['messages'] if m.get('visibility','public')=='public' or me['host'] or m.get('owner')==me['id']]
    if not me['host']:state.pop('secrets',None)
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
            for key in initial_state({}):
                if key not in state:raise ValueError('Falta '+key)
            for character in state['characters']:character['owner']=me['id']
            state['private']={};title=str(data['title'])[:120]
        elif body['type']=='talk' and body.get('director',True):
            if body.get('kind')=='private':raise ValueError('Las notas privadas no se envían a Claude')
            # Validate speaker, ownership and content before making a billable call.
            apply_action(state,body,me)
            refs=search(body['text']);result=ai_reply(state,body['text'],refs)
            state['messages'].append({'kind':'director','speaker':'Director · Claude Haiku','text':result['narration'],'refs':[{'book':r['book'],'page':r['page']} for r in refs],'time':time.time()})
            for proposal in result.get('proposals',[])[:5]:
                state['pending'].append({'reason':str(proposal['reason'])[:1000],'source':'Propuesta de Claude Haiku; pendiente de validación humana'})
        else:apply_action(state,body,me)
        # Firestore CAS + marker are atomic. No RNG or provider call in the retry callback.
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
                self.reply({'aiConfigured':bool(os.environ.get('ANTHROPIC_API_KEY')),'provider':'Anthropic','model':model_name(),'books':repository().counts(),'storage':'Firebase · Cloud Firestore','hosting':'Render' if os.environ.get('RENDER') else 'local con Firebase remoto'});return
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
                token=repository().create(str(body.get('title','Nueva crónica')),initial_state(body),str(body.get('player','Anfitrión')))
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
