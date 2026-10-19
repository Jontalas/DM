"""Sube los PDF a Firebase Storage y sus páginas/términos a Cloud Firestore."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from firebase_store import BOOKS,FirestoreStore


def upload(store,books_dir,index_dir,selected):
    inputs={}
    # Validate all local files before performing any remote write.
    for book in selected:
        pdf=Path(books_dir)/BOOKS[book]
        with pdf.open('rb') as source:
            if source.read(5)!=b'%PDF-':raise ValueError(f'PDF inválido: {pdf.name}')
        pages=json.loads((Path(index_dir)/f'{book}.json').read_text(encoding='utf-8'))
        if not isinstance(pages,list) or not pages or any(not isinstance(p,dict) or type(p.get('page'))!=int or not isinstance(p.get('text'),str) for p in pages):
            raise ValueError(f'Índice inválido: {book}')
        inputs[book]=(pdf,pages)
    for book,(pdf,pages) in inputs.items():
        store.upload_book(book,pdf)
        store.index_book(book,pages)
        print(f'{book}: PDF privado subido; {len(pages)} páginas indexadas en Firestore')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--books-dir',default=str(Path.home()/'Desktop'))
    parser.add_argument('--index-dir',default='data')
    parser.add_argument('--book',choices=['all',*BOOKS],default='all')
    args=parser.parse_args()
    upload(FirestoreStore.from_environment(),args.books_dir,args.index_dir,BOOKS if args.book=='all' else [args.book])
