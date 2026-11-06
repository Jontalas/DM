"""Source-backed consciousness checks and episode state; no IO.

Core Rules PDF191-192 (printed190-191). Integration must record care,
advance shared fictional time, and support conscious negative-HP characters
before exposing an hourly campaign action. apply_hour is internal; its caller
must advance shared fictional time and confirm all affected actors atomically.
"""


def is_conscious(character):
    return character['hp']>=0 or (character['hp']>-character['abilities'][2]
        and character.get('stable') is True and character.get('recoveryState',{}).get('conscious') is True)


def clear_episode(character):
    character.pop('recoveryCare',None);character.pop('recoveryState',None)


def record_stabilization(character,*,assisted,round_number):
    # Called only when a verified rule actually stabilizes a dying creature.
    consciousness_check({**character,'stable':True},20,assisted=assisted)
    if type(round_number)!=int or not 1<=round_number<=1000000:
        raise ValueError('La asistencia requiere una ronda válida')
    character['stable']=True
    character.pop('recoveryState',None)
    character['recoveryCare']={'format':'cronicas-pf-care-1','assisted':assisted,'round':round_number}


def validate_restored(state):
    for character in state.get('characters',[]):
        if 'recoveryState' in character and 'recoveryCare' not in character:raise ValueError('La recuperación no conserva asistencia conocida')
        if 'recoveryCare' not in character:continue
        care=character['recoveryCare']
        if (state.get('ruleset','pathfinder-1e')!='pathfinder-1e' or not isinstance(care,dict)
            or set(care)!={'format','assisted','round'} or care['format']!='cronicas-pf-care-1'
            or type(care['assisted'])!=bool or type(care['round'])!=int or not 1<=care['round']<=1000000):
            raise ValueError('Registro de asistencia Pathfinder inválido')
        patient={k:v for k,v in character.items() if k!='recoveryState'}
        consciousness_check(patient,20,assisted=care['assisted'])
        if 'recoveryState' in character:
            recovery=character['recoveryState']
            if (not isinstance(recovery,dict) or set(recovery)!={'format','hours','conscious','lastCheck'}
                or recovery['format']!='cronicas-pf-recovery-state-1' or type(recovery['hours'])!=int
                or not 1<=recovery['hours']<=1000000 or type(recovery['conscious'])!=bool
                or not isinstance(recovery['lastCheck'],dict)):
                raise ValueError('Estado de consciencia inválido')
            check=recovery['lastCheck']
            if 'hpBefore' not in check or 'die' not in check:raise ValueError('Falta la prueba de recuperación')
            expected=consciousness_check(patient|{'hp':check['hpBefore']},check['die'],assisted=care['assisted'])
            from rule_pack_authoring import canonical
            if canonical(check)!=canonical(expected) or expected['dead'] or expected['hpAfter']!=character['hp'] or expected['conscious']!=recovery['conscious']:
                raise ValueError('La consciencia no coincide con su prueba de recuperación')


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
