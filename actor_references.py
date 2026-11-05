"""Bind known NPC actor identities/revisions, without declaring attacks legal.

References feed the campaign request layer. Position, actual scene visibility,
range, turns and rule-specific requirements belong to that separate layer.
No inference, dice, storage or changes of either character occur here.
"""
import copy
from rule_pack_runtime import RulePackError


def _selection(state,character_id,target_id,me,pack):
    character=next((c for c in state['characters'] if c['id']==character_id),None)
    if character is None or character['owner']!=me['id']:raise PermissionError('Solo el propietario selecciona por este personaje')
    if not pack.ready(character['sheet']):raise RulePackError('Completa la creación antes de seleccionar otra ficha')
    known={n['id'] for n in (state.get('narrative') or {}).get('npcs',[]) if n['known']}
    target=next((a for a in state.get('actors',[]) if a['id']==target_id and a['npc'] in known),None)
    if target is None or target['controller']!='director' or target['kind']!='npc':
        raise RulePackError('Actor objetivo no disponible para este personaje')
    if not pack.ready(target['sheet']):raise RulePackError('Actor objetivo no disponible para este personaje')
    binding={'character':character['id'],'target':target['id'],'npc':target['npc'],'packageSha256':pack.digest,
        'characterRevision':character['sheet']['revision'],'targetRevision':target['sheet']['revision']}
    return binding,target


def select(state,character_id,target_id,me,pack):
    """Only the reference is safe for pending public requests, not target.sheet."""
    binding,_=_selection(state,character_id,target_id,me,pack)
    return copy.deepcopy(binding)


def validate(binding,state,me,pack):
    if not isinstance(binding,dict) or set(binding)!={'character','target','npc','packageSha256','characterRevision','targetRevision'}:
        raise RulePackError('Referencia de objetivo incompleta')
    if any(type(binding[key])!=int for key in ('characterRevision','targetRevision')):
        raise RulePackError('Revisión de referencia inválida')
    expected,target=_selection(state,binding['character'],binding['target'],me,pack)
    if binding!=expected:raise RulePackError('La ficha, el objetivo o las reglas cambiaron; revisa la selección antes de tirar')
    return copy.deepcopy(target['sheet'])
