"""Private prepared actors with replayable creation, not yet combat targets.

Actors require an explicit source-backed creation profile. No fallback to the
default player creator, raw-stat edits, inferred creature stats or paid calls.
"""
import copy
import re
from rule_pack_authoring import canonical
from rule_pack_runtime import RulePackError
import rule_pack_world as world

MAX_ACTORS=16
MAX_BYTES=200000


def _identity(identifier):
    if not isinstance(identifier,str) or not re.fullmatch('[a-f0-9]{24}',identifier):
        raise RulePackError('Identidad de actor inválida')
    return identifier


def _public_fields(pack,fields):
    definitions=pack.document()['fields']
    if not isinstance(fields,list) or len(fields)>16 or any(not isinstance(f,str) or f not in definitions for f in fields) or len(set(fields))!=len(fields):
        raise RulePackError('Campos públicos del actor inválidos')
    return copy.deepcopy(fields)


def _no_draw(sides):
    raise RulePackError('Esta preparación de actores requiere dados confirmados; no se ha generado otra tirada')


def create(pack,identifier,npc,profile,stages,public_fields,npcs,policy,draw=None):
    identifier=_identity(identifier)
    if policy!='provided-profile':raise RulePackError('El actor requiere un perfil aportado explícitamente; no certifica reglas de PNJ')
    if not isinstance(npc,str) or npc not in {item['id'] for item in world.validate(npcs)}:
        raise RulePackError('El actor necesita un PNJ de ficción existente')
    if not isinstance(profile,str) or profile not in pack.creation_profiles:
        raise RulePackError('El actor necesita un perfil de creación explícito')
    steps=pack.creation_profiles[profile]['steps']
    if not isinstance(stages,list) or len(stages)!=len(steps):raise RulePackError('Completa todas las etapas del perfil de actor')
    selected=_public_fields(pack,public_fields);owner='director:'+identifier;records=[];sheet=None
    for index,(step,entry) in enumerate(zip(steps,stages)):
        if not isinstance(entry,dict) or set(entry)!={'inputs','physical'}:raise RulePackError('Preparación de etapa de actor inválida')
        if index==0:sheet,trace=pack.create_character(owner,entry['inputs'],physical=entry['physical'],draw=draw or _no_draw,profile=profile)
        else:sheet,trace=pack.advance_character(sheet,step,entry['inputs'],owner,physical=entry['physical'],draw=draw or _no_draw)
        records.append({'inputs':copy.deepcopy(entry['inputs']),'trace':trace})
    actor={'id':identifier,'kind':'npc','controller':'director','npc':npc,'profile':profile,'policy':policy,
        'publicFields':selected,'sheet':sheet,'creation':{'steps':records}}
    if len(canonical(actor).encode('utf-8'))>MAX_BYTES:raise RulePackError('La preparación del actor supera su límite')
    return actor


def validate(actor,pack,npcs):
    keys={'id','kind','controller','npc','profile','policy','publicFields','sheet','creation'}
    if not isinstance(actor,dict) or set(actor)!=keys or actor['kind']!='npc' or actor['controller']!='director':
        raise RulePackError('Registro privado de actor inválido')
    creation=actor['creation']
    if not isinstance(creation,dict) or set(creation)!={'steps'} or not isinstance(creation['steps'],list):
        raise RulePackError('Actor sin evidencia de creación')
    stages=[]
    for entry in creation['steps']:
        if not isinstance(entry,dict) or set(entry)!={'inputs','trace'}:raise RulePackError('Etapa de actor sin evidencia')
        trace=entry['trace']
        if not isinstance(trace,dict) or not isinstance(trace.get('rolls'),dict) or any(not isinstance(r,dict) for r in trace['rolls'].values()):
            raise RulePackError('Dados de creación de actor inválidos')
        physical={key:value.get('values') for key,value in trace['rolls'].items() if value.get('rolled')}
        stages.append({'inputs':entry['inputs'],'physical':physical})
    expected=create(pack,actor['id'],actor['npc'],actor['profile'],stages,actor['publicFields'],npcs,actor['policy'])
    for original,replayed in zip(creation['steps'],expected['creation']['steps']):
        for key,roll in original['trace']['rolls'].items():
            if roll.get('rolled') is True:
                if roll.get('origin') not in ('server','physical'):raise RulePackError('Origen de dado de actor inválido')
                if key in replayed['trace']['rolls']:replayed['trace']['rolls'][key]['origin']=roll['origin']
    if canonical(actor)!=canonical(expected):raise RulePackError('La ficha del actor no coincide con su perfil y decisiones confirmadas')
    return copy.deepcopy(expected)


def validate_registry(actors,pack,npcs,player_ids=()):
    if not isinstance(actors,list) or len(actors)>MAX_ACTORS or len(canonical(actors).encode('utf-8'))>MAX_BYTES:
        raise RulePackError('Registro privado de actores fuera de límites')
    seen=set();references=set();result=[]
    for actor in actors:
        validated=validate(actor,pack,npcs)
        if validated['id'] in seen or validated['id'] in player_ids or validated['npc'] in references:
            raise RulePackError('Un actor no puede duplicar otra ficha ni otro PNJ')
        seen.add(validated['id']);references.add(validated['npc']);result.append(validated)
    return result


def public_view(actors,pack,npcs):
    # The caller validates the registry at mutation/import boundaries. Viewing
    # uses loaded data and performs neither replay nor another remote read.
    known={npc['id']:npc for npc in world.validate(npcs) if npc['known']};result=[];definitions=pack.document()['fields']
    for actor in actors:
        npc=known.get(actor['npc'])
        if npc is None:continue
        fields=pack.view(actor['sheet'])['fields']
        result.append({'id':actor['id'],'npc':npc['id'],'name':npc['name'],
            'fields':{key:{'label':definitions[key]['label'],'value':copy.deepcopy(fields[key])} for key in actor['publicFields']}})
    return result
