"""Pure HP calculation for one uninterrupted8h night, Core PDF191-192.

Not a rest action: the caller must schedule time, all other creatures, armor,
fatigue and daily resources before applying this result. No dice or IO.
"""
import pf_recovery


def night_healing(character,*,elapsed_seconds,significant_interruption=False):
    if type(elapsed_seconds)!=int or not 0<=elapsed_seconds<=28800 or type(significant_interruption)!=bool:
        raise ValueError('Este cálculo cubre un único período de descanso de hasta8h')
    hp=character.get('hp');maximum=character.get('maxHp');level=character.get('level');abilities=character.get('abilities')
    if (type(hp)!=int or type(maximum)!=int or not 1<=maximum<=10000 or hp>maximum
        or type(level)!=int or not 1<=level<=100 or not isinstance(abilities,list) or len(abilities)!=6
        or type(abilities[2])!=int or not 1<=abilities[2]<=60):
        raise ValueError('El descanso requiere PG, nivel y Constitución preparados')
    if hp<=-abilities[2]:raise ValueError('El descanso no devuelve la vida')
    if character.get('conditions','').strip():raise ValueError('Las condiciones necesitan resolución conjunta antes de aplicar descanso')
    pf_recovery.validate_restored({'characters':[character]})
    assisted=None
    if hp<0:
        assisted=character.get('recoveryCare',{}).get('assisted')
        if character.get('stable') is not True or assisted is not True:
            raise ValueError('La recuperación natural con PG negativos sin ayuda requiere su prueba diaria, todavía fuera de este cálculo')
    reason='interrupted' if significant_interruption else 'insufficient-rest' if elapsed_seconds<28800 else 'complete'
    amount=min(level,maximum-hp) if reason=='complete' else 0
    after=hp+amount
    return {'kind':'natural-night-rest','elapsedSeconds':elapsed_seconds,'reason':reason,
        'hpBefore':hp,'hpAfter':after,'amount':amount,'level':level,'assisted':assisted,
        'consciousAfter':after>=0 or pf_recovery.is_conscious(character)}
