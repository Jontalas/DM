"""Durable paid-call reservation and response recovery, private to one host.

Unknown outcomes never authorize another automatic call. A captured response is
reparsed using its original source scheme, even after process restart.
"""
import base64
from collections import OrderedDict
import hashlib
import json
import os
import threading
import weakref
import zlib
from firebase_store import Conflict,Unavailable
from rule_pack_runtime import RulePackError
import rule_pack_authoring as authoring

MAX_PAYLOAD=350000
_memory=weakref.WeakKeyDictionary()
_lock=threading.RLock()


def key(actor,request_sha):return hashlib.sha256((actor+':'+request_sha).encode()).hexdigest()


def input_request(prepared):
    if prepared.get('sourceScheme')=='pf-director-v1':
        import legacy_director_attempt as legacy
        return legacy.capture_input(prepared)
    if 'captureRequest' in prepared:raise RulePackError('Entrada de captura fuera de su contrato')
    return prepared['request']


def inputs_match(saved,current,saved_scheme,current_scheme):
    if authoring.canonical(saved)==authoring.canonical(current):return True
    if saved_scheme==current_scheme=='pf-director-v1':
        import legacy_director_attempt as legacy
        if (isinstance(saved,dict) and isinstance(current,dict)
            and isinstance(saved.get('context'),dict) and isinstance(current.get('context'),dict)
            and saved.get('contract')==current.get('contract')==legacy.CONTRACT):
            return authoring.canonical(legacy.keyed_request(saved))==authoring.canonical(legacy.keyed_request(current))
    return False


def pack(value):
    raw=authoring.canonical(value).encode('utf-8')
    if len(raw)>MAX_PAYLOAD:raise RulePackError('La captura de preparación supera su límite')
    return zlib.compress(raw)


def unpack(data):
    try:
        if not isinstance(data,bytes) or len(data)>MAX_PAYLOAD+1000:raise ValueError()
        decoder=zlib.decompressobj();raw=decoder.decompress(data,MAX_PAYLOAD+1)
        if len(raw)>MAX_PAYLOAD or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:raise ValueError()
        return json.loads(raw)
    except (ValueError,TypeError,zlib.error):raise Unavailable('La captura de preparación no está íntegra') from None


def check_attempt(attempt,actor,request_sha):
    if attempt.get('actor')!=actor or attempt.get('requestSha256')!=request_sha:raise Conflict('El intento pertenece a otra identidad o solicitud')
    if attempt.get('sourceScheme') not in (authoring.SOURCE_SCHEME,authoring.LEGACY_SOURCE_SCHEME,'director-v1','pf-director-v1'):raise RulePackError('Esquema de fuentes del intento desconocido')


def _remember(store,cid,identifier,payload):
    data=pack(payload)
    with _lock:
        cache=_memory.setdefault(store,OrderedDict());cache[cid,identifier]=data;cache.move_to_end((cid,identifier))
        while len(cache)>8:cache.popitem(last=False)
    return data


def _recall(store,cid,identifier):
    with _lock:
        cache=_memory.get(store);data=cache.get((cid,identifier)) if cache else None
    return data


def forget(store,cid,identifier):
    with _lock:
        cache=_memory.get(store)
        if cache is not None:cache.pop((cid,identifier),None)


def _restore(prepared,payload,scheme):
    original=authoring.prepare_input(prepared['request'],scheme)
    if not isinstance(payload,dict) or set(payload)!={'kind','value','latencyMs'}:raise RulePackError('Captura de preparación inválida')
    if payload['kind']=='raw':
        try:report=authoring.parse_response(original,base64.b64decode(payload['value'],validate=True),payload['latencyMs'])
        except (ValueError,KeyError,TypeError,AttributeError):raise RulePackError('La respuesta guardada sigue siendo inválida; no se ha repetido la inferencia') from None
    elif payload['kind']=='report':report=payload['value']
    else:raise RulePackError('Tipo de captura desconocido')
    record={'request':original['request'],'sha256':original['sha256'],'sourceScheme':scheme,'report':report}
    authoring.validate_record(record);return record


def run(store,cid,actor,prepared,converter=None,restore=None):
    converter=authoring.propose if converter is None else converter
    restore=_restore if restore is None else restore
    identifier=key(actor,prepared['sha256'])
    from model_config import model_name
    configured=bool(os.environ.get('ANTHROPIC_API_KEY'))
    try:model_name()
    except ValueError:configured=False
    attempt=store.begin_rule_preparation(cid,identifier,actor,prepared,allow_create=configured)
    if attempt is None:raise RulePackError('Claude Haiku sin configurar; no se ha reservado ni llamado al proveedor')
    check_attempt(attempt,actor,prepared['sha256'])
    restore_prepared=prepared
    if attempt['sourceScheme']=='pf-director-v1' and attempt.get('inputData') is not None:
        # Reparse only capabilities present when this response was captured.
        restore_prepared={**prepared,'request':unpack(attempt['inputData'])}
    data=attempt.get('responseData') or _recall(store,cid,identifier)
    if data is not None:
        if not attempt.get('responseData'):store.save_rule_preparation_response(cid,identifier,actor,prepared['sha256'],data)
        return restore(restore_prepared,unpack(data),attempt['sourceScheme'])
    if not attempt.get('fresh'):
        raise Conflict('Existe un intento en curso o de resultado incierto sin respuesta recuperable. No se hará otra llamada de IA automáticamente')
    captured=[]
    def observe(raw,elapsed):
        payload={'kind':'raw','value':base64.b64encode(raw).decode(),'latencyMs':elapsed};captured.append(payload)
        data=_remember(store,cid,identifier,payload)
        try:store.save_rule_preparation_response(cid,identifier,actor,prepared['sha256'],data)
        except Exception as error:raise Unavailable('La respuesta se conserva en memoria, pero no se pudo guardar; reintenta el mismo envío sin volver a generar') from error
    report=converter(prepared,response_observer=observe)
    if captured:return restore(restore_prepared,captured[0],attempt['sourceScheme'])
    # Deterministic/injected converters may return a validated report directly.
    payload={'kind':'report','value':report,'latencyMs':report.get('usage',{}).get('latencyMs',0)}
    record=restore(restore_prepared,payload,attempt['sourceScheme'])
    data=_remember(store,cid,identifier,payload)
    store.save_rule_preparation_response(cid,identifier,actor,prepared['sha256'],data)
    return record
