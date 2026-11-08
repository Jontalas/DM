"""Owner-chosen bounded wait for one stable NPC, Core PDF191-192.

No sleep, healing or decisions for the PC. The six-check boundary is coverage,
not a Pathfinder rule. Unknown rest/concurrent effects remain unsupported.
"""
import copy
import hashlib
import pf_recovery
import pf_timeline
from rule_pack_authoring import canonical

SCOPE='npc-consciousness-wait-1'
FORMAT='cronicas-pf-npc-recovery-wait-1'


def supported(definition):return isinstance(definition,dict) and definition.get('npcWaitScope')==SCOPE


def _patient(start):
    if (not isinstance(start,dict) or set(start)!={'epoch','round','initiative','order','character','actorHp','npc'}
        or start['epoch']!=1 or type(start['epoch'])!=int or type(start['round'])!=int or not 1<=start['round']<600
        or not isinstance(start['order'],list) or len(start['order'])!=2 or any(not isinstance(v,str) for v in start['order'])
        or len(set(start['order']))!=2 or start['initiative'] not in start['order'] or start['character'] not in start['order']
        or type(start['actorHp'])!=int or not 1<=start['actorHp']<=10000 or not isinstance(start['npc'],dict)
        or set(start['npc'])!={'id','hp','constitution','care'}):raise ValueError('Inicio de espera médica inválido')
    row=start['npc'];care=row['care']
    if (row['id'] not in start['order'] or row['id']==start['character'] or type(row['hp'])!=int
        or type(row['constitution'])!=int or not 1<=row['constitution']<=60 or not -row['constitution']<row['hp']<0
        or not isinstance(care,dict) or care.get('format')!='cronicas-pf-care-3'
        or care.get('epoch')!=start['epoch'] or care.get('order')!=start['order']):raise ValueError('La espera necesita asistencia y reloj conocidos')
    patient={'id':row['id'],'hp':row['hp'],'abilities':[10,10,row['constitution'],10,10,10],'stable':True,'conditions':'','recoveryCare':copy.deepcopy(care)}
    pf_recovery.validate_restored({'characters':[patient],'board':{'combatSerial':1}})
    origin=(care['round'],start['order'].index(care['initiative']));clock=(start['round'],start['order'].index(start['initiative']))
    if not origin<=clock<(origin[0]+600,origin[1]):raise ValueError('La espera no puede omitir una comprobación ya debida')
    return patient


def simulate(start,draw):
    patient=_patient(start);dice=[];audit=[];clock=(start['round'],start['order'].index(start['initiative']))
    for hour in range(1,7):
        event=pf_recovery.next_hourly_events([patient])[0];due=(event['round'],event['orderIndex'])
        if due<clock:raise ValueError('La espera no puede retroceder')
        raw=draw();check=pf_recovery.apply_hour(patient,raw);dice.append(raw);audit.append({'hour':hour,'round':event['round'],'initiative':event['initiative'],**check});clock=due
        if patient['hp']<=-patient['abilities'][2]:status='dead';break
        if pf_recovery.is_conscious(patient):status='conscious';break
    else:status='limit'
    begin=(start['round'],start['order'].index(start['initiative']))
    elapsed=pf_timeline.elapsed_seconds(begin,clock) if begin[1]==clock[1] else None
    return {'patient':patient,'dice':dice,'audit':audit,'status':status,'hours':len(dice),
        'end':{'round':clock[0],'initiative':start['order'][clock[1]]},'elapsedSeconds':elapsed,'secondsSinceStabilization':len(dice)*3600}


def limitation(state):
    record=state.get('pfEncounter') or {};board=state['board']
    if not supported(record.get('definition')):return 'Esta escena no incluye la espera preparada.'
    if record.get('npcRecovery'):return 'La espera preparada ya está registrada.'
    if record.get('phase')!='resolved' or board['active']:return 'Resuelve primero el enfrentamiento y la estabilización.'
    actors={c['id']:c for c in state['characters']};actor=actors.get(record['character']);npc=actors.get(record['npc'])
    import board_scenes
    if len(actors)!=2 or not actor or not npc or not all(board_scenes.present(state,c) for c in (actor,npc)):return 'La espera requiere a ambos participantes presentes.'
    if actor['hp']<=0:return 'Esta espera preparada requiere que tu personaje tenga PG positivos.'
    if not -npc['abilities'][2]<npc['hp']<0 or npc.get('stable') is not True:return 'La guardiana debe estar viva, estable y con PG negativos.'
    if npc.get('recoveryState'):return 'La recuperación ya ha comenzado; esta espera no sustituye su historial.'
    if (any(c.get('conditions','').strip() or c.get('creation',{}).get('manualOverride') or c.get('npcCreation',{}).get('manualOverride') for c in (actor,npc))
        or board['terrain'] or state['pending'] or any(not e.get('interpreted') for e in state['consequences'])):return 'Resuelve las condiciones o situaciones pendientes antes de esperar.'
    if state['location']!=record['definition']['location'] or state.get('pfContinuation'):return 'La espera corresponde al patio antes de investigar.'
    try:_patient(_snapshot(state))
    except (ValueError,KeyError,IndexError,TypeError):return 'La espera necesita el reloj del primer combate corto, sin horas pendientes.'
    return None


def _snapshot(state):
    record=state['pfEncounter'];board=state['board'];actor=next(c for c in state['characters'] if c['id']==record['character']);npc=next(c for c in state['characters'] if c['id']==record['npc'])
    return {'epoch':board.get('combatSerial'),'round':board['round'],'initiative':board['order'][board['turn']]['id'],
        'order':[v['id'] for v in board['order']],'character':actor['id'],'actorHp':actor['hp'],
        'npc':{'id':npc['id'],'hp':npc['hp'],'constitution':npc['abilities'][2],'care':copy.deepcopy(npc.get('recoveryCare'))}}


def _receipt(record,start,result,world_time):
    return {'format':FORMAT,'encounterSha256':record['sha256'],'start':copy.deepcopy(start),'dice':result['dice'][:],
        'status':result['status'],'hours':result['hours'],'npcHp':result['patient']['hp'],'end':result['end'],
        'elapsedSeconds':result['elapsedSeconds'],'secondsSinceStabilization':result['secondsSinceStabilization'],'worldTimeBefore':world_time}


def wait(state,body,me):
    if body.get('type')!='wait_pf_npc_recovery' or set(body)-{'type','id','version'}:raise ValueError('Elige esperar sin añadir consecuencias')
    import pf_encounters
    pf_encounters.validate_restored(state)
    record=state.get('pfEncounter') or {};actor=next((c for c in state['characters'] if c['id']==record.get('character')),None)
    if not actor or actor['owner']!=me['id']:raise PermissionError('Solo el propietario decide si su personaje espera')
    reason=limitation(state)
    if reason:raise ValueError(reason)
    import game_randomness
    start=_snapshot(state);result=simulate(start,lambda:game_randomness.draw(20));updated=copy.deepcopy(state)
    target=next(c for c in updated['characters'] if c['id']==record['npc'])
    for key in ('hp','stable','recoveryCare','recoveryState'):
        if key in result['patient']:target[key]=copy.deepcopy(result['patient'][key])
        else:target.pop(key,None)
    receipt=_receipt(record,start,result,state['worldTime']);updated['pfEncounter']['npcRecovery']=receipt
    updated['worldTime']=str(result['hours'])+' hora'+('s' if result['hours']!=1 else '')+' desde la estabilización de la guardiana'
    from engine import log
    outcome='La guardiana ha despertado; sigue herida y permanece sentada y despierta.' if result['status']=='conscious' else 'La guardiana ha muerto por sus heridas.' if result['status']=='dead' else 'La espera se detiene antes de un descanso todavía no cubierto; sigue inconsciente y estable.'
    log(updated,updated['worldTime']+'. '+outcome+' Tu personaje no ha dormido ni recuperado PG. Tú decides cómo continuar.',
        npcRecoverySha256=hashlib.sha256(canonical(receipt).encode()).hexdigest(),recoveryChecks=result['audit'],refs=[{'book':'reglas','page':191},{'book':'reglas','page':192}])
    validate_restored(updated);pf_recovery.validate_restored(updated);state.clear();state.update(updated)


def validate_restored(state):
    record=state.get('pfEncounter') or {};record=record if isinstance(record,dict) else {}
    receipt=record.get('npcRecovery');markers=[m['npcRecoverySha256'] for m in state.get('messages',[]) if 'npcRecoverySha256' in m]
    if receipt is None:
        if markers:raise ValueError('Falta la espera médica registrada')
        return None
    fields={'format','encounterSha256','start','dice','status','hours','npcHp','end','elapsedSeconds','secondsSinceStabilization','worldTimeBefore'}
    if (not supported(record.get('definition')) or not isinstance(receipt,dict) or set(receipt)!=fields or receipt['format']!=FORMAT
        or receipt['encounterSha256']!=record.get('sha256') or not isinstance(receipt['dice'],list) or not 1<=len(receipt['dice'])<=6
        or not isinstance(receipt['worldTimeBefore'],str) or record.get('phase')=='offered'):raise ValueError('La espera no corresponde a este encuentro')
    start=receipt['start'];_patient(start)
    if start['character']!=record.get('character') or start['npc']['id']!=record.get('npc') or state['board'].get('combatSerial',0)<1:raise ValueError('La espera no corresponde a sus participantes')
    import npc_catalog
    original,_=npc_catalog.prepare(record['definition']['npc']['template'],'pathfinder-1e')
    if start['npc']['constitution']!=original['abilities'][2]:raise ValueError('La espera necesita la Constitución original')
    if record.get('phase')=='resolved' and state['board'].get('combatSerial')==1:
        outcome=record.get('outcome') or {}
        if start['npc']['hp']!=outcome.get('hp') or outcome.get('status')!='stable':raise ValueError('La espera no parte del desenlace estabilizado')
    index=0
    def replay():
        nonlocal index
        if index>=len(receipt['dice']):raise ValueError('Faltan pruebas de la espera')
        raw=receipt['dice'][index];index+=1;return raw
    result=simulate(start,replay)
    if index!=len(receipt['dice']) or canonical(receipt)!=canonical(_receipt(record,start,result,receipt['worldTimeBefore'])) or markers!=[hashlib.sha256(canonical(receipt).encode()).hexdigest()]:raise ValueError('La espera no coincide con sus comprobaciones')
    return result


def can_remain_awake(state,character):
    record=state.get('pfEncounter') or {}
    if (record.get('phase')!='resolved' or state['board'].get('combatSerial')!=1 or character.get('id')!=record.get('npc')
        or not supported(record.get('definition')) or not record.get('npcRecovery') or character.get('conditions','').strip()
        or character.get('npcCreation',{}).get('manualOverride')):return False
    try:result=validate_restored(state);pf_recovery.validate_restored({'characters':[character],'board':state['board']})
    except (ValueError,KeyError,TypeError):return False
    return result['status']=='conscious' and all(character.get(k)==result['patient'].get(k) for k in ('hp','stable','recoveryCare','recoveryState'))


def public_view(state):
    record=state.get('pfEncounter') or {}
    if not supported(record.get('definition')):return None
    receipt=record.get('npcRecovery')
    npc=next((c for c in state['characters'] if c['id']==record['npc']),{})
    result=validate_restored(state) if receipt else None
    current=bool(result and record.get('phase')=='resolved' and state['board'].get('combatSerial')==1
        and all(npc.get(k)==result['patient'].get(k) for k in ('hp','stable','recoveryCare','recoveryState')))
    return {'reason':limitation(state),'assisted':bool(npc.get('recoveryCare',{}).get('assisted')),
        'result':{k:receipt[k] for k in ('status','hours','npcHp')} if receipt else None,
        'currentResult':current,'canContinue':current and can_remain_awake(state,npc)}
