"""Identifica instantáneas antiguas sin referencia; --apply autoriza borrarlas."""
import argparse
from datetime import datetime,timedelta,timezone
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from firebase_store import FirestoreStore


def cleanup(store,days=7,apply=False):
    if days<1:raise ValueError('Conserva al menos un día de margen')
    cutoff=datetime.now(timezone.utc)-timedelta(days=days);count=0
    for snapshot in store.client.collection_group('snapshots').stream():
        # A project may contain unrelated collections; operate only on this app's prefix.
        if not snapshot.reference.path.startswith(store.prefix+'_campaigns/'):continue
        data=snapshot.to_dict()
        if not data.get('createdAt') or data['createdAt']>=cutoff:continue
        parent=snapshot.reference.parent.parent;meta=parent.get().to_dict() or {}
        if snapshot.id.startswith(meta.get('snapshot','')+'-'):continue
        count+=1
        if apply:snapshot.reference.delete()
    print(f'{count} fragmentos '+('eliminados' if apply else 'candidatos; simulación, no se ha borrado nada'))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--days',type=int,default=7);parser.add_argument('--apply',action='store_true')
    args=parser.parse_args();cleanup(FirestoreStore.from_environment(),args.days,args.apply)
