"""Cairn-specific campaign adapter. Not registered as available yet."""
import copy
import json
from pathlib import Path
from systems import cairn_1e as rules,cairn_creator as creator,cairn_inventory as inventory


def initial_state(config):
    return {'ruleset':rules.ID,'characters':[],'creationDrafts':{},'messages':[],
        'tone':str(config.get('tone','Fantasía y misterio'))[:200],
        'limits':str(config.get('limits',''))[:2000],'goal':str(config.get('goal',''))[:2000]}


def resources():
    data=json.loads(Path(__file__).with_name('cairn_1e_tables.json').read_text(encoding='utf-8'))
    return {'ruleset':rules.ID,'tables':data,'items':copy.deepcopy(inventory._catalog()),
        'coverage':'Creador experimental; todavía no disponible para jugar'}


def public_view(state,me):
    result=copy.deepcopy(state)
    result['creationDrafts']={key:value for key,value in result.get('creationDrafts',{}).items() if key==me['id']}
    return result


def execute_action(state,body,me):
    # The server owns id/version and checks their replay marker before dispatching.
    action={k:v for k,v in body.items() if k not in ('id','version')}
    return creator.draft_action(state,action,me['id'])


def validate_restored(state):
    if not isinstance(state,dict) or set(state)!=set(initial_state({})) or state.get('ruleset')!=rules.ID:
        raise ValueError('Estado de Cairn incompleto o incompatible')
    if state['characters'] or state['messages']:
        raise ValueError('La recuperación de personajes e historial de Cairn requiere su integración completa')
    if not isinstance(state['creationDrafts'],dict) or len(state['creationDrafts'])>100:raise ValueError('Borradores de Cairn inválidos')
    for owner,draft in state['creationDrafts'].items():
        creator.validate(draft)
        if owner!=draft['owner']:raise ValueError('El propietario del borrador no coincide')
