"""Immutable private adventure text and deterministic bounded fragment retrieval.

Sources describe fiction, never executable rules, instructions or occurred facts.
Original text is retained; fragmentation is only a local context projection.
"""
import copy
import hashlib
import json
import re
import zlib
from rule_pack_authoring import canonical
from rule_pack_runtime import RulePackError

FORMAT='cronicas-adventure-source-1'
REF_FORMAT='cronicas-adventure-source-ref-1'
MAX_CHARS=12000
MAX_BYTES=50000


def create(title,text,policy):
    if policy!='provided-adventure':raise RulePackError('Confirma que puedes utilizar esta aventura aportada')
    if not isinstance(title,str) or not title.strip() or len(title)>100:raise RulePackError('Título de fuente de aventura inválido')
    if not isinstance(text,str) or not text.strip() or len(text)>MAX_CHARS or any(ord(c)<32 and c not in '\n\r\t' for c in text):
        raise RulePackError('Aporta texto legible de aventura de hasta 12.000 caracteres')
    record={'format':FORMAT,'title':title,'text':text,'policy':policy}
    record['sha256']=hashlib.sha256(canonical(record).encode()).hexdigest()
    if len(canonical(record).encode())>MAX_BYTES:raise RulePackError('La fuente supera su límite en bytes')
    return record


def validate(record):
    if not isinstance(record,dict) or set(record)!={'format','title','text','policy','sha256'} or record['format']!=FORMAT:raise RulePackError('Fuente de aventura inválida')
    expected=create(record['title'],record['text'],record['policy'])
    if record!=expected:raise RulePackError('La aventura no coincide con su huella original')
    return copy.deepcopy(record)


def reference(record):
    record=validate(record)
    return {'format':REF_FORMAT,'sha256':record['sha256'],'title':record['title'],'characters':len(record['text'])}


def validate_ref(ref):
    if (not isinstance(ref,dict) or set(ref)!={'format','sha256','title','characters'} or ref['format']!=REF_FORMAT
        or not isinstance(ref['sha256'],str) or not re.fullmatch('[a-f0-9]{64}',ref['sha256'])
        or not isinstance(ref['title'],str) or not ref['title'].strip() or len(ref['title'])>100
        or type(ref['characters'])!=int or not 1<=ref['characters']<=MAX_CHARS):raise RulePackError('Referencia privada de aventura inválida')
    return ref


def decode(ref,packed):
    validate_ref(ref)
    if not isinstance(packed,bytes) or len(packed)>MAX_BYTES+1000:raise RulePackError('Fuente privada de aventura fuera de límites')
    try:
        decoder=zlib.decompressobj();raw=decoder.decompress(packed,MAX_BYTES+1)
        if len(raw)>MAX_BYTES or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:raise ValueError()
        record=validate(json.loads(raw))
        if reference(record)!=ref:raise ValueError()
        return record
    except (ValueError,TypeError,UnicodeError,zlib.error):raise RulePackError('No se puede recuperar una aventura privada íntegra') from None


def detach(state):
    if state.get('ruleset')!='rule-pack':return state,None
    source=state.get('adventureSource');ref=state.get('adventureSourceRef')
    if ref is not None:validate_ref(ref)
    if source is None:return state,None
    source=validate(source);expected=reference(source)
    if ref is not None and ref!=expected:raise RulePackError('Dos versiones incompatibles de la aventura')
    raw=canonical(source).encode();result=copy.deepcopy(state)
    result['adventureSource']=None;result['adventureSourceRef']=expected
    return result,{'reference':expected,'raw':raw,'packed':zlib.compress(raw)}


def fragments(record,query='',opening=False):
    record=validate(record)
    if opening:return {'title':record['title'],'sha256':record['sha256'],'fragments':[{'id':'original','text':record['text']}]}
    text=record['text'];chunks=[];start=0
    # Stable character offsets preserve references even in unformatted prose.
    while start<len(text):
        end=min(start+1400,len(text))
        if end<len(text):
            boundary=text.rfind('\n',start+700,end)
            if boundary!=-1:end=boundary+1
        chunks.append({'id':f'chars-{start}-{end}','text':text[start:end]});start=end
    words=set(list(dict.fromkeys(re.findall(r'[^\W\d_]{4,}',query.casefold())))[:128])
    ranked=sorted(enumerate(chunks),key=lambda pair:(-len(words&set(re.findall(r'[^\W\d_]{4,}',pair[1]['text'].casefold()))),pair[0]))
    selected=sorted(ranked[:3]);result=[];remaining=8000
    for _,chunk in selected:
        size=len(chunk['text'].encode())
        if size>remaining:continue
        result.append(chunk);remaining-=size
    return {'title':record['title'],'sha256':record['sha256'],'fragments':result}
