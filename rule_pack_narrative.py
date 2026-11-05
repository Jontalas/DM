"""Persistent fiction, bounded mechanical requests and confirmed continuations."""
import copy
import json
import re
import secrets
import time
import rule_pack_world as world
import rule_pack_objectives as objectives
import adventure_discoveries as discoveries
from rule_pack_runtime import RulePackError,read_document
import rule_pack_director as director

CALLS={'start_pack_adventure','talk_pack_adventure','continue_pack_adventure'}
ACTIONS=CALLS|{'resolve_pack_request','cancel_pack_request','prepare_pack_discoveries','request_pack_target'}


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
    prepared_plan=None;prepared_goals=None;prepared_npcs=None
    if state['package']['policy']!='provided-rules':raise RulePackError('Activa el paquete antes de jugar')
    if kind=='request_pack_target':
        from target_actions import request
        return request(state,action,me,pack)
    if kind=='prepare_pack_discoveries':
        _keys(action,('type','definitions','policy'))
        if not me['host']:raise PermissionError('Solo el anfitrión prepara consecuencias de la aventura')
        if memory is None or memory['pending'] is not None or memory['continuation'] is not None:
            raise RulePackError('Prepara descubrimientos entre intervenciones resueltas')
        if 'action-results' not in pack.document()['requires']:raise RulePackError('Los descubrimientos requieren resultados explícitos de acción')
        if 'discoveries' in memory:raise RulePackError('El catálogo de descubrimientos es inmutable')
        if result.get('adventureSource') is None and source_loader is not None:result=source_loader(result);memory=result['narrative']
        source=result.get('adventureSource')
        if source is None:raise RulePackError('Los descubrimientos necesitan la fuente original aportada')
        catalog=discoveries.prepare(source['text'],action['definitions'],action['policy'])
        for definition in catalog['definitions']:
            goal=next((g for g in memory.get('objectives',[]) if g['id']==definition['objective']),None)
            field=pack.document()['fields'].get(definition['field'])
            if goal is None or not goal['known'] or goal['status']!='open' or field is None or field['type']!='boolean' or 'initial' not in field:
                raise RulePackError('El descubrimiento necesita un objetivo abierto conocido y resultado booleano almacenado')
        index=len(result['messages'])
        result['messages'].append({'kind':'system','text':'Consecuencias informativas preparadas desde la fuente aportada; no certifican reglas ni conceden recompensas.','actor':me['id'],'time':time.time()})
        memory['discoveries']={'catalog':catalog,'sourceSha256':source['sha256'],'installedAt':index,'receipts':[]}
        return result
    if kind=='start_pack_adventure':
        _keys(action,('type','character'),('sourceTitle','sourceText','sourcePolicy','plan'))
        if not me['host']:raise PermissionError('Solo el anfitrión inicia la aventura compartida')
        if memory is not None:raise RulePackError('La aventura ya está iniciada')
        if len(state['characters'])>8:raise RulePackError('Este director admite como máximo ocho fichas; grupos grandes aún no verificados')
        if 'plan' in action:
            if any(key in action for key in ('sourceTitle','sourceText')) or result.get('adventureSource') is not None or result.get('adventureSourceRef') is not None:
                raise RulePackError('La preparación estructurada debe conservar una única fuente original')
            from adventure_plan import compile_plan
            prepared_plan=compile_plan(action['plan'],pack,action.get('sourcePolicy'))
            if 'npcPreparation' in prepared_plan:
                import rule_pack_actors as actors
                preparation=prepared_plan['npcPreparation'];prepared_npcs=preparation['npcs']
                actors.validate_registry(preparation['actors'],pack,prepared_npcs,[c['id'] for c in state['characters']])
                if state.get('actors'):raise RulePackError('La preparación inicial no puede sustituir actores existentes')
            result['adventureSource']=prepared_plan['source'];prepared_goals=[]
            for offset in range(0,len(prepared_plan['objectives']),2):
                prepared_goals=objectives.merge(prepared_goals,prepared_plan['objectives'][offset:offset+2],len(result['messages']))
        elif any(key in action for key in ('sourceTitle','sourceText','sourcePolicy')):
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
            if 'targetBinding' in pending:
                from target_actions import resolve
                return resolve(result,action,me,pack,draw=draw)
            preview=pack.preview(actor['sheet'],pending['action'],pending['inputs'],me['id'])
            if director.canonical(pending['rolls'])!=director.canonical(preview['rolls']):raise RulePackError('Los dados previstos no coinciden con la ficha y las reglas')
            inputs=action.get('inputs',pending['inputs'])
            if 'objectiveCheck' in pending:objectives.check_spec(pending['objectiveCheck'],pending['action'],memory.get('objectives',[]),pack.document())
            expected=discoveries.bindings(memory['discoveries']['catalog'],pending.get('objectiveCheck'),pending['id']) if 'discoveries' in memory else []
            if pending.get('discoveryBindings',[])!=expected:raise RulePackError('La solicitud perdió su vínculo de descubrimiento')
            sheet,trace=pack.execute(actor['sheet'],pending['action'],inputs,me['id'],physical=action.get('physical'),draw=draw)
            actor['sheet']=sheet
            result['messages'].append({'kind':'pack-action','character':actor['id'],'actor':me['id'],'speaker':me['name'],
                'host':bool(me['host']),'time':time.time(),'action':pending['action'],'inputs':copy.deepcopy(inputs),'trace':trace})
            goals,proof=objectives.resolve(memory.get('objectives',[]),pending,result['messages'][-1],sheet,len(result['messages'])-1,pack.document())
            if goals:memory['objectives']=goals
            if proof is not None:result['messages'][-1]['objectiveResolution']=proof
            if 'discoveries' in memory:
                store=memory['discoveries']
                receipts=[receipt for binding in expected if (receipt:=discoveries.resolve(store['catalog'],binding,proof,len(result['messages'])-1)) is not None]
                if receipts:
                    store['receipts'].extend(receipts);result['messages'][-1]['discoveryReveals']=receipts
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
    if prepared_npcs is not None:
        game['actors']=prepared_plan['npcPreparation']['actors']
        game['preparedNpcs']=prepared_npcs
    if len(json.dumps(game,ensure_ascii=False).encode('utf-8'))>650000 or len(state['messages'])>4997:raise RulePackError('No hay espacio reservado para otra intervención; no se ha llamado a IA')
    from target_journal import public_continuation
    if result.get('adventureSourceRef') is not None and result.get('adventureSource') is None and source_loader is not None and not (operation=='continue' and public_continuation(result)):result=source_loader(result)
    prepared=director.prepare(result,operation,actor,text,mode,pack,prepared_goals=prepared_goals,prepared_npcs=prepared_npcs)
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
    if prepared['request']['contract']==director.PUBLIC_TARGET_CONTRACT:
        result['narrative']['preparation']=memory['preparation']
    npcs=world.merge(prepared_npcs if prepared_npcs is not None else memory.get('npcs',[]) if memory else [],reply.get('npcUpdates',[]))
    if npcs:result['narrative']['npcs']=npcs
    places=world.merge_places(memory.get('places',[]) if memory else [],reply.get('placeUpdates',[]))
    relationships=world.merge_relationships(memory.get('relationships',[]) if memory else [],reply.get('relationshipUpdates',[]),npcs,places)
    if places:result['narrative']['places']=places
    if relationships:result['narrative']['relationships']=relationships
    goals=objectives.merge(prepared_goals if prepared_goals is not None else memory.get('objectives',[]) if memory else [],reply.get('objectiveUpdates',[]),len(result['messages'])-1)
    if goals:result['narrative']['objectives']=goals
    if memory and 'discoveries' in memory:result['narrative']['discoveries']=copy.deepcopy(memory['discoveries'])
    if prepared_plan is not None:
        if prepared_npcs is not None:
            result['actors']=copy.deepcopy(prepared_plan['npcPreparation']['actors'])
            for prepared_actor in result['actors']:prepared_actor['introducedAt']=len(result['messages'])
        index=len(result['messages'])
        result['messages'].append({'kind':'system','text':'Preparación estructurada aportada: objetivos y consecuencias informativas cargados; no certifica reglas.','actor':me['id'],'time':time.time()})
        result['narrative']['discoveries']={'catalog':prepared_plan['catalog'],'sourceSha256':prepared_plan['source']['sha256'],
            'installedAt':index,'receipts':[],'planSha256':prepared_plan['sha256']}
    if 'objectiveCheck' in reply:
        pending['objectiveCheck']=objectives.check_spec(reply['objectiveCheck'],pending['action'],goals,pack.document())
        if 'discoveries' in result['narrative']:
            bindings=discoveries.bindings(result['narrative']['discoveries']['catalog'],pending['objectiveCheck'],pending['id'])
            if bindings:pending['discoveryBindings']=bindings
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
    if 'discoveries' in memory:
        store=memory['discoveries'];result['discoveries']=discoveries.public_view(store['catalog'],store['receipts'])
    return result


def validate(state,pack):
    memory=state.get('narrative')
    if memory is None:
        if any(event.get('kind') in ('pack-talk','pack-director') for event in state['messages']):raise RulePackError('El registro narrativo requiere su memoria de aventura')
        return
    if not state['characters']:raise RulePackError('Aventura sin personajes')
    _keys(memory,('revision','summary','preparation','pending','continuation'),('npcs','objectives','places','relationships','discoveries'))
    world.validate_places(memory.get('places',[]))
    world.validate_relationships(memory.get('relationships',[]),memory.get('npcs',[]),memory.get('places',[]))
    objectives.validate(memory.get('objectives',[]),state,pack)
    validate_discoveries(state,memory,pack)
    world.validate(memory.get('npcs',[]))
    if {npc['id'] for npc in memory.get('npcs',[])}&{actor['id'] for actor in state['characters']}:raise RulePackError('Un personaje jugador no puede convertirse en PNJ')
    if type(memory['revision'])!=int or not 1<=memory['revision']<=1000000:raise RulePackError('Revisión narrativa inválida')
    for key,limit in (('summary',4000),('preparation',6000)):
        if not isinstance(memory[key],str) or not memory[key].strip() or len(memory[key])>limit:raise RulePackError('Memoria narrativa fuera de límites')
    pending=memory['pending'];continuation=memory['continuation']
    if pending is not None and continuation is not None:raise RulePackError('No puede haber solicitud y resultado pendientes a la vez')
    if pending is not None:
        _keys(pending,('id','character','action','inputs','rolls','reason','packageSha256','sheetRevision'),('objectiveCheck','discoveryBindings','targetBinding'))
        expected=discoveries.bindings(memory['discoveries']['catalog'],pending.get('objectiveCheck'),pending['id']) if 'discoveries' in memory else []
        if pending.get('discoveryBindings',[])!=expected:raise RulePackError('Vínculos de descubrimiento de la solicitud incompatibles')
        if 'objectiveCheck' in pending:objectives.check_spec(pending['objectiveCheck'],pending['action'],memory.get('objectives',[]),pack.document())
        if not isinstance(pending['id'],str) or not 1<=len(pending['id'])<=100 or not isinstance(pending['reason'],str) or not 1<=len(pending['reason'])<=600:raise RulePackError('Solicitud narrativa inválida')
        actor=next((c for c in state['characters'] if c['id']==pending['character']),None)
        if actor is None or pending['packageSha256']!=pack.digest or type(pending['sheetRevision'])!=int or pending['sheetRevision']!=actor['sheet']['revision']:raise RulePackError('Solicitud vinculada a otra ficha o reglas')
        if not isinstance(pending['action'],str) or pending['action'] not in pack.document()['actions'] or pack.document()['actions'][pending['action']].get('permission','owner')!='owner':raise RulePackError('La solicitud no puede ejecutar herramientas del anfitrión')
        if 'targetBinding' in pending:
            from target_actions import check_pending
            check_pending(state,pending,{'id':actor['owner']},pack)
            preview={'rolls':pending['rolls']}
        else:preview=pack.preview(actor['sheet'],pending['action'],pending['inputs'],actor['owner'])
        if director.canonical(pending['rolls'])!=director.canonical(preview['rolls']):raise RulePackError('Los dados previstos no coinciden con la ficha y las reglas')
    if continuation is not None:
        _keys(continuation,('character','message'));index=continuation['message']
        if type(index)!=int or not 0<=index<len(state['messages']):raise RulePackError('Continuación narrativa sin resultado')
        event=state['messages'][index]
        if event.get('kind')!='pack-action' or event.get('character')!=continuation['character']:raise RulePackError('Continuación narrativa ligada a otro resultado')
        if 'targetResolutions' in state and any(message.get('kind')=='pack-action' for message in state['messages'][index+1:]):
            raise RulePackError('La continuación debe corresponder al último resultado mecánico confirmado')


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


def validate_discoveries(state,memory,pack):
    store=memory.get('discoveries');messages=state['messages']
    if store is None:
        if any('discoveryReveals' in event for event in messages):raise RulePackError('Revelaciones sin catálogo de aventura')
        return
    _keys(store,('catalog','sourceSha256','installedAt','receipts'),('planSha256',))
    if 'planSha256' in store and (not isinstance(store['planSha256'],str) or not re.fullmatch('[a-f0-9]{64}',store['planSha256'])):
        raise RulePackError('Identidad de preparación aportada inválida')
    if 'action-results' not in pack.document()['requires']:raise RulePackError('Descubrimientos sin resultados explícitos de acción')
    catalog=discoveries.validate_shape(store['catalog'])
    source=state.get('adventureSource');reference=state.get('adventureSourceRef')
    origin=source or reference
    if origin is None or store['sourceSha256']!=origin['sha256']:raise RulePackError('Descubrimientos ligados a otra fuente original')
    if source is not None:discoveries.validate(catalog,source['text'])
    index=store['installedAt']
    if type(index)!=int or not 0<=index<len(messages) or messages[index].get('kind')!='system':raise RulePackError('Descubrimientos sin preparación registrada')
    goals={goal['id']:goal for goal in memory.get('objectives',[])}
    for item in catalog['definitions']:
        goal=goals.get(item['objective'])
        field=pack.document()['fields'].get(item['field'])
        if field is None or field['type']!='boolean' or 'initial' not in field:raise RulePackError('Resultado de descubrimiento inválido')
        if goal is None or not goal['known'] or goal['introducedAt']>=index or goal['evidence'] and goal['evidence']['message']<=index:
            raise RulePackError('El descubrimiento necesita un objetivo conocido abierto al prepararlo')
    expected=[]
    for position,event in enumerate(messages):
        proof=event.get('objectiveResolution');receipts=[]
        if position>index and proof is not None:
            check={key:proof[key] for key in ('objective','field')}
            for binding in discoveries.bindings(catalog,check,proof['request']):
                receipt=discoveries.resolve(catalog,binding,proof,position)
                if receipt is not None:receipts.append(receipt)
        if event.get('discoveryReveals',[])!=receipts or 'discoveryReveals' in event and not receipts:
            raise RulePackError('Revelación no respaldada por esa resolución confirmada')
        expected.extend(receipts)
    if store['receipts']!=expected:raise RulePackError('El diario de descubrimientos difiere del registro confirmado')
    discoveries.public_view(catalog,store['receipts'])
