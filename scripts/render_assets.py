"""Empaqueta o instala manuales e índices sin incluirlos en el repositorio."""
import argparse
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import server


def members():
    return {**{f'books/{name}':server.BOOKS_DIR/name for name in server.BOOKS.values()},
            **{f'indexes/{key}.json':server.INDEX_DIR/f'{key}.json' for key in server.BOOKS}}


def pack(output):
    files=members()
    missing=[str(p) for p in files.values() if not p.is_file()]
    if missing: raise ValueError('Faltan archivos. Extrae los manuales antes de empaquetar:\n'+'\n'.join(missing))
    output=Path(output)
    output.parent.mkdir(parents=True,exist_ok=True)
    # Never silently replace a previous bundle.
    with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_DEFLATED) as archive:
        for name,path in files.items(): archive.write(path,name)
    print(f'Paquete privado creado: {output}. Contiene manuales e índices, no partidas ni credenciales.')


def install(source):
    targets=members()
    with zipfile.ZipFile(source) as archive:
        names=archive.namelist()
        if len(names)!=len(set(names)) or set(names)!=set(targets):
            raise ValueError('El paquete debe contener exactamente los tres PDF y sus tres índices, sin rutas adicionales')
        if sum(i.file_size for i in archive.infolist())>1_000_000_000:
            raise ValueError('El paquete descomprimido supera 1 GB')
        # Validate everything before replacing any installed file. No extractall/path traversal.
        for name in names:
            with archive.open(name) as src:
                if name.endswith('.pdf'):
                    if src.read(5)!=b'%PDF-': raise ValueError(f'PDF inválido: {name}')
                else:
                    pages=json.load(src)
                    if not isinstance(pages,list) or not pages or any(not isinstance(p,dict) or type(p.get('page'))!=int or p['page']<1 or not isinstance(p.get('text'),str) for p in pages):
                        raise ValueError(f'Índice inválido: {name}')
        for name,target in targets.items():
            target.parent.mkdir(parents=True,exist_ok=True)
            temporary=None
            try:
                with tempfile.NamedTemporaryFile(dir=target.parent,delete=False) as dst, archive.open(name) as src:
                    temporary=Path(dst.name);shutil.copyfileobj(src,dst)
                os.replace(temporary,target)
            finally:
                if temporary and temporary.exists(): temporary.unlink()
    print('Manuales e índices instalados. Reinicia el servicio para indexarlos. No se ha modificado ninguna campaña.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation',choices=['pack','install'])
    parser.add_argument('archive',help='Ruta del ZIP privado')
    args=parser.parse_args()
    try:
        if args.operation=='pack':pack(args.archive)
        else:install(args.archive)
    except (ValueError,OSError,zipfile.BadZipFile) as exc:
        parser.exit(1,str(exc)+'\n')
