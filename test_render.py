"""Despliegue: mismo recorrido HTTP bajo Waitress y almacenamiento separado."""
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
import zipfile
from contextlib import closing
from unittest.mock import patch
import server
import test_server
from wsgi import application
from scripts import render_assets, backup_db


class ProductionServerTests(test_server.IntegrationTests):
    @classmethod
    def setUpClass(cls):
        from waitress.server import create_server
        cls.tmp=tempfile.TemporaryDirectory()
        cls.oldDB,cls.oldIndex,cls.oldBooks=server.DB,server.INDEX_DIR,server.BOOKS_DIR
        server.DB=Path(cls.tmp.name)/'persistent'/'campaigns.sqlite'
        server.INDEX_DIR=Path(cls.tmp.name)/'indexes'
        server.BOOKS_DIR=Path(cls.tmp.name)/'books'
        server.initialize()
        with server.conn() as c:c.execute('INSERT INTO pages VALUES(?,?,?)',('reglas',194,'Texto de prueba: diagonales y movimiento.'))
        cls.socket_map={}
        cls.http=create_server(application,host='127.0.0.1',port=0,map=cls.socket_map,threads=4)
        cls.url='http://127.0.0.1:'+str(cls.http.effective_port)
        cls.thread=threading.Thread(target=cls.http.run,daemon=True);cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        from waitress import wasyncore
        cls.http.task_dispatcher.shutdown()
        wasyncore.close_all(cls.socket_map)
        cls.thread.join(timeout=3)
        server.DB,server.INDEX_DIR,server.BOOKS_DIR=cls.oldDB,cls.oldIndex,cls.oldBooks
        cls.tmp.cleanup()

    def test_static_health_and_head(self):
        self.assertEqual(self.request('/healthz'),{'status':'ok'})
        for path in ['/','/app.js','/style.css']:
            with urllib.request.urlopen(self.url+path) as response:
                self.assertEqual(response.status,200);self.assertGreater(len(response.read()),100)
        with urllib.request.urlopen(urllib.request.Request(self.url+'/',method='HEAD')) as response:
            self.assertEqual(response.read(),b'');self.assertGreater(int(response.headers['Content-Length']),100)

    def test_https_origin_through_proxy_and_host_filter(self):
        payload=json.dumps({'title':'Render','player':'Ana'}).encode()
        request=urllib.request.Request(self.url+'/api/create',data=payload,headers={'Content-Type':'application/json','Host':'dm.example.onrender.com','Origin':'https://dm.example.onrender.com'})
        with urllib.request.urlopen(request) as response:self.assertIn('token',json.load(response))
        request.add_header('Origin','https://otro.example')
        with self.assertRaises(urllib.error.HTTPError) as ctx:urllib.request.urlopen(request)
        self.assertEqual(ctx.exception.code,403);ctx.exception.close()

    def test_book_auth_missing_book_and_stream(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:urllib.request.urlopen(self.url+'/books/trey')
        self.assertEqual(ctx.exception.code,401);ctx.exception.close()
        with self.assertRaises(urllib.error.HTTPError) as ctx:urllib.request.urlopen(self.url+'/books/trey?token='+self.token)
        self.assertEqual(ctx.exception.code,404);ctx.exception.close()
        server.BOOKS_DIR.mkdir(exist_ok=True)
        fake=b'%PDF-1.4\nTest fixture\n'
        (server.BOOKS_DIR/server.BOOKS['trey']).write_bytes(fake)
        with urllib.request.urlopen(self.url+'/books/trey?token='+self.token) as response:
            self.assertEqual(response.read(),fake);self.assertIn('private',response.headers['Cache-Control'])

    def test_backup_includes_confirmed_campaign(self):
        destination=Path(self.tmp.name)/'backup.sqlite'
        backup_db.backup(destination)
        with closing(sqlite3.connect(destination)) as db:
            self.assertTrue(db.execute('SELECT 1 FROM campaigns WHERE id=?',(self.state()['id'],)).fetchone())


class AssetTests(unittest.TestCase):
    def test_bundle_roundtrip_and_reject_extra_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);books=root/'books';indexes=root/'indexes';books.mkdir();indexes.mkdir()
            for name in server.BOOKS.values():(books/name).write_bytes(b'%PDF-1.4\nFixture\n')
            for key in server.BOOKS:(indexes/f'{key}.json').write_text(json.dumps([{'page':1,'text':'Texto de prueba'}]),encoding='utf-8')
            bundle=root/'assets.zip'
            with patch.object(server,'BOOKS_DIR',books),patch.object(server,'INDEX_DIR',indexes):render_assets.pack(bundle)
            with patch.object(server,'BOOKS_DIR',root/'newbooks'),patch.object(server,'INDEX_DIR',root/'newindex'):
                render_assets.install(bundle)
                self.assertEqual((root/'newbooks'/server.BOOKS['trey']).read_bytes(),b'%PDF-1.4\nFixture\n')
                self.assertTrue((root/'newindex/trey.json').is_file())
                with zipfile.ZipFile(bundle,'a') as archive:archive.writestr('../escape','invalid')
                with self.assertRaises(ValueError):render_assets.install(bundle)
            self.assertFalse((root/'escape').exists())


if __name__=='__main__':unittest.main()
