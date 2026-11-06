"""Data-backed, source-identified NPC preparation for the existing PF1 adapter.

The preparation API uses this factory; no autonomous encounter is enabled by it.
Its partial melee profile does not certify lighting, cover or future choices.
"""
import copy
import hashlib
import json
from functools import lru_cache
from pathlib import Path
import combat
from rule_pack_authoring import canonical

NOTICE_FILES=('NPC-CONTENT.md','OGL-1.0a-Bestiary.txt','OGL-1.0a-Core-Rulebook.txt')


@lru_cache(maxsize=1)
def _catalog():
    document=json.loads((Path(__file__).parent/'catalogs/npc-catalog.json').read_text(encoding='utf-8'))
    if document.get('format')!='cronicas-npc-catalog-1' or not isinstance(document.get('templates'),dict):
        raise ValueError('Catálogo de PNJ incompatible')
    return document


def prepare(identifier,ruleset,name=None,mode='basic-melee'):
    if not isinstance(identifier,str) or identifier not in _catalog()['templates']:raise ValueError('Plantilla de PNJ no disponible')
    template=_catalog()['templates'][identifier]
    if ruleset!=template['ruleset']:raise ValueError('La plantilla pertenece a otro sistema; no se convierten sus reglas')
    if mode!=template['profile']['mode']:raise ValueError('Ese modo de PNJ todavía no está automatizado')
    if name is not None and (not isinstance(name,str) or not name.strip() or len(name)>80):raise ValueError('Nombre de PNJ inválido')
    data=copy.deepcopy(template['character'])
    if name is not None:data['name']=name.strip()
    combat.profile(data)
    return data,{'template':identifier,'version':template['version'],
        'templateSha256':hashlib.sha256(canonical(template).encode('utf-8')).hexdigest(),
        'ruleset':ruleset,'license':template['license'],'licenseNotices':['/licenses/'+name for name in NOTICE_FILES],
        'sources':copy.deepcopy(template['sources']),
        'coverage':copy.deepcopy(template['coverage']),'profile':copy.deepcopy(template['profile'])}


def validate_character(character,ruleset):
    proof=character.get('npcCreation')
    if proof is None:return
    if not isinstance(proof,dict) or not isinstance(proof.get('template'),str):raise ValueError('PNJ sin procedencia válida')
    expected,source=prepare(proof['template'],ruleset,name=character.get('name'))
    if set(proof)-set(source)-{'manualOverride'} or any(proof.get(key)!=value for key,value in source.items()):
        raise ValueError('La procedencia del PNJ no coincide con su plantilla versionada')
    if type(proof.get('manualOverride'))!=bool:raise ValueError('Indica si el PNJ fue corregido excepcionalmente')
    if character.get('owner')!='director' or character.get('enemy') is not True:raise ValueError('Un PNJ preparado conserva su controlador de aventura')
    keys=[key for key in expected if key not in ('hp','name')]
    if not proof['manualOverride'] and canonical({key:character.get(key) for key in keys})!=canonical({key:expected[key] for key in keys}):
        raise ValueError('Las estadísticas del PNJ difieren de su preparación; registra una corrección excepcional')
    if any(type(character.get(key))!=int or abs(character[key])>10000 for key in ('level','hp','maxHp','ac','speed','initiative','attack')):
        raise ValueError('Totales de PNJ inválidos')
    if not 1<=character['maxHp']<=10000 or not -10000<=character['hp']<=character['maxHp'] or not 1<=character['speed']<=100 or not 1<=character['level']<=100:
        raise ValueError('PG, nivel o velocidad de PNJ fuera de límites operativos')
    if not isinstance(character.get('abilities'),list) or len(character['abilities'])!=6 or any(type(value)!=int or not 1<=value<=60 for value in character['abilities']):raise ValueError('Características de PNJ inválidas')
    if not isinstance(character.get('saves'),list) or len(character['saves'])!=3 or any(type(value)!=int or abs(value)>10000 for value in character['saves']):raise ValueError('Salvaciones de PNJ inválidas')
    if any(type(character.get(key))!=int or not 0<=character[key]<20 for key in ('x','y')):raise ValueError('Posición de PNJ inválida')
    if character.get('meleeProfile') is not None:combat.profile(character)


def validate_restored(state):
    prepared=[character for character in state.get('characters',[]) if 'npcCreation' in character]
    if len(prepared)>16:raise ValueError('Máximo dieciséis PNJ preparados en este bloque')
    for character in prepared:validate_character(character,state.get('ruleset','pathfinder-1e'))


@lru_cache(maxsize=1)
def _notices():
    return {name:(Path(__file__).parent/'licenses'/name).read_text(encoding='utf-8') for name in NOTICE_FILES}


def export_notices(state):
    if state.get('ruleset','pathfinder-1e')!='pathfinder-1e' or not any('npcCreation' in character for character in state.get('characters',[])):return {}
    validate_restored(state)
    return copy.deepcopy(_notices())
