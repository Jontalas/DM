"""Private, resumable provider verification. Default mode only replays a capture.

Example: python scripts/verify_rule_authoring.py --request .deps/request.json
  --session .deps/authoring-session.json --live
No credentials, request headers or rulebook text are printed. Captures stay in
the ignored .deps directory. An uncertain previous call is never repeated.
"""
import argparse
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import time
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import rule_pack_authoring as authoring
from model_config import model_name
from rule_pack_runtime import RulePackError


def _path(value):
    result=Path(value).resolve()
    if not result.is_relative_to((ROOT/'.deps').resolve()):raise ValueError('La captura privada debe guardarse dentro de .deps')
    return result


def _save(path,record):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(authoring.canonical(record)+'\n',encoding='utf-8');temp.replace(path)


def verify(raw,path,live=False):
    path=_path(path)
    current_prompt=hashlib.sha256(authoring.PROMPT.encode()).hexdigest()
    if path.exists():
        record=json.loads(path.read_text(encoding='utf-8'))
        prepared=authoring.prepare_input(raw,record.get('sourceScheme',authoring.LEGACY_SOURCE_SCHEME))
        if record.get('requestSha256')!=prepared['sha256']:raise ValueError('La sesión pertenece a otra fuente o alcance; se conserva sin modificar')
        captured=record.get('responseBase64')
        if not captured:raise ValueError('La llamada anterior no tiene respuesta capturada; su resultado es incierto y no se repetirá automáticamente')
        response=base64.b64decode(captured,validate=True)
        if len(response)>authoring.MAX_RESPONSE+1:raise ValueError('La captura supera el límite de respuesta')
        mode='replay'
    else:
        prepared=authoring.prepare_input(raw)
        if not live:raise ValueError('No hay captura. Usa --live expresamente para una primera llamada; por defecto no se accede al proveedor')
        if not os.environ.get('ANTHROPIC_API_KEY'):raise ValueError('No hay clave local de Anthropic; no se ha creado sesión ni llamado al proveedor')
        record={'format':'cronicas-authoring-verification-1','requestSha256':prepared['sha256'],
            'request':prepared['request'],'sourceScheme':prepared['sourceScheme'],'model':model_name(),'promptSha256':current_prompt,'phase':'started'}
        # Reserve this attempt before network I/O. No retry after uncertain exit.
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('x',encoding='utf-8') as stream:stream.write(authoring.canonical(record)+'\n')
        mode='live';response=None
    actual_open=authoring.urllib.request.urlopen
    calls=0;payload_matches=False
    def transport(request,**options):
        nonlocal calls,response,payload_matches
        calls+=1
        if calls>1:raise AssertionError('La verificación no permite repetir el transporte')
        if mode=='live':
            record['payloadSha256']=hashlib.sha256(request.data).hexdigest()
            started=time.monotonic()
            with actual_open(request,**options) as opened:response=opened.read(authoring.MAX_RESPONSE+1)
            record['transportMs']=round((time.monotonic()-started)*1000)
            record['responseBase64']=base64.b64encode(response).decode();record['phase']='response'
            _save(path,record) # Persist before parsing/compiling the proposal.
        payload_matches=record.get('payloadSha256')==hashlib.sha256(request.data).hexdigest()
        return io.BytesIO(response)
    try:
        # The existing adapter still validates model output, examples and usage.
        # Replay never reads a real key or reaches the network.
        env={'ANTHROPIC_API_KEY':'replay-placeholder-never-sent'} if mode=='replay' else {}
        with patch.dict(os.environ,env),patch.object(authoring.urllib.request,'urlopen',side_effect=transport):
            report=authoring.propose(prepared)
        if 'transportMs' in record:report['usage']['latencyMs']=record['transportMs']
        record['phase']='validated';record['report']=report;record.pop('error',None)
        _save(path,record)
        return {'mode':mode,'status':report['status'],'examples':len(report['checks']),
            'sourceVerification':report['sourceVerification'],'usage':report.get('usage'),
            'requestedModel':record['model'],'samePrompt':record['promptSha256']==current_prompt,'samePayload':payload_matches}
    except Exception as error:
        record['phase']='failed';record['error']=type(error).__name__
        _save(path,record)
        raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request',required=True,type=Path)
    parser.add_argument('--session',required=True,type=Path)
    parser.add_argument('--live',action='store_true',help='Allow one first provider call; never repeats a recorded attempt')
    options=parser.parse_args()
    result=verify(json.loads(options.request.read_text(encoding='utf-8')),options.session,options.live)
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':
    try:main()
    except (ValueError,OSError) as error:raise SystemExit(str(error)) from None
