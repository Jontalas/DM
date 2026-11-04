"""Copy a pinned, integrity-checked PDF.js distribution without install scripts.

Download separately with npm pack pdfjs-dist@6.5.438 --ignore-scripts. Original
bytes/licenses are preserved. No viewer, scripting sandbox, maps or QuickJS.
"""
import base64
import hashlib
import json
from pathlib import Path,PurePosixPath
import tarfile

ROOT=Path(__file__).resolve().parents[1]
VERSION='6.5.438'
INTEGRITY='vg8Pw1x+AFKy4AMDvhuWl5cOYV8d698UoEANoFFhc79hqXDnZQqnOXoxw3HG907WHOg1JYOvLhP756boddFxpA=='
TARGET=ROOT/'static'/'vendor'/('pdfjs-'+VERSION)


def main():
    archive=ROOT/'.deps'/('pdfjs-dist-'+VERSION+'.tgz')
    actual=base64.b64encode(hashlib.sha512(archive.read_bytes()).digest()).decode()
    if actual!=INTEGRITY:raise ValueError('PDF.js archive integrity mismatch')
    TARGET.mkdir(parents=True,exist_ok=True);files={}
    with tarfile.open(archive) as bundle:
        for member in bundle:
            if not member.isfile():continue
            relative=member.name.removeprefix('package/')
            selected=relative in ('LICENSE','build/pdf.min.mjs','build/pdf.worker.min.mjs') or relative.startswith(('cmaps/','standard_fonts/','iccs/','wasm/'))
            if not selected or 'quickjs' in relative.lower():continue
            parts=PurePosixPath(relative).parts
            if '..' in parts or PurePosixPath(relative).is_absolute():raise ValueError('Unsafe archive path')
            destination=TARGET.joinpath(*parts)
            if not destination.resolve().is_relative_to(TARGET.resolve()):raise ValueError('Unsafe target')
            if relative in files:raise ValueError('Duplicate archive member')
            data=bundle.extractfile(member).read()
            if destination.exists() and destination.read_bytes()!=data:raise ValueError('An immutable vendor asset has changed')
            destination.parent.mkdir(parents=True,exist_ok=True)
            destination.write_bytes(data)
            files[relative]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
    manifest={'package':'pdfjs-dist','version':VERSION,'license':'Apache-2.0 (plus bundled resource licenses)',
        'source':'https://registry.npmjs.org/pdfjs-dist/-/pdfjs-dist-'+VERSION+'.tgz',
        'release':'https://github.com/mozilla/pdf.js/releases/tag/v'+VERSION,
        'integrity':'sha512-'+INTEGRITY,'changes':'Selected unmodified distribution assets; no viewer or scripting sandbox.',
        'files':files}
    (TARGET/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'PDF.js {VERSION}: {len(files)} assets, {sum(v["bytes"] for v in files.values())} bytes; original licenses retained.')


if __name__=='__main__':main()
