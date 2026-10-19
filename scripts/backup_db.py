"""Copia SQLite consistente, incluidos los cambios confirmados en WAL."""
import argparse
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server


def backup(destination):
    destination=Path(destination).resolve()
    if destination==server.DB.resolve(): raise ValueError('El destino debe ser distinto de la base activa')
    if destination.exists(): raise ValueError('El destino ya existe; usa un nombre nuevo')
    if not server.DB.is_file(): raise ValueError('La base de datos todavía no existe')
    destination.parent.mkdir(parents=True,exist_ok=True)
    source=sqlite3.connect(server.DB.resolve().as_uri()+'?mode=ro',uri=True)
    target=sqlite3.connect(destination)
    try: source.backup(target)
    finally: source.close();target.close()
    print(f'Copia SQLite creada en {destination}')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination')
    args=parser.parse_args()
    try: backup(args.destination)
    except (ValueError,OSError,sqlite3.Error) as exc: parser.exit(1,str(exc)+'\n')
