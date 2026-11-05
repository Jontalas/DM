"""Player-selected abstract scene actions; no inferred targets or spatial rules."""
import copy
import secrets
import time
from rule_pack_runtime import RulePackError
from rule_pack_authoring import canonical
import actor_references
import target_context
import target_journal


def _room(state):
    memory=state.get('narrative')
    if state['package']['policy']!='provided-rules' or memory is None:raise RulePackError('Inicia una aventura con reglas activadas')
    if len(state.get('targetResolutions',[]))>=target_journal.MAX_RECORDS:raise RulePackError('El registro privado alcanza su límite; conserva una copia antes de ampliarlo')
    return memory


def request(state,action,me,pack):
    if set(action)!={'type','character','action','target','inputs'}:raise RulePackError('Solicitud dirigida incompleta o no admitida')
    memory=_room(state)
    if memory['pending'] is not None or memory['continuation'] is not None:raise RulePackError('Resuelve la intervención anterior antes de otra acción')
    binding,preview=target_context.select(state,action['character'],action['target'],action['action'],action['inputs'],me,pack)
    npc=next(n for n in memory['npcs'] if n['id']==binding['npc']);label=pack.document()['actions'][action['action']]['label']
    result=copy.deepcopy(state);memory=result['narrative'];text='Solicito '+label+' sobre '+npc['name']+'.'
    memory['pending']={'id':secrets.token_hex(12),'character':binding['character'],'action':action['action'],'inputs':preview['inputs'],
        'rolls':preview['rolls'],'reason':'Acción elegida sobre '+npc['name']+' en contexto abstracto compartido.',
        'packageSha256':pack.digest,'sheetRevision':binding['characterRevision'],'targetBinding':binding}
    result['messages'].append({'kind':'pack-talk','character':binding['character'],'actor':me['id'],'speaker':me['name'],'time':time.time(),'text':text,'mode':'action'})
    return result


def check_pending(state,pending,me,pack):
    if 'objectiveCheck' in pending or 'discoveryBindings' in pending:
        raise RulePackError('La vinculación de objetivos de aventura a otro actor aún no está soportada')
    binding=pending['targetBinding']
    if not isinstance(binding,dict) or binding.get('character')!=pending['character']:raise RulePackError('Objetivo vinculado a otra ficha')
    actor_references.validate(binding,state,me,pack)
    actual,preview=target_context.select(state,pending['character'],binding['target'],pending['action'],pending['inputs'],me,pack)
    if actual!=binding or canonical(preview['rolls'])!=canonical(pending['rolls']):raise RulePackError('La selección o sus dados cambiaron antes de resolver')
    return binding


def resolve(state,action,me,pack,draw=None):
    memory=_room(state);pending=memory['pending'];binding=check_pending(state,pending,me,pack)
    target_sheet=actor_references.validate(binding,state,me,pack)
    character=next(c for c in state['characters'] if c['id']==pending['character'])
    inputs=action.get('inputs',pending['inputs'])
    # Edited choices are validated again against the same bound identities;
    # neither another NPC nor a changed revision can be substituted here.
    target_context.select(state,pending['character'],binding['target'],pending['action'],inputs,me,pack)
    player,other,trace=pack.execute_targeted(character['sheet'],target_sheet,pending['action'],inputs,me['id'],physical=action.get('physical'),draw=draw)
    result=copy.deepcopy(state);position=len(result['messages']);public=copy.deepcopy(trace);public.pop('target')
    result['messages'].append({'kind':'pack-action','character':pending['character'],'actor':me['id'],'speaker':me['name'],'host':bool(me['host']),
        'time':time.time(),'action':pending['action'],'inputs':copy.deepcopy(inputs),'trace':public,'targetRef':{'id':binding['target'],'npc':binding['npc']}})
    shared=next(actor for actor in state['actors'] if actor['id']==binding['target'])['publicFields']
    result.setdefault('targetResolutions',[]).append({'message':position,'binding':copy.deepcopy(binding),'inputs':copy.deepcopy(inputs),'trace':trace,'sharedFields':copy.deepcopy(shared),'continuationScope':'public'})
    if len(canonical(result['targetResolutions']).encode('utf-8'))>target_journal.MAX_BYTES:raise RulePackError('La evidencia privada supera su límite; no se ha aplicado la acción')
    next(c for c in result['characters'] if c['id']==pending['character'])['sheet']=player
    next(a for a in result['actors'] if a['id']==binding['target'])['sheet']=other
    result['narrative']['pending']=None;result['narrative']['continuation']={'character':pending['character'],'message':position}
    return result
