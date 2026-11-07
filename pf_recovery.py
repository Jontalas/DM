"""Source-backed consciousness checks and episode state; no IO.

Core Rules PDF191-192 (printed190-191). Integration must record care,
advance shared fictional time, and support conscious negative-HP characters
before exposing an hourly campaign action. apply_hour is internal; its caller
must advance shared fictional time and confirm all affected actors atomically.
"""
import copy


def is_conscious(character):
    return character['hp']>=0 or (character['hp']>-character['abilities'][2]
        and character.get('stable') is True and character.get('recoveryState',{}).get('conscious') is True)


def clear_episode(character):
    character.pop('recoveryCare',None);character.pop('recoveryState',None)


def record_stabilization(character,*,assisted,round_number,initiative=None,order=None,epoch=None):
    # Called only when a verified rule actually stabilizes a dying creature.
    consciousness_check({**character,'stable':True},20,assisted=assisted)
    if type(round_number)!=int or not 1<=round_number<=1000000:
        raise ValueError('La asistencia requiere una ronda válida')
    care={'format':'cronicas-pf-care-1','assisted':assisted,'round':round_number}
    if initiative is not None or order is not None or epoch is not None:
        care.update(format='cronicas-pf-care-2',initiative=initiative,order=order[:] if isinstance(order,list) else order)
        if epoch is not None:care.update(format='cronicas-pf-care-3',epoch=epoch)
        _validate_initiative_care(character,care)
    character['stable']=True
    character.pop('recoveryState',None)
    character['recoveryCare']=care


def _validate_initiative_care(character,care):
    order=care['order']
    if (not isinstance(order,list) or not 1<=len(order)<=400 or any(not isinstance(v,str) or not 1<=len(v)<=80 for v in order)
        or len(set(order))!=len(order) or not isinstance(care['initiative'],str)
        or care['initiative'] not in order or character.get('id') not in order):
        raise ValueError('La asistencia no conserva su cuenta de iniciativa')
    if care['format']=='cronicas-pf-care-3' and (type(care['epoch'])!=int or not 1<=care['epoch']<=1000000):
        raise ValueError('La asistencia no conserva el episodio de combate')


def validate_restored(state):
    board=state.get('board',{})
    if not isinstance(board,dict):raise ValueError('Tablero temporal inválido')
    if 'combatSerial' in board and (type(board['combatSerial'])!=int or not 0<=board['combatSerial']<=1000000):
        raise ValueError('Historial temporal de combate inválido')
    for character in state.get('characters',[]):
        recovery=character.get('recoveryState')
        adjusted=isinstance(recovery,dict) and recovery.get('format')=='cronicas-pf-recovery-state-2'
        if adjusted and 'recoveryCare' in character:raise ValueError('La corrección manual no certifica asistencia actual')
        if 'recoveryState' in character and 'recoveryCare' not in character and not adjusted:raise ValueError('La recuperación no conserva asistencia conocida')
        if 'recoveryCare' not in character and not adjusted:continue
        care=recovery.get('careAtCheck') if adjusted else character['recoveryCare']
        version=care.get('format') if isinstance(care,dict) else None
        fields={'format','assisted','round'}|({'initiative','order'} if version in ('cronicas-pf-care-2','cronicas-pf-care-3') else set())|({'epoch'} if version=='cronicas-pf-care-3' else set())
        if (state.get('ruleset','pathfinder-1e')!='pathfinder-1e' or not isinstance(care,dict)
            or set(care)!=fields or version not in ('cronicas-pf-care-1','cronicas-pf-care-2','cronicas-pf-care-3')
            or type(care['assisted'])!=bool or type(care['round'])!=int or not 1<=care['round']<=1000000):
            raise ValueError('Registro de asistencia Pathfinder inválido')
        if version in ('cronicas-pf-care-2','cronicas-pf-care-3'):_validate_initiative_care(character,care)
        if version=='cronicas-pf-care-3' and 'board' in state and care['epoch']>board.get('combatSerial',0):
            raise ValueError('La asistencia pertenece a un combate posterior al reloj de esta copia')
        if not isinstance(character.get('conditions',''),str):raise ValueError('Anotación de condiciones inválida')
        # Current annotations do not rewrite the circumstances of a past check.
        # Issuing a new check still validates the real conditions below.
        patient={**{k:v for k,v in character.items() if k!='recoveryState'},'conditions':''}
        consciousness_check(patient,20,assisted=care['assisted'])
        if 'recoveryState' in character:
            fields={'format','hours','conscious','lastCheck'}|({'careAtCheck','adjustments'} if adjusted else set())
            if (not isinstance(recovery,dict) or set(recovery)!=fields
                or recovery['format'] not in ('cronicas-pf-recovery-state-1','cronicas-pf-recovery-state-2') or type(recovery['hours'])!=int
                or not 1<=recovery['hours']<=1000000 or type(recovery['conscious'])!=bool
                or not isinstance(recovery['lastCheck'],dict)):
                raise ValueError('Estado de consciencia inválido')
            check=recovery['lastCheck']
            if 'hpBefore' not in check or 'die' not in check:raise ValueError('Falta la prueba de recuperación')
            expected=consciousness_check(patient|{'hp':check['hpBefore']},check['die'],assisted=care['assisted'])
            final_hp=expected['hpAfter']
            if adjusted:
                changes=recovery['adjustments']
                if not isinstance(changes,list) or not 1<=len(changes)<=100:raise ValueError('Historial de correcciones médicas inválido')
                for change in changes:
                    if (not isinstance(change,dict) or set(change)!={'kind','fromHp','hp','reason'}
                        or change['kind']!='manual-hp-correction' or type(change['fromHp'])!=int or change['fromHp']!=final_hp
                        or type(change['hp'])!=int or not final_hp<change['hp']<0
                        or not isinstance(change['reason'],str) or not change['reason'].strip() or len(change['reason'])>500):
                        raise ValueError('La corrección no conserva la evolución de las heridas')
                    final_hp=change['hp']
            from rule_pack_authoring import canonical
            if canonical(check)!=canonical(expected) or expected['dead'] or final_hp!=character['hp'] or expected['conscious']!=recovery['conscious']:
                raise ValueError('La consciencia no coincide con su prueba de recuperación')


def manual_hp_change(character,delta,*,reason):
    """Explicit correction, not certified healing; retain historical awareness."""
    if type(delta)!=int or not -10000<=delta<=10000 or not isinstance(reason,str) or not reason.strip():
        raise ValueError('La corrección de PG requiere valor y motivo válidos')
    if not delta:return
    before=character['hp'];after=before+delta;proof=None
    if delta>0 and after<0 and 'recoveryState' in character:
        validate_restored({'characters':[character]})
        proof=copy.deepcopy(character['recoveryState'])
        if proof['format']=='cronicas-pf-recovery-state-1':
            proof.update(format='cronicas-pf-recovery-state-2',careAtCheck=copy.deepcopy(character['recoveryCare']),adjustments=[])
        if len(proof['adjustments'])>=100:raise ValueError('El historial médico requiere revisión antes de otra corrección')
        proof['adjustments'].append({'kind':'manual-hp-correction','fromHp':before,'hp':after,'reason':reason.strip()[:500]})
    character['hp']=after;character['stable']=delta>0;clear_episode(character)
    if proof is not None:character['recoveryState']=proof


def consciousness_check(character,raw,*,assisted):
    if type(assisted)!=bool or type(raw)!=int or not 1<=raw<=20:
        raise ValueError('La recuperación requiere asistencia conocida y un d20 válido')
    abilities=character.get('abilities')
    if not isinstance(abilities,list) or len(abilities)!=6 or type(abilities[2])!=int or not 1<=abilities[2]<=60:
        raise ValueError('La recuperación requiere Constitución verificada')
    hp=character.get('hp');constitution=abilities[2]
    if type(hp)!=int or not -constitution<hp<0 or character.get('stable') is not True:
        raise ValueError('La prueba horaria requiere un paciente vivo, estable y con PG negativos')
    if character.get('conscious') is True or character.get('recoveryState',{}).get('conscious') is True or character.get('conditions','').strip():
        raise ValueError('La consciencia o las condiciones requieren otro recorrido de recuperación')
    modifier=(constitution-10)//2+hp
    success=raw==20 or raw+modifier>=10
    after=hp-(not assisted and not success)
    return {'die':raw,'modifier':modifier,'total':raw+modifier,'dc':10,
        'success':success,'naturalSuccess':raw==20,'assisted':assisted,
        'hpBefore':hp,'hpAfter':after,'conscious':success,'dead':after<=-constitution,
        'elapsedSeconds':3600}


def apply_hour(character,raw):
    """Internal patient update; campaign clock/authorization belong to caller."""
    validate_restored({'characters':[character]})
    care=character.get('recoveryCare')
    if care is None:raise ValueError('No se conoce la asistencia de este episodio; no se supone una recuperación')
    result=consciousness_check(character,raw,assisted=care['assisted'])
    hours=character.get('recoveryState',{}).get('hours',0)+1
    if hours>1000000:raise ValueError('La recuperación supera el límite operativo')
    character['hp']=result['hpAfter']
    if result['dead']:
        character['stable']=False;clear_episode(character)
    else:
        character['recoveryState']={'format':'cronicas-pf-recovery-state-1','hours':hours,
            'conscious':result['conscious'],'lastCheck':result}
    return result


def next_hourly_events(characters):
    """Read-only next simultaneous checks; not a complete time controller.

    Core PDF179/printed178: a round is6s and a full-round interval ends at
    the same initiative count.600 rounds are one hour. Do not invent equal
    fractions of6s for participants. Natural healing/rest must be scheduled
    separately before this planner can drive multi-patient campaign time.
    """
    validate_restored({'characters':characters})
    events=[];shared_order=None;shared_epoch=None
    for patient in characters:
        if patient['hp']>=0 or patient['hp']<=-patient['abilities'][2] or is_conscious(patient):continue
        if patient.get('conditions','').strip():raise ValueError('Las condiciones requieren resolver sus efectos antes de programar horas')
        if patient.get('stable') is not True:raise ValueError('Resuelve la estabilización por turnos antes de avanzar horas')
        care=patient.get('recoveryCare',{})
        if care.get('format')!='cronicas-pf-care-3':raise ValueError('La copia no conserva el episodio e instante de asistencia; no se supone un reloj')
        if shared_epoch is None:shared_epoch=care['epoch']
        elif shared_epoch!=care['epoch']:raise ValueError('Los pacientes pertenecen a combates distintos; hace falta un reloj común verificado')
        if shared_order is None:shared_order=care['order']
        elif shared_order!=care['order']:raise ValueError('Los pacientes necesitan un reloj común; no se mezclan iniciativas históricas distintas')
        hours=patient.get('recoveryState',{}).get('hours',0)+1
        due=(care['round']+600*hours,care['order'].index(care['initiative']))
        events.append({'character':patient['id'],'epoch':care['epoch'],'round':due[0],'initiative':care['initiative'],'orderIndex':due[1]})
    if not events:return []
    earliest=min((e['round'],e['orderIndex']) for e in events)
    return [e for e in events if (e['round'],e['orderIndex'])==earliest]
