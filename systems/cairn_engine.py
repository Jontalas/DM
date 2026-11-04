"""Cairn-specific campaign adapter. Not registered as available yet."""
import copy
import json
import secrets
import time
import math
from pathlib import Path
from systems import cairn_1e as rules,cairn_creator as creator,cairn_inventory as inventory


def initial_state(config):
    return {'ruleset':rules.ID,'characters':[],'creationDrafts':{},'importedDrafts':{},'messages':[],
        'tone':str(config.get('tone','Fantasía y misterio'))[:200],
        'limits':str(config.get('limits',''))[:2000],'goal':str(config.get('goal',''))[:2000]}


def resources():
    data=json.loads(Path(__file__).with_name('cairn_1e_tables.json').read_text(encoding='utf-8'))
    return {'ruleset':rules.ID,'tables':data,'items':copy.deepcopy(inventory._catalog()),
        'coverage':'Creador experimental; todavía no disponible para jugar'}


def public_view(state,me):
    result=copy.deepcopy(state)
    result['creationDrafts']={key:value for key,value in result.get('creationDrafts',{}).items() if key==me['id']}
    if not me['host']:result.pop('importedDrafts',None)
    for character in result['characters']:
        if character['owner']!=me['id']:character.pop('creation',None)
    return result


def execute_action(state,body,me):
    # The server owns id/version and checks their replay marker before dispatching.
    action={k:v for k,v in body.items() if k not in ('id','version')}
    if action.get('type')=='confirm_character':
        if set(action)!={'type','choices'}:raise ValueError('La confirmación solo admite elecciones del personaje')
        draft=state['creationDrafts'].get(me['id'])
        if draft is None:raise ValueError('No tienes un borrador pendiente de confirmación')
        if len(state['characters'])>=400:raise ValueError('Límite de personajes de la campaña alcanzado')
        character=creator.finalize(draft,action['choices'],me['id'])
        character['id']=secrets.token_hex(12)
        result=copy.deepcopy(state);result['characters'].append(character);del result['creationDrafts'][me['id']]
        result['messages'].append({'kind':'rules','speaker':'Motor de Cairn','text':character['name']+' ha confirmado su personaje.',
            'time':time.time(),'character':character['id']})
        return result
    if action.get('type')=='recover_imported_draft':
        if not me['host']:raise PermissionError('Solo el anfitrión recupera borradores de una copia importada')
        if set(action)!={'type','draft'}:raise ValueError('Recuperación de borrador inválida')
        if me['id'] in state['creationDrafts']:raise ValueError('Confirma primero tu borrador actual; no se sobrescriben tiradas')
        key=action['draft']
        if not isinstance(key,str) or key not in state.get('importedDrafts',{}):raise ValueError('Borrador importado no disponible')
        result=copy.deepcopy(state);draft=result['importedDrafts'].pop(key);draft['owner']=me['id']
        result['creationDrafts'][me['id']]=draft
        return result
    return creator.draft_action(state,action,me['id'])


def validate_restored(state):
    if isinstance(state,dict):state.setdefault('importedDrafts',{})
    if not isinstance(state,dict) or set(state)!=set(initial_state({})) or state.get('ruleset')!=rules.ID:
        raise ValueError('Estado de Cairn incompleto o incompatible')
    if not isinstance(state['characters'],list) or len(state['characters'])>400:raise ValueError('Personajes de Cairn inválidos')
    ids=set()
    for character in state['characters']:
        creator.validate_created(character)
        if character['id'] in ids:raise ValueError('Personaje duplicado en la copia')
        ids.add(character['id'])
    for key,limit in [('tone',200),('limits',2000),('goal',2000)]:
        if not isinstance(state[key],str) or len(state[key])>limit:raise ValueError('Texto de campaña inválido')
    if not isinstance(state['messages'],list) or len(state['messages'])>10000:raise ValueError('Historial de Cairn inválido')
    for message in state['messages']:
        if (not isinstance(message,dict) or set(message)!={'kind','speaker','text','time','character'} or message['kind']!='rules'
            or any(not isinstance(message[k],str) or len(message[k])>6000 for k in ('speaker','text','character'))
            or type(message['time']) not in (int,float) or not math.isfinite(message['time'])):raise ValueError('Mensaje de Cairn inválido')
    if not isinstance(state['creationDrafts'],dict) or len(state['creationDrafts'])>100:raise ValueError('Borradores de Cairn inválidos')
    for owner,draft in state['creationDrafts'].items():
        creator.validate(draft)
        if owner!=draft['owner']:raise ValueError('El propietario del borrador no coincide')
    if (not isinstance(state['importedDrafts'],dict) or len(state['importedDrafts'])+len(state['creationDrafts'])>400):raise ValueError('Archivo de borradores inválido')
    for key,draft in state['importedDrafts'].items():
        if not isinstance(key,str) or not key or len(key)>200:raise ValueError('Referencia de borrador inválida')
        creator.validate(draft)


def import_campaign(incoming,me):
    if not me['host']:raise PermissionError('Solo el anfitrión importa una campaña')
    result=copy.deepcopy(incoming);validate_restored(result)
    for character in result['characters']:
        character['owner']=me['id'];character['creation']['draft']['owner']=me['id']
    # Preserve every unfinished draft; the host explicitly recovers one at a time.
    for draft in result['creationDrafts'].values():
        base=draft['owner'];key=base;suffix=1
        while key in result['importedDrafts']:
            key=base+':'+str(suffix);suffix+=1
        result['importedDrafts'][key]=draft
    result['creationDrafts']={}
    validate_restored(result)
    return result
