"""Lectura privada por páginas, con caché acotada y descargas concurrentes únicas."""
from collections import OrderedDict
from concurrent.futures import Future
import hashlib
import json
import re
import threading
import time

BOOK_KEYS={'trey','reglas','bestiario'}


class ReaderAssets:
    def __init__(self,download,max_bytes=32*1024*1024):
        self.download=download;self.max_bytes=max_bytes
        self.cache=OrderedDict();self.inflight={};self.bytes=0;self.lock=threading.Lock()

    def _get(self,key,ttl):
        with self.lock:
            previous=self.cache.pop(key,None)
            if previous:
                if previous[1]>time.monotonic():
                    self.cache[key]=previous;return previous[0]
                self.bytes-=len(previous[0])
            pending=self.inflight.get(key);owner=pending is None
            if owner:pending=Future();self.inflight[key]=pending
        if not owner:return pending.result(timeout=45)
        try:
            raw=self.download(key)
            if not isinstance(raw,bytes):raise ValueError('Recurso de lectura inválido')
            with self.lock:
                if len(raw)<=self.max_bytes:
                    while self.cache and self.bytes+len(raw)>self.max_bytes:
                        _,entry=self.cache.popitem(last=False);self.bytes-=len(entry[0])
                    self.cache[key]=(raw,time.monotonic()+ttl);self.bytes+=len(raw)
            pending.set_result(raw)
            return raw
        except Exception as exc:
            pending.set_exception(exc);raise
        finally:
            with self.lock:self.inflight.pop(key,None)

    def describe(self,book):
        if book not in BOOK_KEYS:raise ValueError('Libro desconocido')
        raw=self._get(f'manuals/{book}/reader/manifest.json',60)
        data=json.loads(raw)
        if (not isinstance(data,dict) or data.get('book')!=book or data.get('version')!=1
            or data.get('format') not in ('jpeg','webp') or type(data.get('pages'))!=int or not 1<=data['pages']<=2000
            or not re.fullmatch(r'[a-f0-9]{32}',str(data.get('revision','')))):
            raise ValueError('Versión de lectura inválida')
        return data

    def image(self,book,revision,page,extension=None):
        if not re.fullmatch(r'[a-f0-9]{32}',revision) or type(page)!=int:raise ValueError('Página inválida')
        info=self.describe(book)
        if info['revision']!=revision:raise FileNotFoundError('La versión del manual ha cambiado')
        if not 1<=page<=info['pages']:raise ValueError('Página fuera del manual')
        suffix,mime=('jpg','image/jpeg') if info['format']=='jpeg' else ('webp','image/webp')
        if extension is not None and extension!=suffix:raise ValueError('Formato de página inválido')
        raw=self._get(f'manuals/{book}/reader/{revision}/{page}.{suffix}',3600)
        valid=raw.startswith(b'\xff\xd8') if suffix=='jpg' else raw.startswith(b'RIFF') and raw[8:12]==b'WEBP'
        if not valid or len(raw)>8*1024*1024:raise ValueError('Página de lectura inválida')
        return raw,'"'+hashlib.sha256(raw).hexdigest()+'"',mime
