"""Bounded fictional NPC memory; never executable mechanics or player choices."""
import copy
import re
from rule_pack_runtime import RulePackError

MAX_NPCS=16


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
