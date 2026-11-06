"""Source-backed hourly consciousness checks; no state/clock mutation or IO.

Core Rules PDF191-192 (printed190-191). Integration must record care,
advance shared fictional time, and support conscious negative-HP characters
before applying this calculation to a campaign.
"""


def record_stabilization(character,*,assisted,round_number):
    # Called only when a verified rule actually stabilizes a dying creature.
    consciousness_check({**character,'stable':True},20,assisted=assisted)
    if type(round_number)!=int or not 1<=round_number<=1000000:
        raise ValueError('La asistencia requiere una ronda válida')
    character['stable']=True
    character['recoveryCare']={'format':'cronicas-pf-care-1','assisted':assisted,'round':round_number}


def validate_restored(state):
    for character in state.get('characters',[]):
        if 'recoveryCare' not in character:continue
        care=character['recoveryCare']
        if (state.get('ruleset','pathfinder-1e')!='pathfinder-1e' or not isinstance(care,dict)
            or set(care)!={'format','assisted','round'} or care['format']!='cronicas-pf-care-1'
            or type(care['assisted'])!=bool or type(care['round'])!=int or not 1<=care['round']<=1000000):
            raise ValueError('Registro de asistencia Pathfinder inválido')
        consciousness_check(character,20,assisted=care['assisted'])


def consciousness_check(character,raw,*,assisted):
    if type(assisted)!=bool or type(raw)!=int or not 1<=raw<=20:
        raise ValueError('La recuperación requiere asistencia conocida y un d20 válido')
    abilities=character.get('abilities')
    if not isinstance(abilities,list) or len(abilities)!=6 or type(abilities[2])!=int or not 1<=abilities[2]<=60:
        raise ValueError('La recuperación requiere Constitución verificada')
    hp=character.get('hp');constitution=abilities[2]
    if type(hp)!=int or not -constitution<hp<0 or character.get('stable') is not True:
        raise ValueError('La prueba horaria requiere un paciente vivo, estable y con PG negativos')
    if character.get('conscious') is True or character.get('conditions','').strip():
        raise ValueError('La consciencia o las condiciones requieren otro recorrido de recuperación')
    modifier=(constitution-10)//2+hp
    success=raw==20 or raw+modifier>=10
    after=hp-(not assisted and not success)
    return {'die':raw,'modifier':modifier,'total':raw+modifier,'dc':10,
        'success':success,'naturalSuccess':raw==20,'assisted':assisted,
        'hpBefore':hp,'hpAfter':after,'conscious':success,'dead':after<=-constitution,
        'elapsedSeconds':3600}
