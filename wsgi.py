"""Entrada WSGI: reutiliza las rutas de la mesa y transmite archivos por bloques."""
from http import HTTPStatus
from io import BytesIO
import json
import mimetypes
from urllib.parse import parse_qs
from wsgiref.headers import Headers
from wsgiref.util import FileWrapper
import server


class ApiRequest(server.Handler):
    """Adapta exclusivamente las rutas JSON sin abrir otro servidor HTTP."""
    def __init__(self, environ):
        self.path = environ.get('PATH_INFO', '/')
        if environ.get('QUERY_STRING'): self.path += '?' + environ['QUERY_STRING']
        self.headers = Headers([(k[5:].replace('_','-'),v) for k,v in environ.items() if k.startswith('HTTP_')])
        for name in ('CONTENT_TYPE','CONTENT_LENGTH'):
            if environ.get(name): self.headers.add_header(name.replace('_','-'),environ[name])
        self.rfile = environ['wsgi.input']
        self.wfile = BytesIO()
        self.status = 200
        self.response_headers = []

    def send_response(self, code, message=None): self.status = code
    def send_header(self, name, value): self.response_headers.append((name,str(value)))
    def end_headers(self): pass


def error(start_response, code, message):
    raw = json.dumps({'error':message},ensure_ascii=False).encode()
    start_response(f'{code} {HTTPStatus(code).phrase}', [('Content-Type','application/json; charset=utf-8'),('Content-Length',str(len(raw))),('Cache-Control','no-store')])
    return [raw]


def file_response(environ, start_response, path, private=False):
    try:
        stream = path.open('rb')
    except FileNotFoundError:
        return error(start_response,404,'Archivo no instalado en este servidor')
    size = path.stat().st_size
    content_type = mimetypes.guess_type(str(path))[0] or 'application/octet-stream'
    if path.suffix in {'.js','.css','.html'}: content_type += '; charset=utf-8'
    start_response('200 OK',[('Content-Type',content_type),('Content-Length',str(size)),('Cache-Control','private, no-store' if private else 'no-cache')])
    if environ['REQUEST_METHOD']=='HEAD': stream.close(); return []
    wrapper = environ.get('wsgi.file_wrapper',FileWrapper)
    return wrapper(stream,65536)


def application(environ, start_response):
    method = environ['REQUEST_METHOD']
    path = environ.get('PATH_INFO','/')
    if method not in {'GET','HEAD','POST'}:
        return error(start_response,405,'Método no permitido')
    if path.startswith('/api/') or path=='/healthz' or path.startswith('/book-pages/'):
        request = ApiRequest(environ)
        if method=='POST': request.do_POST()
        else: request.do_GET()
        start_response(f'{request.status} {HTTPStatus(request.status).phrase}',request.response_headers)
        return [] if method=='HEAD' else [request.wfile.getvalue()]
    if method=='POST': return error(start_response,404,'Ruta desconocida')
    if path.startswith('/books/'):
        book = path.removeprefix('/books/')
        try:
            server.identity(parse_qs(environ.get('QUERY_STRING','')).get('token',[''])[0])
        except PermissionError as exc:
            return error(start_response,401,str(exc))
        if book not in server.BOOKS: return error(start_response,404,'Libro desconocido')
        try: stream,size=server.open_book(book)
        except FileNotFoundError:return error(start_response,404,'Manual no instalado en Firebase Storage')
        except Exception:return error(start_response,503,'Firebase Storage no está disponible; comprueba bucket y permisos')
        start_response('200 OK',[('Content-Type','application/pdf'),('Content-Length',str(size)),('Cache-Control','private, no-store')])
        if method=='HEAD':stream.close();return []
        def blocks():
            try:
                while chunk:=stream.read(65536):yield chunk
            finally:stream.close()
        return blocks()
    static_root = (server.ROOT/'static').resolve()
    target = (static_root/('index.html' if path=='/' else path.lstrip('/'))).resolve()
    if not target.is_relative_to(static_root) or not target.is_file():
        return error(start_response,404,'No encontrado')
    return file_response(environ,start_response,target)
