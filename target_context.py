"""Preflight for explicitly abstract, shared-scene actions; no spatial combat.

Candidate projection uses only loaded data. It does not pick a target, make a
decision for the player, or infer scene/visibility from a fictional NPC name.
Used by explicit campaign requests; individual sight, range and turns are not
approximated by this shared-scene mode.
"""
import actor_references
from rule_pack_runtime import RulePackError
from target_journal import public_roll_shape


def context_key(spec):return spec['sceneField']+':'+spec['visibleField']


def _actions(pack):
    return {key:spec for key,spec in pack.document()['actions'].items()
        if key not in pack.reserved_creation_actions and spec.get('permission','owner')=='owner' and 'targetContext' in spec}


def options(state,me,pack):
    contexts={context_key(action['targetContext']):action['targetContext'] for action in _actions(pack).values()}
    if not contexts:return {'format':'cronicas-target-options-1','byCharacter':{}}
    known={n['id'] for n in (state.get('narrative') or {}).get('npcs',[]) if n['known']}
    visible=[]
    for actor in state.get('actors',[]):
        if actor['npc'] in known and actor['kind']=='npc' and actor['controller']=='director' and pack.ready(actor['sheet']):
            visible.append((actor['id'],pack.view(actor['sheet'])['fields']))
    result={}
    for character in state['characters']:
        if character['owner']!=me['id'] or not pack.ready(character['sheet']):continue
        fields=pack.view(character['sheet'])['fields'];groups={}
        for key,spec in contexts.items():
            targets=[identifier for identifier,target_fields in visible if pack.shared_target_context(spec,fields,target_fields)]
            if targets:groups[key]=targets
        if groups:result[character['id']]=groups
    return {'format':'cronicas-target-options-1','byCharacter':result}


def select(state,character_id,target_id,action_id,inputs,me,pack):
    if not isinstance(action_id,str):raise RulePackError('Identidad de acción dirigida inválida')
    action=_actions(pack).get(action_id)
    if action is None:raise RulePackError('La acción aún no tiene un contexto jugable de objetivo soportado')
    binding=actor_references.select(state,character_id,target_id,me,pack)
    target_sheet=actor_references.validate(binding,state,me,pack)
    target=next(actor for actor in state['actors'] if actor['id']==target_id)
    public_roll_shape(action,target['publicFields'])
    character=next(character for character in state['characters'] if character['id']==character_id)
    preview=pack.preview_targeted(character['sheet'],target_sheet,action_id,inputs,me['id'])
    return binding,preview
