"""Explicit player entry into source-backed prepared PF1 encounters.

Scenario fiction and voluntary NPC choices are original content. Statistics,
initiative and tactics reuse the existing catalog/engine without house rules.
Combat conclusion is deliberately not inferred from narration or zero HP.
"""
import copy
import hashlib
import json
from pathlib import Path
import npc_catalog
import combat
import checks
import game_randomness
import board_scenes
from rule_pack_authoring import canonical

ID='patio-del-peaje'


def participants_present(state,record):
    return all(any(c['id']==identifier and board_scenes.present(state,c) for c in state['characters'])
        for identifier in (record['character'],record['npc']))


def definition(version='1.11.0'):
    if version=='1.11.0':
        return json.loads((Path(__file__).parent/'adventures/pf-patio-del-peaje-1.11.0.json').read_text(encoding='utf-8'))
    if version=='1.10.0':
        return json.loads((Path(__file__).parent/'adventures/pf-patio-del-peaje-1.10.0.json').read_text(encoding='utf-8'))
    if version=='1.9.0':
        return json.loads((Path(__file__).parent/'adventures/pf-patio-del-peaje-1.9.0.json').read_text(encoding='utf-8'))
    if version=='1.8.0':
        return json.loads((Path(__file__).parent/'adventures/pf-patio-del-peaje-1.8.0.json').read_text(encoding='utf-8'))
    files={'1.0.0':'pf-patio-del-peaje.json','1.1.0':'pf-patio-del-peaje-1.1.0.json','1.2.0':'pf-patio-del-peaje-1.2.0.json','1.3.0':'pf-patio-del-peaje-1.3.0.json','1.4.0':'pf-patio-del-peaje-1.4.0.json','1.5.0':'pf-patio-del-peaje-1.5.0.json','1.6.0':'pf-patio-del-peaje-1.6.0.json','1.7.0':'pf-patio-del-peaje-1.7.0.json'}
    if not isinstance(version,str) or version not in files:raise ValueError('Revisión de encuentro no disponible')
    return json.loads((Path(__file__).parent/'adventures'/files[version]).read_text(encoding='utf-8'))


def enter(state,body,me):
    if body.get('type')!='enter_pf_encounter' or set(body)-{'type','encounter','encounterVersion','character','id','version'} or body.get('encounter')!=ID:raise ValueError('Encuentro preparado no disponible')
    if state.get('ruleset','pathfinder-1e')!='pathfinder-1e':raise ValueError('Este encuentro pertenece a Pathfinder primera edición')
    if state.get('mode','solo')!='solo':raise ValueError('Este primer encuentro solo cubre el modo individual')
    if any(state.get(field) for field in ('secrets','directorNotes','directorMemory')):raise ValueError('Conserva la preparación existente del director; este inicio requiere otra campaña nueva')
    if state['board']['active'] or state.get('pfEncounter') or state.get('adventure') or state.get('adventureModule') or state.get('adventureRoute'):
        raise ValueError('Este primer encuentro requiere una campaña nueva sin aventura ni combate iniciados')
    if len(state['characters'])!=1 or state['board']['terrain'] or state['board'].get('order') or state['pending']:
        raise ValueError('Este encuentro requiere un único PJ y un tablero inicial abierto')
    actor=state['characters'][0]
    if actor['id']!=body.get('character') or actor['owner']!=me['id']:raise PermissionError('La entrada corresponde al propietario del personaje')
    if actor.get('enemy') or not actor.get('creation') or actor['creation'].get('manualOverride') or actor['hp']!=actor['maxHp'] or actor.get('conditions','').strip():
        raise ValueError('Selecciona un personaje creado por el asistente, sin heridas ni condiciones, para este recorrido inicial')
    if (actor['x'],actor['y'])!=(0,0):raise ValueError('Este encuentro requiere la posición inicial del personaje; no se teletransportan fichas existentes')
    scenario=definition(body.get('encounterVersion','1.0.0'));npc_catalog.prepare(scenario['npc']['template'],'pathfinder-1e',name=scenario['npc']['name'])
    result=copy.deepcopy(state)
    from engine import apply_action,log
    apply_action(result,{'type':'create_npc',**scenario['npc']},{**me,'host':True})
    npc=result['characters'][-1]
    result['pfEncounter']={'format':'cronicas-pf-encounter-state-1','definition':scenario,
        'sha256':hashlib.sha256(canonical(scenario).encode()).hexdigest(),'character':actor['id'],'npc':npc['id'],'phase':'offered'}
    result['location']=scenario['location']
    if scenario.get('restScope') in ('courtyard-safe-night-1','courtyard-safe-night-2','courtyard-safe-night-3'):
        import pf_night_rest
        if state['worldTime']!='Comienzo de la aventura':raise ValueError('La noche preparada requiere un reloj inicial sin modificaciones')
        result['worldTime']=pf_night_rest.START_TIME
    log(result,scenario['description'])
    state.clear();state.update(result)


def choose(state,body,me):
    if body.get('type')!='choose_pf_encounter' or set(body)-{'type','choice','id','version'} or body.get('choice') not in ('parley','combat'):raise ValueError('Decisión de encuentro no disponible')
    record=state.get('pfEncounter')
    if record is None or record['phase']!='offered' or state['board']['active']:raise ValueError('La elección inicial ya no está disponible')
    if not participants_present(state,record):raise ValueError('La elección corresponde al patio y sus participantes presentes')
    actor=next((c for c in state['characters'] if c['id']==record['character']),None)
    if actor is None or actor['owner']!=me['id']:raise PermissionError('Solo el jugador decide cómo responde su personaje')
    validate_restored(state)
    npc=next(c for c in state['characters'] if c['id']==record['npc'])
    if len(state['characters'])!=2 or state['board']['terrain'] or any(c['hp']!=c['maxHp'] or c.get('conditions','').strip() for c in (actor,npc)) or npc['npcCreation'].get('manualOverride') or actor['creation'].get('manualOverride'):
        raise ValueError('La preparación inicial cambió; no se asume un encuentro verificado con heridas o correcciones')
    result=copy.deepcopy(state)
    from engine import apply_action,log
    if body['choice']=='parley':
        result['pfEncounter']['phase']='agreement';log(result,record['definition']['agreement'])
    else:
        result['pfEncounter']['phase']='combat'
        apply_action(result,{'type':'combat','automateEnemies':True},{**me,'host':True})
    state.clear();state.update(result)


def sync_outcome(state):
    record=state.get('pfEncounter')
    if not record or record['phase']!='combat' or not state['board']['active']:return
    if not participants_present(state,record):return
    actor=next(c for c in state['characters'] if c['id']==record['character'])
    npc=next(c for c in state['characters'] if c['id']==record['npc'])
    if (len(state['characters'])!=2 or not combat.standing(actor) or actor.get('conditions','').strip() or npc.get('conditions','').strip()
        or actor.get('creation',{}).get('manualOverride') or npc.get('npcCreation',{}).get('manualOverride')):return
    status=combat.health_status(npc)
    if status not in ('muerto','inconsciente estable'):return
    state['board']['active']=False;state['board'].pop('autoPaused',None)
    record['phase']='resolved';record['outcome']={'status':'dead' if status=='muerto' else 'stable',
        'hp':npc['hp'],'stable':bool(npc.get('stable',False)),'constitution':npc['abilities'][2],'round':state['board']['round']}
    from engine import log
    log(state,'El enfrentamiento ha cesado. '+npc['name']+': '+status+', PG '+str(npc['hp'])+'. No se recuperan PG ni se avanza tiempo adicional; tú decides qué haces a continuación.',refs=[{'book':'reglas','page':191}])


def resolve_defeat(state):
    """Only this authored NPC ceases violence; dying checks remain PF rules."""
    record=state.get('pfEncounter')
    if not record or record['phase']!='combat' or not state['board']['active'] or len(state['characters'])!=2:return False
    if not participants_present(state,record):return False
    actor=next(c for c in state['characters'] if c['id']==record['character'])
    npc=next(c for c in state['characters'] if c['id']==record['npc'])
    if (combat.standing(actor) or any(c.get('conditions','').strip() for c in (actor,npc)) or state['board']['terrain']
        or actor['creation'].get('manualOverride') or npc['npcCreation'].get('manualOverride')):return False
    from engine import log,advance_turn
    if combat.standing(npc):log(state,record['definition']['defeatPolicy'])
    else:log(state,'No quedan participantes conscientes; se resuelven únicamente sus pruebas de estabilización, sin elegir acciones por el PJ.')
    # No one chooses a player's action. Each failure loses HP; the total bound
    # is below one hour for these prepared participants, so hourly recovery is
    # neither skipped nor approximated by this sequence.
    for _ in range((actor['abilities'][2]+npc['abilities'][2]+2)*len(state['board']['order'])):
        if not any(combat.health_status(c)=='moribundo' for c in (actor,npc)):break
        advance_turn(state)
    if any(combat.health_status(c)=='moribundo' for c in (actor,npc)):raise ValueError('El desenlace excedió el ámbito de estabilización; no se ha confirmado un resultado supuesto')
    record['phase']='defeated'
    record['outcome']={'status':'dead' if combat.health_status(actor)=='muerto' else 'unconscious',
        'hp':actor['hp'],'stable':bool(actor.get('stable',False)),'constitution':actor['abilities'][2],
        'npcHp':npc['hp'],'npcStable':bool(npc.get('stable',False)),'npcConstitution':npc['abilities'][2],'round':state['board']['round']}
    if record['definition'].get('recoveryScope')=='single-unconscious-player-1':
        record['outcome']['assisted']=actor.get('recoveryCare',{}).get('assisted')
    state['board']['active']=False;state['board'].pop('autoPaused',None)
    log(state,'Desenlace del PJ: '+combat.health_status(actor)+', PG '+str(actor['hp'])+'. Se conservan las heridas y la situación; no se presume recuperación ni se eligen acciones mientras está inconsciente.',refs=[{'book':'reglas','page':191}])
    resolve_recovery(state)
    return True


def resolve_recovery(state):
    """Quiet authored scene, one unconscious patient; no player decisions."""
    record=state.get('pfEncounter')
    if record and not participants_present(state,record):return False
    if record and record['definition'].get('recoveryScope')=='shared-patients-1':
        import pf_shared_recovery
        return pf_shared_recovery.apply(state)
    if (not record or record['phase']!='defeated' or state['board']['active'] or record.get('recoveryOutcome') or record.get('recoveryLimit')
        or record['definition'].get('recoveryScope')!='single-unconscious-player-1' or len(state['characters'])!=2
        or state['board']['terrain'] or state['pending'] or any(not e.get('interpreted') for e in state['consequences'])):return False
    actor=next(c for c in state['characters'] if c['id']==record['character'])
    npc=next(c for c in state['characters'] if c['id']==record['npc'])
    if (combat.health_status(actor)!='inconsciente estable' or npc['hp']<0
        or any(c.get('conditions','').strip() for c in (actor,npc))
        or actor['creation'].get('manualOverride') or npc['npcCreation'].get('manualOverride')
        or 'recoveryState' in actor or actor.get('recoveryCare',{}).get('round')!=record['outcome']['round']
        or actor['hp']!=record['outcome']['hp'] or type(record['outcome'].get('assisted'))!=bool
        or actor.get('recoveryCare',{}).get('assisted') is not record['outcome']['assisted']):return False
    import character_builder
    import pf_recovery
    original,_=character_builder.build(actor['creation']['choices'])
    constitution=original['abilities'][2]
    if actor['abilities'][2]!=constitution or constitution>20:return False
    if record['outcome']['assisted']:
        record['recoveryLimit']='assisted-rest'
        from engine import log
        log(state,'No se avanzan horas: la recuperación de este PJ asistido necesita coordinar su descanso y todavía no está cubierta. Se conserva su estado.',refs=[{'book':'reglas','page':192}])
        return False
    if actor['creation']['choices']['armor'] not in ('leather','studded','chainshirt'):
        record['recoveryLimit']='armor-rest'
        from engine import log
        log(state,'No se avanzan horas de recuperación: dormir con armadura intermedia puede causar fatiga y ese descanso todavía requiere una resolución excepcional. Se conservan las heridas y la consciencia actuales.',
            refs=[{'book':'reglas','page':151},{'book':'reglas','page':152}])
        return False
    pf_recovery.validate_restored(state)
    result=copy.deepcopy(state);patient=next(c for c in result['characters'] if c['id']==actor['id'])
    care=patient['recoveryCare']['assisted'];raws=[];hourly=[];before=patient['hp']
    from engine import log
    log(result,record['definition']['recoveryPolicy'])
    for _ in range(constitution):
        raw=game_randomness.draw(20);raws.append(raw);check=pf_recovery.apply_hour(patient,raw)
        hourly.append(check)
        if check['conscious'] or check['dead']:break
    else:raise ValueError('La recuperación excedió el límite; no se confirma un resultado supuesto')
    receipt={'format':'cronicas-pf-recovery-outcome-1','fromHp':before,'hp':patient['hp'],
        'constitution':constitution,'assisted':care,'dice':raws,'hours':len(raws),'seconds':len(raws)*3600,
        'status':'conscious' if check['conscious'] else 'dead','worldTimeBefore':state['worldTime']}
    result['pfEncounter']['recoveryOutcome']=receipt
    result['worldTime']=str(receipt['hours'])+' hora'+('s' if receipt['hours']!=1 else '')+' después del enfrentamiento en el patio'
    log(result,result['worldTime']+': '+('recupera la consciencia sin curación' if check['conscious'] else 'muere por sus heridas')+', PG '+str(patient['hp'])+'.',
        check={'kind':'recovery','character':patient['id'],'hours':receipt['hours'],'hp':patient['hp'],'status':receipt['status']},
        recoveryChecks=hourly,refs=[{'book':'reglas','page':191},{'book':'reglas','page':192}])
    state.clear();state.update(result);return True


def aid_or_wait(state,body,me):
    if body.get('type') not in ('pf_first_aid','pf_wait_stabilization') or set(body)-{'type','physical','id','version'}:raise ValueError('Decisión de asistencia no disponible')
    if body['type']=='pf_wait_stabilization' and 'physical' in body:raise ValueError('La espera utiliza las pruebas de estabilización del motor')
    record=state.get('pfEncounter')
    if not record or record['phase']!='combat' or not state['board']['active']:raise ValueError('No hay un desenlace pendiente de este encuentro')
    validate_restored(state)
    actor=next(c for c in state['characters'] if c['id']==record['character'])
    patient=next(c for c in state['characters'] if c['id']==record['npc'])
    board_scenes.require_present(state,actor,patient)
    if actor['owner']!=me['id']:raise PermissionError('Solo el jugador decide si presta auxilio o espera')
    if (len(state['characters'])!=2 or not combat.standing(actor) or any(c.get('conditions','').strip() for c in (actor,patient))
        or state['board']['terrain'] or actor['creation'].get('manualOverride') or patient['npcCreation'].get('manualOverride')):
        raise ValueError('Este auxilio solo cubre los participantes preparados y conscientes, sin condiciones ni terreno especial')
    if state['board']['order'][state['board']['turn']]['id']!=actor['id']:raise ValueError('Espera al turno de tu personaje')
    if combat.health_status(patient)!='moribundo':raise ValueError('El paciente ya no necesita estabilización en este bloque')
    result=copy.deepcopy(state)
    helper=next(c for c in result['characters'] if c['id']==actor['id'])
    target=next(c for c in result['characters'] if c['id']==patient['id'])
    from engine import log,advance_turn,run_automatic_turns
    if body['type']=='pf_first_aid':
        if 'physical' in body and not me['host']:raise PermissionError('En esta mesa el anfitrión registra los dados físicos, como en las demás pruebas Pathfinder')
        if max(abs(helper['x']-target['x']),abs(helper['y']-target['y']))!=1:raise ValueError('Este bloque de primeros auxilios requiere un paciente adyacente')
        spent=result['board']['spent'].get(helper['id'],{})
        if spent.get('standard') or helper['hp']<=0 and spent.get('move'):raise ValueError('No queda la acción estándar necesaria para primeros auxilios')
        # Validate the prepared skill and physical die before any RNG.
        checks.modifier(helper,'skill','Curar')
        if 'physical' in body:checks.integer(body['physical'],1,20)
        die=body['physical'] if 'physical' in body else game_randomness.draw(20)
        resolved=checks.resolve(helper,'skill','Curar',die,15)
        result['board']['spent'].setdefault(helper['id'],{})['standard']=True
        if resolved['success']:
            import pf_recovery
            pf_recovery.record_stabilization(target,assisted=True,round_number=result['board']['round'],initiative=helper['id'],order=[entry['id'] for entry in result['board']['order']],epoch=result['board'].get('combatSerial'))
        if helper['hp']<=0:
            import pf_recovery
            helper['hp']-=1;helper['stable']=False;pf_recovery.clear_episode(helper)
        log(result,helper['name']+': primeros auxilios, d20 '+str(die)+' '+str(resolved['modifier'])+' = '+str(resolved['total'])+' contra CD15. '+('El paciente queda estable sin recuperar PG.' if resolved['success'] else 'El paciente sigue moribundo; no se aplica daño adicional por fallar.'),
            check=resolved|{'patient':target['id']},refs=[{'book':'reglas','page':93},{'book':'reglas','page':94},{'book':'reglas','page':191}])
    else:
        log(result,helper['name']+': decide esperar sin prestar auxilio hasta que el paciente se estabilice o muera.')
        # Each failed check loses HP, so this bounded loop must reach a terminal
        # health state. It never chooses an action for the conscious player.
        for _ in range(target['abilities'][2]+1):
            if combat.health_status(target)!='moribundo':break
            advance_turn(result);run_automatic_turns(result)
        if combat.health_status(target)=='moribundo':raise ValueError('La estabilización excedió el límite; no se ha confirmado una espera parcial')
    sync_outcome(result);resolve_defeat(result);state.clear();state.update(result)


def validate_restored(state):
    record=state.get('pfEncounter')
    import pf_ceasefire
    import pf_npc_wait
    if record is None:
        pf_ceasefire.validate_restored(state)
        pf_npc_wait.validate_restored(state)
        return
    fields={'format','definition','sha256','character','npc','phase'}
    if isinstance(record,dict) and record.get('phase') in ('resolved','defeated'):fields.add('outcome')
    if isinstance(record,dict) and 'recoveryOutcome' in record:fields.add('recoveryOutcome')
    if isinstance(record,dict) and 'recoveryLimit' in record:fields.add('recoveryLimit')
    if isinstance(record,dict) and 'recoveryStart' in record:fields.add('recoveryStart')
    if isinstance(record,dict) and 'ceasefire' in record:fields.add('ceasefire')
    if isinstance(record,dict) and 'npcRecovery' in record:fields.add('npcRecovery')
    if (state.get('ruleset','pathfinder-1e')!='pathfinder-1e' or not isinstance(record,dict)
        or set(record)!=fields
        or record['format']!='cronicas-pf-encounter-state-1' or record['phase'] not in ('offered','agreement','combat','resolved','defeated')):
        raise ValueError('Estado de encuentro Pathfinder inválido')
    # This first authored version is fixed. Do not silently reinterpret a copy.
    if (not isinstance(record['definition'],dict) or canonical(record['definition'])!=canonical(definition(record['definition'].get('version')))
        or record['sha256']!=hashlib.sha256(canonical(record['definition']).encode()).hexdigest()):
        raise ValueError('El encuentro requiere otra definición o revisión')
    actor=next((c for c in state['characters'] if c['id']==record['character']),None)
    npc=next((c for c in state['characters'] if c['id']==record['npc']),None)
    if actor is None or actor.get('enemy') or not actor.get('creation') or npc is None or npc.get('npcCreation',{}).get('template')!=record['definition']['npc']['template']:
        raise ValueError('El encuentro no está vinculado a sus participantes preparados')
    npc_catalog.validate_character(npc,'pathfinder-1e')
    pf_ceasefire.validate_restored(state)
    pf_npc_wait.validate_restored(state)
    here=participants_present(state,record)
    if record['phase']=='offered' and not here:raise ValueError('La escena ofrecida requiere sus participantes presentes')
    if record['phase'] in ('offered','agreement') and state['board']['active'] and here:raise ValueError('La fase del encuentro contradice el combate activo')
    if record['phase']=='resolved':
        outcome=record['outcome']
        if (not isinstance(outcome,dict) or set(outcome)!={'status','hp','stable','constitution','round'}
            or type(outcome['hp'])!=int or not -10000<=outcome['hp']<0 or type(outcome['stable'])!=bool
            or type(outcome['constitution'])!=int
            or type(outcome['round'])!=int or not 1<=outcome['round']<=1000000):raise ValueError('Desenlace de encuentro inválido')
        original,_=npc_catalog.prepare(record['definition']['npc']['template'],'pathfinder-1e')
        if outcome['constitution']!=original['abilities'][2]:raise ValueError('El desenlace requiere su Constitución original verificada')
        dead=outcome['hp']<=-outcome['constitution']
        if outcome['status']!=('dead' if dead else 'stable') or not dead and not outcome['stable']:raise ValueError('El desenlace no corresponde a muerte o estabilización verificables')
        if state['board']['active'] and here:raise ValueError('Un encuentro resuelto no conserva combate activo')
    if record['phase']=='defeated':
        outcome=record['outcome']
        outcome_fields={'status','hp','stable','constitution','npcHp','npcStable','npcConstitution','round'}
        if record['definition'].get('recoveryScope')=='single-unconscious-player-1':outcome_fields.add('assisted')
        if (not isinstance(outcome,dict) or set(outcome)!=outcome_fields
            or type(outcome['hp'])!=int or not -10000<=outcome['hp']<0 or type(outcome['stable'])!=bool
            or type(outcome['constitution'])!=int or type(outcome['npcHp'])!=int or not -10000<=outcome['npcHp']<=10000
            or type(outcome['npcStable'])!=bool or type(outcome['npcConstitution'])!=int
            or type(outcome['round'])!=int or not 1<=outcome['round']<=1000000):raise ValueError('Desenlace de derrota inválido')
        import character_builder
        original,_=character_builder.build(actor['creation']['choices'])
        if outcome['constitution']!=original['abilities'][2]:raise ValueError('La derrota requiere la Constitución verificada del PJ')
        dead=outcome['hp']<=-outcome['constitution']
        if 'assisted' in outcome and outcome['assisted'] is not None and (type(outcome['assisted'])!=bool or dead or not outcome['stable']):
            raise ValueError('Asistencia de desenlace inválida')
        if outcome['status']!=('dead' if dead else 'unconscious') or not dead and not outcome['stable']:raise ValueError('La derrota no corresponde al estado verificado del PJ')
        original_npc,_=npc_catalog.prepare(record['definition']['npc']['template'],'pathfinder-1e')
        if outcome['npcHp']>original_npc['maxHp']:raise ValueError('Los PG del desenlace superan el perfil original del PNJ')
        if outcome['npcConstitution']!=original_npc['abilities'][2]:raise ValueError('La derrota requiere la Constitución verificada del PNJ')
        if -outcome['npcConstitution']<outcome['npcHp']<0 and not outcome['npcStable']:raise ValueError('No se omite un PNJ todavía moribundo')
        if state['board']['active'] and here:raise ValueError('La derrota registrada no conserva combate activo')
    if record['definition'].get('recoveryScope')=='shared-patients-1':
        import pf_shared_recovery
        if record.get('recoveryLimit')=='armor-rest' and actor['creation']['choices']['armor']!='scale':raise ValueError('El límite de armadura no corresponde al PJ')
        pf_shared_recovery.validate_record(record);return
    if 'recoveryStart' in record:raise ValueError('Este encuentro no admite reloj compartido')
    if 'recoveryLimit' in record:
        if (record['phase']!='defeated' or record['definition'].get('recoveryScope')!='single-unconscious-player-1'
            or record['recoveryLimit'] not in ('armor-rest','assisted-rest') or 'recoveryOutcome' in record
            or record['recoveryLimit']=='armor-rest' and actor['creation']['choices']['armor']!='scale'
            or record['recoveryLimit']=='assisted-rest' and record['outcome']['assisted'] is not True):
            raise ValueError('Límite de recuperación inválido')
    if 'recoveryOutcome' in record:
        import pf_recovery
        receipt=record['recoveryOutcome']
        if (record['phase']!='defeated' or record['definition'].get('recoveryScope')!='single-unconscious-player-1'
            or not isinstance(receipt,dict) or set(receipt)!={'format','fromHp','hp','constitution','assisted','dice','hours','seconds','status','worldTimeBefore'}
            or receipt['format']!='cronicas-pf-recovery-outcome-1' or type(receipt['assisted'])!=bool
            or receipt['assisted'] is not record['outcome']['assisted']
            or type(receipt['fromHp'])!=int or receipt['fromHp']!=record['outcome']['hp']
            or type(receipt['hp'])!=int or type(receipt['constitution'])!=int or receipt['constitution']!=record['outcome']['constitution']
            or type(receipt['hours'])!=int or not 1<=receipt['hours']<=20 or type(receipt['seconds'])!=int
            or receipt['seconds']!=receipt['hours']*3600 or not isinstance(receipt['dice'],list)
            or len(receipt['dice'])!=receipt['hours'] or not isinstance(receipt['worldTimeBefore'],str)):
            raise ValueError('Desenlace horario inválido')
        patient={'hp':receipt['fromHp'],'abilities':[10,10,receipt['constitution'],10,10,10],'stable':True}
        for index,raw in enumerate(receipt['dice']):
            check=pf_recovery.consciousness_check(patient,raw,assisted=receipt['assisted']);patient['hp']=check['hpAfter']
            if (check['conscious'] or check['dead']) and index!=len(receipt['dice'])-1:raise ValueError('No se repite una recuperación ya determinada')
        if not (check['conscious'] or check['dead']) or receipt['hp']!=patient['hp'] or receipt['status']!=('conscious' if check['conscious'] else 'dead'):
            raise ValueError('El desenlace horario no coincide con sus dados y heridas')
