"""Bounded fictional people, places and links; never mechanics/player choices."""
import copy
import re
import hashlib
from rule_pack_runtime import RulePackError

MAX_NPCS=16
MAX_PLACES=8
MAX_RELATIONSHIPS=16


def validate(npcs):
    if not isinstance(npcs,list) or len(npcs)>MAX_NPCS:raise RulePackError('Memoria de PNJ fuera de límites')
    identifiers=set()
    for npc in npcs:
        if not isinstance(npc,dict) or set(npc)!={'id','name','known','public','private'}:raise RulePackError('Datos de PNJ inválidos')
        identifier=npc['id']
        if not isinstance(identifier,str) or not re.fullmatch('[a-z][a-z0-9-]{0,47}',identifier) or identifier in identifiers:raise RulePackError('Identidad de PNJ inválida o repetida')
        identifiers.add(identifier)
        if type(npc['known'])!=bool:raise RulePackError('Visibilidad de PNJ inválida')
        for key,limit in [('name',80),('public',500),('private',700)]:
            if not isinstance(npc[key],str) or len(npc[key])>limit or key=='name' and not npc[key].strip():raise RulePackError('Texto de PNJ fuera de límites')
        if not npc['known'] and npc['public']:raise RulePackError('Un PNJ desconocido no tiene información pública')
    return copy.deepcopy(npcs)


def merge(previous,updates):
    result={npc['id']:npc for npc in validate(previous)}
    if not isinstance(updates,list) or len(updates)>3:raise RulePackError('Demasiadas actualizaciones de PNJ en una intervención')
    for npc in validate(updates):
        prior=result.get(npc['id'])
        if prior and prior['known'] and not npc['known']:raise RulePackError('No se puede retirar el conocimiento de un PNJ descubierto')
        result[npc['id']]=npc
    return validate(list(result.values()))


def public_view(npcs):
    return [{key:npc[key] for key in ('id','name','public')} for npc in validate(npcs) if npc['known']]


def schema():
    return {'type':'array','items':{'type':'object','properties':{
        **{key:{'type':'string'} for key in ('id','name','public','private')},'known':{'type':'boolean'}},
        'required':['id','name','known','public','private'],'additionalProperties':False}}


def merge_places(previous,updates):
    result=merge(previous,updates)
    if len(result)>MAX_PLACES:raise RulePackError('La memoria admite como máximo ocho lugares')
    return result


def validate_places(places):
    result=validate(places)
    if len(result)>MAX_PLACES:raise RulePackError('Demasiados lugares guardados')
    return result


def _endpoints(npcs,places):
    return {**{'npc:'+item['id']:item for item in validate(npcs)},**{'place:'+item['id']:item for item in validate_places(places)}}


def validate_relationships(items,npcs,places):
    if not isinstance(items,list) or len(items)>MAX_RELATIONSHIPS:raise RulePackError('Relaciones fuera de límites')
    endpoints=_endpoints(npcs,places);seen=set()
    for item in items:
        if not isinstance(item,dict) or set(item)!={'id','from','to','known','public','private'}:raise RulePackError('Datos de relación inválidos')
        identifier=item['id']
        if not isinstance(identifier,str) or not re.fullmatch('[a-z][a-z0-9-]{0,47}',identifier) or identifier in seen:raise RulePackError('Identidad de relación inválida o repetida')
        seen.add(identifier)
        if any(not isinstance(item[key],str) or item[key] not in endpoints for key in ('from','to')) or item['from']==item['to']:
            raise RulePackError('La relación debe enlazar dos PNJ o lugares existentes distintos')
        if type(item['known'])!=bool:raise RulePackError('Visibilidad de relación inválida')
        if item['known'] and not all(endpoints[item[key]]['known'] for key in ('from','to')):raise RulePackError('Una relación pública requiere extremos conocidos por el grupo')
        for key,limit in [('public',350),('private',500)]:
            if not isinstance(item[key],str) or len(item[key])>limit:raise RulePackError('Notas de relación fuera de límites')
        if not item['known'] and item['public']:raise RulePackError('Una relación desconocida no tiene notas públicas')
    return copy.deepcopy(items)


def merge_relationships(previous,updates,npcs,places):
    result={item['id']:item for item in validate_relationships(previous,npcs,places)}
    if not isinstance(updates,list) or len(updates)>3:raise RulePackError('Como máximo tres relaciones por intervención')
    for item in validate_relationships(updates,npcs,places):
        prior=result.get(item['id'])
        if prior and (prior['known'] and not item['known'] or any(prior[key]!=item[key] for key in ('from','to'))):
            raise RulePackError('No se pueden cambiar los extremos ni ocultar de nuevo una relación conocida')
        result[item['id']]=item
    return validate_relationships(list(result.values()),npcs,places)


def public_relationships(items,npcs,places):
    endpoints=_endpoints(npcs,places)
    return [{key:copy.deepcopy(item[key]) for key in ('id','from','to','public')}|
            {'fromName':endpoints[item['from']]['name'],'toName':endpoints[item['to']]['name']}
            for item in validate_relationships(items,npcs,places)
            if item['known'] and endpoints[item['from']]['known'] and endpoints[item['to']]['known']]


def relationship_schema():
    return {'type':'array','items':{'type':'object','properties':{
        **{key:{'type':'string'} for key in ('id','from','to','public','private')},'known':{'type':'boolean'}},
        'required':['id','from','to','known','public','private'],'additionalProperties':False}}


def normalize_start_identifiers(reply,raw):
    """Translate only the observed typed-id representation, without new facts."""
    if not isinstance(reply,dict):return reply
    result=copy.deepcopy(reply);changed=0;endpoint_changes={}
    for field,prefix,kind in [('npcUpdates','npc:','npc'),('placeUpdates','place:','place'),
                              ('relationshipUpdates','rel:','rel'),('objectiveUpdates','obj:','obj')]:
        entries=result.get(field,[])
        if not isinstance(entries,list):return reply
        for entry in entries:
            if not isinstance(entry,dict):return reply
            identifier=entry.get('id')
            if isinstance(identifier,str) and identifier.startswith(prefix):
                bare=identifier[len(prefix):]
                if not re.fullmatch('[a-z][a-z0-9-]{0,47}',bare):return reply
                entry['id']=bare;changed+=1
                if kind in ('npc','place'):endpoint_changes[kind+':'+identifier]=kind+':'+bare
    if not changed:return reply
    for entry in result.get('relationshipUpdates',[]):
        for key in ('from','to'):
            value=entry.get(key)
            if isinstance(value,str) and value in endpoint_changes:entry[key]=endpoint_changes[value];changed+=1
    result['normalization']={'kind':'typed-world-identifiers-v1','sourceReplySha256':hashlib.sha256(raw).hexdigest(),'changedIdentifiers':changed}
    return result


def validate_normalization(value):
    if (not isinstance(value,dict) or set(value)!={'kind','sourceReplySha256','changedIdentifiers'}
        or value['kind']!='typed-world-identifiers-v1' or not isinstance(value['sourceReplySha256'],str)
        or not re.fullmatch('[a-f0-9]{64}',value['sourceReplySha256']) or type(value['changedIdentifiers'])!=int
        or not 1<=value['changedIdentifiers']<=128):raise RulePackError('Procedencia de identificadores normalizados inválida')
