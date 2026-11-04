"""Experimental Cairn 1e arithmetic; not a playable or registered adapter.

Based on Cairn SRD v1.0 by Yochai Gal (CC BY-SA 4.0):
https://cairnrpg.com/first-edition/cairn-srd/
https://creativecommons.org/licenses/by-sa/4.0/
Changes: original deterministic implementation with input validation and provenance.
This file and its rule descriptions are distributed under CC BY-SA 4.0.
No Pathfinder mechanics, classes, levels or DCs are inferred.
"""
import copy

ID='cairn-1e'
ABILITIES=('STR','DEX','WIL')
SOURCE='https://cairnrpg.com/first-edition/cairn-srd/'


def _dice(values,count,sides):
    if not isinstance(values,list) or len(values)!=count or any(type(v)!=int or not 1<=v<=sides for v in values):
        raise ValueError('Resultados de dados de Cairn inválidos')
    return sum(values)


def core_from_rolls(rolls):
    """Calculate only the initial core. Equipment, traits and identity still required."""
    if not isinstance(rolls,dict) or set(rolls)!={'STR','DEX','WIL','HP','gold','age'}:
        raise ValueError('Tiradas iniciales de Cairn incompletas')
    abilities={key:_dice(rolls[key],3,6) for key in ABILITIES}
    hp=_dice(rolls['HP'],1,6);gold=_dice(rolls['gold'],3,6);age=10+_dice(rolls['age'],2,20)
    return {'ruleset':ID,'abilities':abilities,'hitProtection':hp,'initialHitProtection':hp,
        'gold':gold,'age':age,'creation':{'rolls':copy.deepcopy(rolls),'swapped':[],
        'complete':False,'pending':['name','background','traits','startingGear']}}


def swap_initial(core,pair):
    """The player may swap two initial results once, before completing creation."""
    if (not isinstance(pair,list) or len(pair)!=2 or any(not isinstance(k,str) or k not in ABILITIES for k in pair)
        or pair[0]==pair[1]):raise ValueError('Elige dos características diferentes de Cairn')
    if not isinstance(core,dict) or core.get('ruleset')!=ID:raise ValueError('La ficha no pertenece a Cairn 1e')
    creation=core.get('creation',{})
    if not isinstance(creation,dict):raise ValueError('Creación de Cairn inválida')
    if creation.get('complete') or creation.get('swapped'):raise ValueError('El intercambio inicial ya no está disponible')
    original=core_from_rolls(creation.get('rolls'))
    if core.get('abilities')!=original['abilities']:raise ValueError('Las características iniciales han cambiado')
    result=copy.deepcopy(core);a,b=pair
    result['abilities'][a],result['abilities'][b]=result['abilities'][b],result['abilities'][a]
    result['creation']['swapped']=list(pair)
    return result


def save(core,ability,raw):
    """Resolve an already-required save; do not decide when fiction requires one."""
    if not isinstance(core,dict) or core.get('ruleset')!=ID:raise ValueError('La ficha no pertenece a Cairn 1e')
    if not isinstance(ability,str) or ability not in ABILITIES:raise ValueError('Característica de Cairn inválida')
    abilities=core.get('abilities')
    if not isinstance(abilities,dict):raise ValueError('Características de Cairn inválidas')
    score=abilities.get(ability)
    if type(score)!=int or score<0:raise ValueError('Valor de característica de Cairn inválido')
    _dice([raw],1,20)
    return {'ruleset':ID,'ability':ability,'raw':raw,'target':score,
        'success':raw==1 or raw!=20 and raw<=score,
        'source':SOURCE+'#saves','effectApplied':False}
