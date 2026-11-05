"""Data-backed, source-identified NPC preparation for the existing PF1 adapter.

No spawn API or autonomous encounter is enabled by this factory. Its partial
melee profile does not certify lighting, cover, conditions or future choices.
"""
import copy
import hashlib
import json
from functools import lru_cache
from pathlib import Path
import combat
from rule_pack_authoring import canonical


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
        'catalogSha256':hashlib.sha256(canonical(_catalog()).encode('utf-8')).hexdigest(),
        'ruleset':ruleset,'license':template['license'],'sources':copy.deepcopy(template['sources']),
        'coverage':copy.deepcopy(template['coverage']),'profile':copy.deepcopy(template['profile'])}
