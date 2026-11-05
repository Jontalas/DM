"""Persistent fiction, bounded mechanical requests and confirmed continuations."""
import copy
import json
import secrets
import time
import rule_pack_world as world
import rule_pack_objectives as objectives
from rule_pack_runtime import RulePackError,read_document
import rule_pack_director as director

CALLS={'start_pack_adventure','talk_pack_adventure','continue_pack_adventure'}
ACTIONS=CALLS|{'resolve_pack_request','cancel_pack_request'}


def _keys(value,required,optional=()):
    if not isinstance(value,dict) or not set(required)<=set(value) or set(value)-set(required)-set(optional):raise RulePackError('Datos de aventura no admitidos')


def _actor(state,identifier,me):
    actor=next((c for c in state['characters'] if c['id']==identifier),None)
    if actor is None:raise RulePackError('Personaje de aventura no disponible')
    if actor['owner']!=me['id']:raise PermissionError('Solo el propietario decide por este personaje')
    return actor


def _log(state,kind,actor,me,**values):
    state['messages'].append({'kind':kind,'character':actor['id'],'actor':me['id'],
        'speaker':me['name'] if kind=='pack-talk' else 'Director de aventura','time':time.time(),**values})


def apply(state,action,me,pack,call=None,draw=None,source_loader=None):
    kind=action['type'];result=copy.deepcopy(state);memory=result.get('narrative')
    if state['package']['policy']!='provided-rules':raise RulePackError('Activa el paquete antes de jugar')
    if kind=='start_pack_adventure':
        _keys(action,('type','character'),('sourceTitle','sourceText','sourcePolicy'))
        if not me['host']:raise PermissionError('Solo el anfitrión inicia la aventura compartida')
        if memory is not None:raise RulePackError('La aventura ya está iniciada')
        if len(state['characters'])>8:raise RulePackError('Este director admite como máximo ocho fichas; grupos grandes aún no verificados')
        if any(key in action for key in ('sourceTitle','sourceText','sourcePolicy')):
            if not all(key in action for key in ('sourceTitle','sourceText','sourcePolicy')):raise RulePackError('Faltan título, texto o permiso de la aventura aportada')
            if state.get('adventureSource') is not None or state.get('adventureSourceRef') is not None:raise RulePackError('Esta campaña ya conserva su fuente original de aventura')
            import adventure_source
            result['adventureSource']=adventure_source.create(action['sourceTitle'],action['sourceText'],action['sourcePolicy'])
        actor=_actor(result,action['character'],me);operation='start';text='';mode='action'
    else:
        if memory is None:raise RulePackError('Inicia primero la aventura')
        if kind in ('resolve_pack_request','cancel_pack_request'):
            _keys(action,('type','request'),('inputs','physical') if kind=='resolve_pack_request' else ())
            pending=memory['pending']
            if pending is None or action['request']!=pending['id']:raise RulePackError('La solicitud de acción ya no está pendiente')
            actor=_actor(result,pending['character'],me)
            if kind=='cancel_pack_request':
                memory['pending']=None
                _log(result,'pack-talk',actor,me,text='Retiro la acción pendiente.',mode='ooc');return result
            if pending['packageSha256']!=pack.digest or pending['sheetRevision']!=actor['sheet']['revision']:raise RulePackError('La ficha o reglas cambiaron; retira la solicitud y revisa la acción')
            preview=pack.preview(actor['sheet'],pending['action'],pending['inputs'],me['id'])
            if director.canonical(pending['rolls'])!=director.canonical(preview['rolls']):raise RulePackError('Los dados previstos no coinciden con la ficha y las reglas')
            inputs=action.get('inputs',pending['inputs'])
            if 'objectiveCheck' in pending:objectives.check_spec(pending['objectiveCheck'],pending['action'],memory.get('objectives',[]),pack.document())
            sheet,trace=pack.execute(actor['sheet'],pending['action'],inputs,me['id'],physical=action.get('physical'),draw=draw)
            actor['sheet']=sheet
            result['messages'].append({'kind':'pack-action','character':actor['id'],'actor':me['id'],'speaker':me['name'],
                'host':bool(me['host']),'time':time.time(),'action':pending['action'],'inputs':copy.deepcopy(inputs),'trace':trace})
            goals,proof=objectives.resolve(memory.get('objectives',[]),pending,result['messages'][-1],sheet,len(result['messages'])-1,pack.document())
            if goals:memory['objectives']=goals
            if proof is not None:result['messages'][-1]['objectiveResolution']=proof
            memory['pending']=None;memory['continuation']={'character':actor['id'],'message':len(result['messages'])-1};return result
        if kind=='talk_pack_adventure':
            _keys(action,('type','character','text','mode'))
            actor=_actor(result,action['character'],me);mode=action['mode'];text=action['text'];operation='talk'
            if mode not in ('action','dialogue','ooc') or not isinstance(text,str) or not text.strip() or len(text)>4000:raise RulePackError('Declaración inválida o fuera de límites')
            if mode=='ooc':
                _log(result,'pack-talk',actor,me,text=text,mode=mode);return result
            if memory['continuation'] is not None:raise RulePackError('Narra primero el resultado confirmado antes de otra intervención')
            if mode=='action' and memory['pending'] is not None:raise RulePackError('Resuelve o retira la solicitud pendiente antes de otra acción')
        elif kind=='continue_pack_adventure':
            _keys(action,('type',))
            continuation=memory['continuation']
            if continuation is None:raise RulePackError('No hay un resultado nuevo pendiente de narración')
            actor=_actor(result,continuation['character'],me);operation='continue';text='';mode='action'
        else:raise RulePackError('Operación narrativa desconocida')
    if not pack.ready(actor['sheet']):raise RulePackError('Completa las etapas de creación de tu personaje antes de entrar en la aventura')
    # Reserve growth before a potentially billable call. No private source read.
    game={key:value for key,value in state.items() if key not in ('authoring','authoringWorkspace','adventureSource')}
    if len(json.dumps(game,ensure_ascii=False).encode('utf-8'))>650000 or len(state['messages'])>4997:raise RulePackError('No hay espacio reservado para otra intervención; no se ha llamado a IA')
    if result.get('adventureSourceRef') is not None and result.get('adventureSource') is None and source_loader is not None:result=source_loader(result)
    prepared=director.prepare(result,operation,actor,text,mode,pack)
    reply=director.validate_reply(prepared,(call or director.propose)(prepared))
    proposal=reply['proposal'];pending=memory.get('pending') if memory else None
    if proposal['action']:
        inputs=read_document(proposal['inputsJson']);preview=pack.preview(actor['sheet'],proposal['action'],inputs,me['id'])
        pending={'id':secrets.token_hex(12),'character':actor['id'],'action':proposal['action'],'inputs':preview['inputs'],'rolls':preview['rolls'],
            'reason':proposal['reason'],'packageSha256':pack.digest,'sheetRevision':actor['sheet']['revision']}
    if operation=='talk':_log(result,'pack-talk',actor,me,text=text,mode=mode)
    _log(result,'pack-director',actor,me,text=reply['narration'],limitation=reply['limitation'],usage=reply.get('usage'),
        **({'recovery':reply['recovery']} if 'recovery' in reply else {}),
        **({'normalization':reply['normalization']} if 'normalization' in reply else {}))
    result['narrative']={'revision':(memory['revision'] if memory else 0)+1,'summary':reply['summary'],
        'preparation':reply['preparation'],'pending':pending,'continuation':None}
    npcs=world.merge(memory.get('npcs',[]) if memory else [],reply.get('npcUpdates',[]))
    if npcs:result['narrative']['npcs']=npcs
    places=world.merge_places(memory.get('places',[]) if memory else [],reply.get('placeUpdates',[]))
    relationships=world.merge_relationships(memory.get('relationships',[]) if memory else [],reply.get('relationshipUpdates',[]),npcs,places)
    if places:result['narrative']['places']=places
    if relationships:result['narrative']['relationships']=relationships
    goals=objectives.merge(memory.get('objectives',[]) if memory else [],reply.get('objectiveUpdates',[]),len(result['messages'])-1)
    if goals:result['narrative']['objectives']=goals
    if 'objectiveCheck' in reply:
        pending['objectiveCheck']=objectives.check_spec(reply['objectiveCheck'],pending['action'],goals,pack.document())
    return result


def public_view(memory):
    if memory is None:return None
    result={key:copy.deepcopy(memory[key]) for key in ('revision','summary','pending','continuation')}
    known=world.public_view(memory.get('npcs',[]))
    if known:result['npcs']=known
    known_places=world.public_view(memory.get('places',[]))
    known_relationships=world.public_relationships(memory.get('relationships',[]),memory.get('npcs',[]),memory.get('places',[]))
    if known_places:result['places']=known_places
    if known_relationships:result['relationships']=known_relationships
    known_goals=objectives.public_view(memory.get('objectives',[]))
    if known_goals:result['objectives']=known_goals
    return result


def validate(state,pack):
    memory=state.get('narrative')
    if memory is None:
        if any(event.get('kind') in ('pack-talk','pack-director') for event in state['messages']):raise RulePackError('El registro narrativo requiere su memoria de aventura')
        return
    if not state['characters']:raise RulePackError('Aventura sin personajes')
    _keys(memory,('revision','summary','preparation','pending','continuation'),('npcs','objectives','places','relationships'))
    world.validate_places(memory.get('places',[]))
    world.validate_relationships(memory.get('relationships',[]),memory.get('npcs',[]),memory.get('places',[]))
    objectives.validate(memory.get('objectives',[]),state,pack)
    world.validate(memory.get('npcs',[]))
    if {npc['id'] for npc in memory.get('npcs',[])}&{actor['id'] for actor in state['characters']}:raise RulePackError('Un personaje jugador no puede convertirse en PNJ')
    if type(memory['revision'])!=int or not 1<=memory['revision']<=1000000:raise RulePackError('Revisión narrativa inválida')
    for key,limit in (('summary',4000),('preparation',6000)):
        if not isinstance(memory[key],str) or not memory[key].strip() or len(memory[key])>limit:raise RulePackError('Memoria narrativa fuera de límites')
    pending=memory['pending'];continuation=memory['continuation']
    if pending is not None and continuation is not None:raise RulePackError('No puede haber solicitud y resultado pendientes a la vez')
    if pending is not None:
        _keys(pending,('id','character','action','inputs','rolls','reason','packageSha256','sheetRevision'),('objectiveCheck',))
        if 'objectiveCheck' in pending:objectives.check_spec(pending['objectiveCheck'],pending['action'],memory.get('objectives',[]),pack.document())
        if not isinstance(pending['id'],str) or not 1<=len(pending['id'])<=100 or not isinstance(pending['reason'],str) or not 1<=len(pending['reason'])<=600:raise RulePackError('Solicitud narrativa inválida')
        actor=next((c for c in state['characters'] if c['id']==pending['character']),None)
        if actor is None or pending['packageSha256']!=pack.digest or type(pending['sheetRevision'])!=int or pending['sheetRevision']!=actor['sheet']['revision']:raise RulePackError('Solicitud vinculada a otra ficha o reglas')
        if not isinstance(pending['action'],str) or pending['action'] not in pack.document()['actions'] or pack.document()['actions'][pending['action']].get('permission','owner')!='owner':raise RulePackError('La solicitud no puede ejecutar herramientas del anfitrión')
        preview=pack.preview(actor['sheet'],pending['action'],pending['inputs'],actor['owner'])
        if director.canonical(pending['rolls'])!=director.canonical(preview['rolls']):raise RulePackError('Los dados previstos no coinciden con la ficha y las reglas')
    if continuation is not None:
        _keys(continuation,('character','message'));index=continuation['message']
        if type(index)!=int or not 0<=index<len(state['messages']):raise RulePackError('Continuación narrativa sin resultado')
        event=state['messages'][index]
        if event.get('kind')!='pack-action' or event.get('character')!=continuation['character']:raise RulePackError('Continuación narrativa ligada a otro resultado')


def validate_event(event,characters):
    base=('kind','character','actor','speaker','time','text')
    _keys(event,(*base,'mode') if event['kind']=='pack-talk' else (*base,'limitation','usage'),
        ('recovery','normalization') if event['kind']=='pack-director' else ())
    if not isinstance(event['character'],str) or event['character'] not in characters or not isinstance(event['text'],str) or not 1<=len(event['text'])<=10000:raise RulePackError('Intervención narrativa inválida')
    if event['kind']=='pack-talk':
        if event['mode'] not in ('action','dialogue','ooc') or len(event['text'])>4000:raise RulePackError('Declaración guardada inválida')
    elif not isinstance(event['limitation'],str) or len(event['limitation'])>1000:raise RulePackError('Limitación narrativa inválida')
    elif event['usage'] is not None:
        usage=event['usage']
        if not isinstance(usage,dict) or set(usage)!={'inputTokens','outputTokens','latencyMs'} or any(type(v)!=int or not 0<=v<=10000000 for v in usage.values()):raise RulePackError('Consumo narrativo guardado inválido')
    if not isinstance(event['speaker'],str) or not 1<=len(event['speaker'])<=120:raise RulePackError('Autor narrativo inválido')
    if 'recovery' in event:director.validate_recovery(event['recovery'])
    if 'normalization' in event:
        world.validate_normalization(event['normalization'])
        if 'recovery' in event:raise RulePackError('Procedencias de respuesta incompatibles')
