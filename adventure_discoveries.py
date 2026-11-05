"""Pure preparation of source-backed discoveries; not yet enabled in campaigns.

This describes information, never mechanical rewards or source verification.
Only an exact, explicitly provided source excerpt can become a discovery.
"""
import copy
import hashlib
import re
from rule_pack_runtime import RulePackError

FORMAT='cronicas-adventure-discoveries-1'
MAX_DISCOVERIES=12


def _identifier(value):
    if not isinstance(value,str) or not re.fullmatch('[a-z][a-z0-9-]{0,47}',value):
        raise RulePackError('Identidad de descubrimiento inválida')
    return value


def prepare(source,definitions,policy):
    """Build immutable definitions, using Unicode character offsets, not bytes."""
    if policy!='provided-adventure':raise RulePackError('Los descubrimientos requieren una fuente aportada explícitamente')
    if not isinstance(source,str) or not source or len(source)>12000:
        raise RulePackError('Fuente de descubrimientos fuera de límites')
    if not isinstance(definitions,list) or not 1<=len(definitions)<=MAX_DISCOVERIES:
        raise RulePackError('Catálogo de descubrimientos fuera de límites')
    result=[];seen=set()
    for item in definitions:
        if not isinstance(item,dict) or set(item)!={'id','objective','field','start','end','text'}:
            raise RulePackError('Definición de descubrimiento incompleta o no admitida')
        for key in ('id','objective','field'):_identifier(item[key])
        if item['id'] in seen:raise RulePackError('Descubrimiento repetido')
        seen.add(item['id'])
        start,end=item['start'],item['end']
        if type(start)!=int or type(end)!=int or not 0<=start<end<=len(source):
            raise RulePackError('Referencia de descubrimiento inválida')
        text=item['text']
        if not isinstance(text,str) or not text.strip() or len(text)>1000 or source[start:end]!=text:
            raise RulePackError('El descubrimiento debe citar exactamente su fuente')
        result.append(copy.deepcopy(item))
    return {'format':FORMAT,'policy':policy,'sourceSha256':hashlib.sha256(source.encode('utf-8')).hexdigest(),
        'definitions':result}


def validate(catalog,source):
    if not isinstance(catalog,dict) or set(catalog)!={'format','policy','sourceSha256','definitions'}:
        raise RulePackError('Catálogo de descubrimientos inválido')
    rebuilt=prepare(source,catalog['definitions'],catalog['policy'])
    if catalog!=rebuilt:raise RulePackError('Los descubrimientos no coinciden con la fuente aportada')
    return copy.deepcopy(rebuilt)


def bind(catalog,identifier,check,request):
    """Called before dice, after catalog and objectiveCheck validation by caller."""
    _identifier(identifier)
    if not isinstance(check,dict) or set(check)!={'objective','field'}:
        raise RulePackError('El descubrimiento necesita un vínculo de objetivo')
    if not isinstance(request,str) or not 1<=len(request)<=100:
        raise RulePackError('El descubrimiento necesita una solicitud concreta')
    item=next((d for d in catalog['definitions'] if d['id']==identifier),None)
    if item is None or any(item[key]!=check[key] for key in ('objective','field')):
        raise RulePackError('El descubrimiento corresponde a otro objetivo o resultado')
    return {'id':identifier,'objective':check['objective'],'field':check['field'],
        'request':request,'sourceSha256':catalog['sourceSha256']}


def resolve(catalog,binding,proof,message):
    """Return one reveal receipt or None; caller commits it with the action.

    The caller must independently validate the engine proof and chronology.
    This helper never interprets narration or evaluates a mechanical rule.
    """
    if type(message)!=int or message<0:raise RulePackError('Origen de revelación inválido')
    if not isinstance(binding,dict) or set(binding)!={'id','objective','field','request','sourceSha256'}:
        raise RulePackError('Vínculo de descubrimiento inválido')
    expected=bind(catalog,binding['id'],{k:binding[k] for k in ('objective','field')},binding['request'])
    if binding!=expected:raise RulePackError('La fuente del descubrimiento ha cambiado')
    if not isinstance(proof,dict) or any(proof.get(key)!=binding[key] for key in ('objective','field','request')):
        raise RulePackError('La evidencia corresponde a otra solicitud')
    if type(proof.get('met'))!=bool or type(proof.get('matchedInputs'))!=bool:
        raise RulePackError('Evidencia de descubrimiento incompleta')
    if not proof['matchedInputs'] or not proof['met']:return None
    return {**copy.deepcopy(binding),'message':message}


def public_view(catalog,receipts):
    """Only committed receipts enter this projection; never export the catalog."""
    if not isinstance(receipts,list) or len(receipts)>MAX_DISCOVERIES:
        raise RulePackError('Revelaciones fuera de límites')
    known={item['id']:item for item in catalog['definitions']};result=[];seen=set()
    for receipt in receipts:
        if not isinstance(receipt,dict) or set(receipt)!={'id','objective','field','request','sourceSha256','message'}:
            raise RulePackError('Revelación incompleta')
        identifier=_identifier(receipt['id'])
        expected=bind(catalog,identifier,{k:receipt[k] for k in ('objective','field')},receipt['request'])
        if any(receipt[key]!=value for key,value in expected.items()) or type(receipt['message'])!=int or receipt['message']<0:
            raise RulePackError('Revelación incompatible con su definición')
        if identifier in seen:raise RulePackError('Revelación duplicada')
        seen.add(identifier);item=known.get(identifier)
        if item is None or receipt.get('sourceSha256')!=catalog['sourceSha256']:
            raise RulePackError('Revelación ajena al catálogo')
        result.append({'id':identifier,'text':item['text'],'message':receipt['message']})
    return result
