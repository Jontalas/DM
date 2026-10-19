import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
from scripts.export_sqlite_campaigns import export
from scripts.firebase_books import upload
from firebase_store import BOOKS


class MigrationTests(unittest.TestCase):
    def test_legacy_database_export_is_read_only(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=root/'old.sqlite';destination=root/'exports'
            db=sqlite3.connect(source)
            try:
                db.execute('CREATE TABLE campaigns(id TEXT,title TEXT,state TEXT)')
                db.execute('INSERT INTO campaigns VALUES(?,?,?)',('campaign-1','Prueba',json.dumps({'notes':'Datos confirmados'})));db.commit()
            finally:db.close()
            before=source.read_bytes();export(source,destination)
            self.assertEqual(source.read_bytes(),before)
            data=json.loads((destination/'campaign-1.campaign.json').read_text(encoding='utf-8'))
            self.assertEqual(data['format'],'cronicas-1');self.assertEqual(data['state']['notes'],'Datos confirmados')
    def test_manual_upload_validates_inputs_before_remote_writes(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/BOOKS['trey']).write_bytes(b'%PDF-1.4\nFixture')
            (root/'trey.json').write_text(json.dumps([{'page':1,'text':'Fixture propia'}]),encoding='utf-8')
            store=Mock();upload(store,root,root,['trey'])
            store.upload_book.assert_called_once();store.index_book.assert_called_once_with('trey',[{'page':1,'text':'Fixture propia'}])
            store.reset_mock();(root/'trey.json').write_text('[]',encoding='utf-8')
            with self.assertRaises(ValueError):upload(store,root,root,['trey'])
            store.upload_book.assert_not_called();store.index_book.assert_not_called()


if __name__=='__main__':unittest.main()
