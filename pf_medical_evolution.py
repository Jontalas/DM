"""Replayable medical evolution after a verified consciousness check.

Internal arithmetic/audit support, not a campaign rest action or scheduler.
Historical assistance remains distinct from later manual corrections.
"""
import copy
from rule_pack_authoring import canonical

FORMAT='cronicas-pf-recovery-state-3'


def director_view(character):
    proof=character.get('recoveryState')
    if not isinstance(proof,dict) or proof.get('format')!=FORMAT:return None
    return {'format':'cronicas-pf-medical-context-1','hours':proof['hours'],'conscious':proof['conscious']}


def record(character,change):
    import pf_recovery
    recovery=character.get('recoveryState')
    if not isinstance(recovery,dict):raise ValueError('La evolución necesita una comprobación de consciencia registrada')
    previous={'id':character['id'],'hp':character['hp'],'constitution':character['abilities'][2],
        'maxHp':character['maxHp'],'level':character['level'],'stable':character.get('stable',False),
        'care':copy.deepcopy(character.get('recoveryCare')),'recovery':copy.deepcopy(recovery)}
    return {'format':FORMAT,'hours':recovery['hours'],'conscious':pf_recovery.is_conscious(character),
        'previous':previous,'change':copy.deepcopy(change)}


def validate(character,*,board=None):
    import pf_recovery
    import pf_rest
    proof=character['recoveryState'];prior=proof.get('previous');change=proof.get('change')
    abilities=character.get('abilities');hp=character.get('hp')
    if (set(proof)!={'format','hours','conscious','previous','change'} or proof['format']!=FORMAT
        or not isinstance(abilities,list) or len(abilities)!=6 or type(abilities[2])!=int or not 1<=abilities[2]<=60
        or type(hp)!=int or not -abilities[2]<hp<0 or character.get('stable') is not True
        or not isinstance(character.get('conditions',''),str)
        or not isinstance(prior,dict) or set(prior)!={'id','hp','constitution','maxHp','level','stable','care','recovery'}
        or not isinstance(prior['id'],str) or not prior['id'] or prior['id']!=character.get('id')
        or type(prior['constitution'])!=int or not 1<=prior['constitution']<=60
        or type(prior['hp'])!=int or not -prior['constitution']<prior['hp']<hp
        or prior['stable'] is not True or type(prior['maxHp'])!=int or not 1<=prior['maxHp']<=10000
        or type(prior['level'])!=int or not 1<=prior['level']<=100 or not isinstance(prior['recovery'],dict)
        or type(proof['hours'])!=int or type(proof['conscious'])!=bool or not isinstance(change,dict)):
        raise ValueError('La evolución médica no conserva su estado anterior')
    # Strictly increasing negative HP bounds nested history to at most59 steps.
    previous={'id':prior['id'],'hp':prior['hp'],'maxHp':prior['maxHp'],'level':prior['level'],
        'abilities':[10,10,prior['constitution'],10,10,10],'stable':True,'conditions':'',
        'recoveryState':copy.deepcopy(prior['recovery'])}
    if prior['care'] is not None:previous['recoveryCare']=copy.deepcopy(prior['care'])
    context={'characters':[previous]}
    if board is not None:context['board']=board
    pf_recovery.validate_restored(context)
    if proof['hours']!=previous['recoveryState']['hours'] or proof['conscious']!=pf_recovery.is_conscious(previous):
        raise ValueError('La evolución no puede inventar horas ni consciencia')
    if change.get('kind')=='natural-night-rest':
        if set(change)!={'kind','result'} or character.get('recoveryCare')!=prior['care']:
            raise ValueError('La curación natural debe conservar la asistencia verificada')
        expected=pf_rest._night_healing_result(previous,elapsed_seconds=28800,significant_interruption=False)
        if expected['amount']<=0 or expected['hpAfter']!=hp or canonical(change['result'])!=canonical(expected):
            raise ValueError('La evolución no coincide con la curación natural registrada')
    elif change.get('kind')=='manual-hp-correction':
        if (set(change)!={'kind','fromHp','hp','reason'} or type(change['fromHp'])!=int or change['fromHp']!=prior['hp']
            or type(change['hp'])!=int or change['hp']!=hp or 'recoveryCare' in character
            or not isinstance(change['reason'],str) or not change['reason'].strip() or len(change['reason'])>500):
            raise ValueError('La corrección no certifica asistencia ni reemplaza la curación anterior')
    else:raise ValueError('Cambio médico no cubierto')
