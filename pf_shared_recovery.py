"""Bounded shared recovery clock, PF Core PDF179/191-192.

Pure simulation. No campaign mutation, IO, narration or player decisions.
An assisted unconscious NPC stops the clock at the six-hour coverage boundary,
before any eight-hour rest might become due in the supported short encounter.
That boundary is an engine limitation, not a Pathfinder rule.
"""
import copy
import pf_recovery
import game_randomness

SCOPE='shared-patients-1'


class CoverageLimit(ValueError):
    def __init__(self,code):
        self.code=code
        super().__init__('La recuperación compartida necesita resolver '+code)


def _participants(start):
    if not isinstance(start,dict) or set(start)!={'epoch','round','initiative','order','patients'}:
        raise ValueError('Inicio de reloj compartido inválido')
    if type(start['epoch'])!=int or not 1<=start['epoch']<=1000000 or type(start['round'])!=int or not 1<=start['round']<=1000000:
        raise ValueError('Época o ronda compartida inválida')
    rows=start['patients'];order=start['order']
    if not isinstance(rows,list) or len(rows)!=2 or not isinstance(order,list) or len(order)!=2 or any(not isinstance(v,str) for v in order) or len(set(order))!=2 or start['initiative'] not in order:
        raise ValueError('Participantes de reloj compartido inválidos')
    result=[]
    for row in rows:
        if (not isinstance(row,dict) or set(row)!={'id','hp','constitution','stable','care'}
            or not isinstance(row['id'],str) or row['id'] not in order or type(row['hp'])!=int
            or not -10000<=row['hp']<=10000 or type(row['constitution'])!=int or not 1<=row['constitution']<=60
            or type(row['stable'])!=bool):raise ValueError('Paciente de reloj compartido inválido')
        patient={'id':row['id'],'hp':row['hp'],'abilities':[10,10,row['constitution'],10,10,10],'stable':row['stable']}
        if row['care'] is not None:patient['recoveryCare']=copy.deepcopy(row['care'])
        result.append(patient)
    if result[0]['id']==result[1]['id']:raise ValueError('El reloj requiere dos participantes distintos')
    pf_recovery.validate_restored({'characters':result,'board':{'combatSerial':start['epoch']}})
    player=result[0]
    if not -player['abilities'][2]<player['hp']<0 or player['stable'] is not True:raise CoverageLimit('player-state')
    if player['abilities'][2]>20:raise CoverageLimit('profile')
    closure=(start['round'],order.index(start['initiative']))
    for patient in result:
        if patient['hp']>=0 or patient['hp']<=-patient['abilities'][2]:continue
        care=patient.get('recoveryCare',{})
        if care.get('format')!='cronicas-pf-care-3' or care['epoch']!=start['epoch'] or care['order']!=order:
            raise CoverageLimit('unverified-clock')
        if (care['round'],order.index(care['initiative']))>closure:raise ValueError('La asistencia no puede proceder del futuro')
        if (care['round']+600,order.index(care['initiative']))<=closure:raise CoverageLimit('overdue-events')
    if player['recoveryCare']['assisted']:raise CoverageLimit('assisted-player-rest')
    npc=result[1]
    if -npc['abilities'][2]<npc['hp']<0 and (start['epoch']!=1 or start['round']>=600):
        raise CoverageLimit('extended-encounter')
    return result


def simulate(start,draw):
    """draw(role) returns one d20. role0 is PC, role1 is NPC."""
    patients=_participants(start);player,npc=patients;order=start['order']
    care=player['recoveryCare'];origin=(care['round'],order.index(care['initiative']))
    horizon=(origin[0]+3600,origin[1]);clock=(start['round'],order.index(start['initiative']))
    ledger=[];audit=[];roles={p['id']:i for i,p in enumerate(patients)}
    for _ in range(44):
        if pf_recovery.is_conscious(player):status='conscious';break
        if player['hp']<=-player['abilities'][2]:status='dead';break
        assisted_npc=(-npc['abilities'][2]<npc['hp']<0 and not pf_recovery.is_conscious(npc)
            and npc.get('recoveryCare',{}).get('assisted') is True)
        if assisted_npc and clock>=horizon:status='rest-boundary';break
        events=pf_recovery.next_hourly_events(patients)
        if not events:raise ValueError('No hay una próxima prueba verificable para el jugador inconsciente')
        due=(events[0]['round'],events[0]['orderIndex'])
        if due<clock:raise ValueError('El reloj no puede retroceder')
        # Resolve every event at the same instant, even if the PC wakes/dies
        # during that group. Do not process another participant's future event.
        for event in events:
            role=roles[event['character']];patient=patients[role]
            hour=patient.get('recoveryState',{}).get('hours',0)+1
            raw=draw(role);check=pf_recovery.apply_hour(patient,raw)
            ledger.append([role,raw]);audit.append({'role':role,'hour':hour,'round':event['round'],
                'initiative':event['initiative'],**check})
        clock=due
    else:raise ValueError('El reloj compartido superó su límite sin un resultado verificable')
    if clock[1]!=origin[1]:raise ValueError('No se convierte una fracción de iniciativa en segundos inventados')
    elapsed=(clock[0]-origin[0])*6
    return {'patients':patients,'rolls':ledger,'audit':audit,'status':status,'seconds':elapsed,'hours':elapsed//3600}


def _snapshot(state,record):
    board=state['board'];rows=[]
    for identifier in (record['character'],record['npc']):
        c=next(c for c in state['characters'] if c['id']==identifier)
        if c.get('recoveryState'):raise CoverageLimit('existing-recovery')
        rows.append({'id':c['id'],'hp':c['hp'],'constitution':c['abilities'][2],
            'stable':bool(c.get('stable',False)),'care':copy.deepcopy(c.get('recoveryCare'))})
    if not board.get('combatSerial'):raise CoverageLimit('unverified-clock')
    return {'epoch':board['combatSerial'],'round':board['round'],'initiative':board['order'][board['turn']]['id'],
        'order':[v['id'] for v in board['order']],'patients':rows}


def _receipt(start,result,world_time):
    player,npc=result['patients']
    return {'format':'cronicas-pf-recovery-outcome-2','fromHp':start['patients'][0]['hp'],'hp':player['hp'],
        'constitution':player['abilities'][2],'assisted':False,'dice':[raw for role,raw in result['rolls'] if role==0],
        'hours':result['hours'],'seconds':result['seconds'],'status':result['status'],'npcHp':npc['hp'],
        'rolls':result['rolls'],'worldTimeBefore':world_time}


def apply(state):
    """Called only by the prepared encounter after both dying states resolve."""
    record=state.get('pfEncounter')
    if not record or record['definition'].get('recoveryScope')!=SCOPE or record['phase']!='defeated' or state['board']['active'] or record.get('recoveryOutcome') or record.get('recoveryLimit'):return False
    if len(state['characters'])!=2 or state['board']['terrain'] or state['pending'] or any(not e.get('interpreted') for e in state['consequences']):return False
    actor=next(c for c in state['characters'] if c['id']==record['character']);npc=next(c for c in state['characters'] if c['id']==record['npc'])
    if (pf_recovery.is_conscious(actor) or actor['hp']<=-actor['abilities'][2] or actor.get('stable') is not True
        or any(c.get('conditions','').strip() for c in (actor,npc)) or actor['creation'].get('manualOverride') or npc['npcCreation'].get('manualOverride')):return False
    from engine import log
    import character_builder
    original,_=character_builder.build(actor['creation']['choices'])
    if actor['abilities'][2]!=original['abilities'][2]:return False
    if actor['creation']['choices']['armor'] not in ('leather','studded','chainshirt'):
        record['recoveryLimit']='armor-rest'
        log(state,'No se avanzan horas: la recuperación con esta armadura requiere efectos de descanso aún no cubiertos.',refs=[{'book':'reglas','page':151}]);return False
    try:
        start=_snapshot(state,record);_participants(start)
    except CoverageLimit as error:
        record['recoveryLimit']='shared-'+error.code
        log(state,'No se avanza la recuperación compartida: el estado necesita una resolución fuera del alcance actual. Se conservan las heridas y el tiempo.');return False
    result=simulate(start,lambda role:game_randomness.draw(20))
    updated=copy.deepcopy(state);target_record=updated['pfEncounter']
    for role,patient in enumerate(result['patients']):
        if not any(rolled_role==role for rolled_role,raw in result['rolls']):continue
        target=next(c for c in updated['characters'] if c['id']==patient['id'])
        for key in ('hp','stable','recoveryCare','recoveryState'):
            if key in patient:target[key]=copy.deepcopy(patient[key])
            else:target.pop(key,None)
    target_record['recoveryStart']=start;target_record['recoveryOutcome']=_receipt(start,result,state['worldTime'])
    if result['status']=='rest-boundary':target_record['recoveryLimit']='shared-rest-boundary'
    updated['worldTime']=str(result['hours'])+' hora'+('s' if result['hours']!=1 else '')+' desde la estabilización del personaje'
    log(updated,record['definition']['recoveryPolicy'])
    names={0:actor['name'],1:npc['name']}
    audit=[{**check,'characterName':names[check['role']]} for check in result['audit']]
    text=('El personaje recupera la consciencia sin curación.' if result['status']=='conscious' else
        'El personaje muere por sus heridas.' if result['status']=='dead' else 'La recuperación se detiene antes de un descanso todavía no cubierto.')
    log(updated,updated['worldTime']+'. '+text+' PG '+str(result['patients'][0]['hp'])+'.',
        check={'kind':'recovery','character':actor['id'],'hours':result['hours'],'hp':result['patients'][0]['hp'],'status':result['status']},
        recoveryChecks=audit,refs=[{'book':'reglas','page':179},{'book':'reglas','page':191},{'book':'reglas','page':192}])
    state.clear();state.update(updated);return True


def validate_record(record):
    """Replay compact role/die ledger; never use provider or fresh RNG."""
    temporal={'recoveryStart','recoveryOutcome','recoveryLimit'}&set(record)
    if record['phase']!='defeated':
        if temporal:raise ValueError('Recuperación compartida fuera del desenlace')
        return
    if 'recoveryOutcome' not in record:
        if 'recoveryStart' in record:raise ValueError('Reloj compartido sin su resultado')
        limit=record.get('recoveryLimit')
        if limit is not None and limit not in ('armor-rest','shared-player-state','shared-profile','shared-unverified-clock',
            'shared-assisted-player-rest','shared-extended-encounter','shared-existing-recovery','shared-overdue-events'):
            raise ValueError('Límite de reloj compartido inválido')
        return
    start=record.get('recoveryStart');receipt=record['recoveryOutcome'];outcome=record['outcome']
    if not isinstance(start,dict) or not isinstance(receipt,dict) or not isinstance(receipt.get('rolls'),list) or len(receipt['rolls'])>40:
        raise ValueError('Recibo de reloj compartido inválido')
    _participants(start)
    if (start['round']!=outcome['round'] or [p['id'] for p in start['patients']]!=[record['character'],record['npc']]
        or [(p['hp'],p['constitution'],p['stable']) for p in start['patients']]!=[
            (outcome['hp'],outcome['constitution'],outcome['stable']),(outcome['npcHp'],outcome['npcConstitution'],outcome['npcStable'])]):
        raise ValueError('El reloj no parte de su desenlace registrado')
    index=0
    def replay(role):
        nonlocal index
        if index>=len(receipt['rolls']):raise ValueError('Faltan pruebas del reloj compartido')
        entry=receipt['rolls'][index];index+=1
        if not isinstance(entry,list) or len(entry)!=2 or type(entry[0])!=int or entry[0]!=role:
            raise ValueError('Prueba de participante fuera de su instante')
        return entry[1]
    result=simulate(start,replay)
    if index!=len(receipt['rolls']) or not isinstance(receipt.get('worldTimeBefore'),str):raise ValueError('Sobran pruebas o falta el tiempo anterior')
    from rule_pack_authoring import canonical
    if canonical(receipt)!=canonical(_receipt(start,result,receipt['worldTimeBefore'])):
        raise ValueError('El resultado compartido no coincide con sus pruebas')
    expected_limit='shared-rest-boundary' if result['status']=='rest-boundary' else None
    if record.get('recoveryLimit')!=expected_limit:raise ValueError('El límite no corresponde al resultado compartido')
