"""Combate cuerpo a cuerpo básico, Pathfinder 1e; sin llamadas a IA o Firebase.

Perfil acotado: arma empuñada de alcance 5 pies, daño letal sin dados extra,
sin condiciones, cobertura, ocultación, resistencias ni aptitudes especiales.
Los totales se preparan en la ficha; el motor resuelve cada ataque.
"""
import re


def damage_spec(value):
    match=re.fullmatch(r'(\d{1,2})d(\d{1,3})(?:\+(\d{1,3}))?',str(value).strip())
    if not match:raise ValueError('Daño básico: usa NdM o NdM+bonificador, sin daño adicional ni penalizadores')
    count,sides,bonus=int(match[1]),int(match[2]),int(match[3] or 0)
    if not 1<=count<=20 or sides not in (2,3,4,6,8,10,12,20,100):
        raise ValueError('Dados de daño fuera del perfil básico')
    return count,sides,bonus


def profile(character):
    data=character.get('meleeProfile')
    if not isinstance(data,dict):raise ValueError('Prepara el perfil cuerpo a cuerpo básico en ambas fichas antes de atacar')
    if any(type(data.get(key))!=int for key in ('flatAc','criticalMin','multiplier')):
        raise ValueError('Perfil cuerpo a cuerpo incompleto')
    if not 0<=data['flatAc']<=character['ac'] or not 18<=data['criticalMin']<=20 or not 2<=data['multiplier']<=4:
        raise ValueError('CA desprevenido o crítico fuera del perfil básico')
    damage_spec(character['damage'])
    return data


def health_status(character):
    hp=character['hp'];constitution=character['abilities'][2]
    if hp<=-constitution:return 'muerto'
    if hp<0:return 'inconsciente estable' if character.get('stable') else 'moribundo'
    if hp==0:return 'incapacitado'
    return 'consciente'


def standing(character):
    return character['hp']>=0


def adjacent(a,b):
    return max(abs(a['x']-b['x']),abs(a['y']-b['y']))==1


def basic_pair(source,target,board):
    source_profile=profile(source);target_profile=profile(target)
    if source.get('conditions','').strip() or target.get('conditions','').strip():
        raise ValueError('Hay condiciones que requieren una resolución excepcional antes de usar el ataque básico')
    if not adjacent(source,target):raise ValueError('El objetivo debe estar a 5 pies, en una casilla adyacente')
    for c in (source,target):
        if any(board['terrain'].get(f'{x},{y}')=='wall'
               for x in range(c['x']-1,c['x']+2) for y in range(c['y']-1,c['y']+2)):
            raise ValueError('Un muro cercano puede dar cobertura; requiere resolución excepcional')
    return source_profile,target_profile


def attack(state,body,actor,dice):
    board=state['board']
    if not board['active']:raise ValueError('Inicia el combate antes de atacar')
    source=next((c for c in state['characters'] if c['id']==body.get('character')),None)
    target=next((c for c in state['characters'] if c['id']==body.get('target')),None)
    if source is None or target is None:raise ValueError('Selecciona atacante y objetivo')
    if source['owner']!=actor['id'] and not actor['host']:raise PermissionError('No controlas este personaje')
    if board['order'][board['turn']]['id']!=source['id']:raise ValueError('No es tu turno')
    if source['id']==target['id'] or source['enemy']==target['enemy']:raise ValueError('Selecciona un adversario')
    if source['hp']<0:raise ValueError('Un personaje inconsciente o muerto no puede atacar')
    if target['hp']<=0:raise ValueError('Atacar a un adversario caído requiere una resolución excepcional')
    source_profile,target_profile=basic_pair(source,target,board)
    spent=board['spent'].get(source['id'],{})
    if spent.get('standard') or (source['hp']==0 and spent.get('move')):
        raise ValueError('La acción necesaria ya está gastada')
    # Old saved combats lack acted tracking: do not guess flat-footed status.
    if 'acted' not in board:raise ValueError('Reinicia este combate antiguo para activar el ataque automático')
    flat=target['id'] not in board['acted']
    armor=target_profile['flatAc'] if flat else target['ac']
    # Flanking for same-size, 5-foot-reach combatants: opposite adjacent squares.
    flanking=False
    for ally in state['characters']:
        if ally['id']==source['id'] or ally['enemy']!=source['enemy'] or ally['hp']<=0 or ally.get('conditions','').strip():continue
        if not ally.get('meleeProfile') or not adjacent(ally,target):continue
        if (ally['x']-target['x'],ally['y']-target['y'])==(-(source['x']-target['x']),-(source['y']-target['y'])):
            flanking=True
    modifier=source['attack']+(2 if flanking else 0)
    physical=body.get('physical')
    if physical is not None and (not actor['host'] or not isinstance(physical,dict)):
        raise PermissionError('Solo el anfitrión registra tiradas físicas verificadas de combate')
    def roll(key,sides):
        if physical is not None and key not in physical:raise ValueError('Falta la tirada física: '+key)
        return dice(sides,physical[key] if physical is not None else None)
    raw=roll('attack',[20])[0]
    hits=lambda value:value==20 or (value!=1 and value+modifier>=armor)
    hit=hits(raw);confirmation=None;critical=False;damage=0;damage_rolls=[]
    if hit:
        if raw>=source_profile['criticalMin']:
            confirmation=roll('confirmation',[20])[0];critical=hits(confirmation)
        count,sides,bonus=damage_spec(source['damage'])
        multiplier=source_profile['multiplier'] if critical else 1
        damage_rolls=roll('damage',[sides]*(count*multiplier))
        damage=sum(damage_rolls)+bonus*multiplier
    # Mutation begins only after all input and physical dice are validated.
    target['hp']-=damage
    if damage:target['stable']=False
    spent={**spent,'standard':True}
    board['spent'][source['id']]=spent
    if source['hp']==0:
        source['hp']-=1;source['stable']=False  # Strenuous standard action while disabled.
    result={'attacker':source['id'],'target':target['id'],'roll':raw,'modifier':modifier,
            'ac':armor,'flatFooted':flat,'flanking':flanking,'hit':hit,'confirmation':confirmation,
            'critical':critical,'damageRolls':damage_rolls,'damage':damage,'targetHp':target['hp'],
            'status':health_status(target),'attackerHp':source['hp'],'attackerStatus':health_status(source),
            'origin':'físico' if physical is not None else 'servidor'}
    return result
