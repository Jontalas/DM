"""Prepara páginas ligeras una sola vez y las publica privadamente en Storage."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from firebase_store import BOOKS,FirestoreStore

WIDTH=1400
QUALITY=80


def prepare(book,source,output):
    try:import pymupdf
    except ImportError:
        sys.path.insert(0,str(ROOT/'.deps'))
        import pymupdf
    try:from PIL import Image
    except ImportError:
        sys.path.insert(0,str(ROOT/'.deps'))
        from PIL import Image
    source=Path(source)
    with source.open('rb') as stream:source_hash=hashlib.file_digest(stream,'sha256').hexdigest()
    revision=hashlib.sha256(f'{source_hash}:webp:{WIDTH}:{QUALITY}:{pymupdf.VersionBind}:reader-2'.encode()).hexdigest()[:32]
    folder=Path(output)/book/revision;folder.mkdir(parents=True,exist_ok=True)
    total=0;sizes=[]
    with pymupdf.open(source) as document:
        for i,page in enumerate(document):
            target=folder/f'{i+1}.webp'
            if not target.exists():
                scale=WIDTH/page.rect.width
                image=page.get_pixmap(matrix=pymupdf.Matrix(scale,scale),alpha=False,colorspace=pymupdf.csRGB)
                rendered=Image.frombytes('RGB',(image.width,image.height),image.samples)
                temp=target.with_suffix('.tmp');rendered.save(temp,format='WEBP',quality=QUALITY,method=4);temp.replace(target)
            size=target.stat().st_size;total+=size;sizes.append(size)
            if (i+1)%100==0:print(f'{book}: preparadas {i+1}/{len(document)}',flush=True)
        manifest={'version':1,'book':book,'revision':revision,'pages':len(document),'format':'webp',
                  'width':WIDTH,'quality':QUALITY,'totalBytes':total,'maxPageBytes':max(sizes)}
    (folder/'manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
    print(f'{book}: {manifest["pages"]} páginas; {total} bytes; media {total//manifest["pages"]}; máxima {max(sizes)}',flush=True)
    return folder,manifest


def publish(bucket,folder,manifest):
    from google.api_core.exceptions import NotFound,PreconditionFailed
    book=manifest['book'];revision=manifest['revision']
    active=bucket.blob(f'manuals/{book}/reader/manifest.json')
    try:current=json.loads(active.download_as_bytes(timeout=30))
    except NotFound:current=None
    if current and current.get('revision')==revision:
        print(f'{book}: versión ya publicada; sin nuevas cargas',flush=True);return
    def upload(page):
        blob=bucket.blob(f'manuals/{book}/reader/{revision}/{page}.webp')
        try:blob.upload_from_filename(str(folder/f'{page}.webp'),content_type='image/webp',if_generation_match=0,timeout=60)
        except PreconditionFailed:pass  # Resume immutable pages already uploaded.
    with ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(upload,range(1,manifest['pages']+1)))
    # Publish only after every page exists; never switch to a partial reader.
    active.upload_from_string(json.dumps(manifest),content_type='application/json',timeout=30)
    print(f'{book}: lector privado publicado',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--books-dir',default=str(Path.home()/'Desktop'))
    parser.add_argument('--output-dir',default=str(ROOT/'.deps/book-pages'))
    parser.add_argument('--book',choices=['all',*BOOKS],default='all')
    parser.add_argument('--upload',action='store_true')
    args=parser.parse_args()
    selected=list(BOOKS) if args.book=='all' else [args.book]
    for book in selected:
        if not (Path(args.books_dir)/BOOKS[book]).is_file():raise FileNotFoundError(BOOKS[book])
    bucket=None
    if args.upload:
        import os
        from google.cloud import storage
        name=os.environ.get('FIREBASE_STORAGE_BUCKET')
        if not name:raise ValueError('Configura FIREBASE_STORAGE_BUCKET')
        store=FirestoreStore.from_environment()
        bucket=storage.Client(project=store.client.project,credentials=store.credentials).bucket(name)
    for book in selected:
        folder,manifest=prepare(book,Path(args.books_dir)/BOOKS[book],args.output_dir)
        if bucket:publish(bucket,folder,manifest)
