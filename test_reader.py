from concurrent.futures import ThreadPoolExecutor
import json
import threading
import unittest
from unittest.mock import Mock,patch

from book_pages import ReaderAssets
from scripts.prepare_book_pages import publish

REV='a'*32


class ReaderCacheTests(unittest.TestCase):
    def manifest(self,**extra):return json.dumps({'version':1,'book':'reglas','revision':REV,'pages':3,'format':'jpeg',**extra}).encode()
    def reader(self):
        download=Mock(side_effect=lambda name:self.manifest() if name.endswith('manifest.json') else b'\xff\xd8page-'+name.encode())
        return ReaderAssets(download),download

    def test_repeated_page_downloads_once_and_never_reads_original_pdf(self):
        reader,download=self.reader();first=reader.image('reglas',REV,1)
        self.assertEqual(first,reader.image('reglas',REV,1));self.assertEqual(first[2],'image/jpeg')
        self.assertEqual(download.call_count,2)
        self.assertTrue(all('original.pdf' not in c.args[0] for c in download.call_args_list))

    def test_concurrent_requests_share_one_download(self):
        reader,download=self.reader();reader.describe('reglas')
        started=threading.Event();release=threading.Event()
        def load(_):started.set();self.assertTrue(release.wait(5));return b'\xff\xd8page'
        download.side_effect=load
        with ThreadPoolExecutor(max_workers=4) as pool:
            first=pool.submit(reader.image,'reglas',REV,1)
            self.assertTrue(started.wait(5))
            others=[pool.submit(reader.image,'reglas',REV,1) for _ in range(3)]
            release.set();results=[first.result(),*[f.result() for f in others]]
        self.assertTrue(all(r==results[0] for r in results));self.assertEqual(download.call_count,2)

    def test_cache_is_bounded_and_eviction_reloads_only_needed_resource(self):
        download=Mock(return_value=b'1234');reader=ReaderAssets(download,max_bytes=8)
        for key in ('a','b','c'):reader._get(key,60)
        self.assertLessEqual(reader.bytes,8)
        reader._get('c',60);self.assertEqual(download.call_count,3)
        reader._get('a',60);self.assertEqual(download.call_count,4)

    def test_expired_manifest_checks_new_revision_without_serving_old_page(self):
        reader,download=self.reader()
        with patch('book_pages.time.monotonic',return_value=10):reader.describe('reglas')
        download.side_effect=lambda _:self.manifest(revision='b'*32)
        with patch('book_pages.time.monotonic',return_value=71):
            with self.assertRaises(FileNotFoundError):reader.image('reglas',REV,1)

    def test_invalid_routes_and_formats_cannot_escape_manual_namespace(self):
        reader,download=self.reader()
        for book,revision,page in [('../reglas',REV,1),('reglas','../x',1),('reglas',REV,0),('reglas',REV,4),('reglas',REV,True)]:
            with self.subTest(book=book,page=page),self.assertRaises(ValueError):reader.image(book,revision,page)
        with self.assertRaises(ValueError):reader.image('reglas',REV,1,'webp')
        self.assertTrue(all(c.args[0].endswith('manifest.json') for c in download.call_args_list))

    def test_failed_download_is_not_cached_and_can_be_retried(self):
        download=Mock(side_effect=[OSError('Transient'),b'OK']);reader=ReaderAssets(download)
        with self.assertRaises(OSError):reader._get('page',60)
        self.assertEqual(reader._get('page',60),b'OK')

    def test_webp_pages_have_correct_type_and_validation(self):
        download=Mock(side_effect=[self.manifest(format='webp'),b'RIFF0000WEBPfixture'])
        raw,etag,mime=ReaderAssets(download).image('reglas',REV,1,'webp')
        self.assertEqual(mime,'image/webp');self.assertTrue(etag.startswith('"'))
        self.assertEqual(download.call_args.args[0],f'manuals/reglas/reader/{REV}/1.webp')


class ReaderPublisherTests(unittest.TestCase):
    def manifest(self):return {'book':'reglas','revision':REV,'pages':2}

    def test_active_manifest_is_not_published_after_partial_upload(self):
        from google.api_core.exceptions import NotFound
        bucket=Mock();active=Mock();image=Mock()
        active.download_as_bytes.side_effect=NotFound('Missing')
        image.upload_from_filename.side_effect=OSError('Upload failed')
        bucket.blob.side_effect=lambda path:active if path.endswith('manifest.json') else image
        from pathlib import Path
        with self.assertRaises(OSError):publish(bucket,Path('fixture'),self.manifest())
        active.upload_from_string.assert_not_called()

    def test_same_published_revision_skips_all_image_uploads(self):
        bucket=Mock();bucket.blob.return_value.download_as_bytes.return_value=json.dumps(self.manifest()).encode()
        from pathlib import Path
        publish(bucket,Path('fixture'),self.manifest())
        bucket.blob.assert_called_once_with('manuals/reglas/reader/manifest.json')
        bucket.blob.return_value.upload_from_string.assert_not_called()


if __name__=='__main__':unittest.main()
