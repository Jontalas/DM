"""Utilidad de migración: LEE la antigua SQLite y exporta JSON para importar en Firebase."""
import argparse
import json
from pathlib import Path
import sqlite3


def export(source,destination):
    source=Path(source).resolve();destination=Path(destination)
    if not source.is_file():raise ValueError('La base antigua no existe')
    destination.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(source.as_uri()+'?mode=ro',uri=True)
    try:
        db.execute('BEGIN')
        for cid,title,state in db.execute('SELECT id,title,state FROM campaigns'):
            # Exclusive mode preserves previous backups; no sessions/tokens are exported.
            safe=''.join(c for c in cid if c.isalnum() or c in '-_')
            with (destination/(safe+'.campaign.json')).open('x',encoding='utf-8') as target:
                json.dump({'format':'cronicas-1','title':title,'state':json.loads(state)},target,ensure_ascii=False)
    finally:db.close()
    print('Campañas exportadas. Impórtalas desde el diario de la nueva aplicación; la base antigua no se ha modificado.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('source');parser.add_argument('destination')
    args=parser.parse_args();export(args.source,args.destination)
