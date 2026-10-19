import json
from pathlib import Path
from book_pages import ReaderAssets


def fixture_reader():
    folder=Path(__file__).parent/'test_fixtures'
    def download(path):
        parts=path.split('/');book=parts[1]
        revision={'reglas':'1','trey':'2','bestiario':'3'}[book]*32
        if path.endswith('manifest.json'):
            return json.dumps({'version':1,'book':book,'revision':revision,'pages':2,'format':'jpeg','width':180}).encode()
        if parts[-2]!=revision:raise FileNotFoundError('Fixture inexistente')
        return (folder/f'reader-{parts[-1]}').read_bytes()
    return ReaderAssets(download)
