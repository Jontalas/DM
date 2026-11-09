"""Combate cuerpo a cuerpo básico, Pathfinder 1e; sin llamadas a IA o Firebase.

Perfil acotado: arma empuñada de alcance 5 pies, daño letal sin dados extra,
sin condiciones, cobertura, ocultación, resistencias ni aptitudes especiales.
Los totales se preparan en la ficha; el motor resuelve cada ataque.
"""
import re
import pf_recovery
import board_scenes


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
    if hp<0:
        if pf_recovery.is_conscious(character):return 'incapacitado'
        return 'inconsciente estable' if character.get('stable') else 'moribundo'
    if hp==0:return 'incapacitado'
    return 'consciente'


def standing(character):
    return pf_recovery.is_conscious(character)


def movement_cells(character):
    """Full5ft squares in one move: disabled speed halves (Core PDF568/567)."""
    speed=character.get('speed')
    if type(speed)!=int or not 1<=speed<=100:raise ValueError('El movimiento requiere una velocidad normal preparada')
    if not standing(character):return 0
    return speed//2 if character['hp']<=0 else speed


FIVE_FOOT_STEP_SCOPE='normal-light-ground-five-foot-step-1'


def five_foot_step_enabled(state):
    return (state.get('pfEncounter') or {}).get('definition',{}).get('fiveFootStepScope')==FIVE_FOOT_STEP_SCOPE


def five_foot_step_used(board,identifier):
    steps=board.get('fiveFootSteps',{})
    if not isinstance(steps,dict) or any(type(value)!=bool for value in steps.values()):
        raise ValueError('El registro de pasos necesita revisión antes de mover')
    return steps.get(identifier,False)


def five_foot_step_destination(state,source,path):
    """Core PDF184/190/194: a chosen no-action step, not ordinary movement."""
    record=state.get('pfEncounter') or {};board=state['board']
    if not five_foot_step_enabled(state):raise ValueError('Este encuentro aún no ofrece el paso automático de 5 pies')
    if (state.get('mode','solo')!='solo' or record.get('phase')!='combat' or not board.get('active')
        or source['id']!=record.get('character') or len(state['characters'])!=2):
        raise ValueError('El paso automático corresponde al PJ del combate individual preparado')
    if board.get('autoPaused'):raise ValueError('Resuelve primero la pausa del turno automático')
    if not board.get('order') or board['order'][board['turn']]['id']!=source['id']:raise ValueError('No es tu turno')
    board_scenes.require_present(state,source)
    opponent=next((c for c in state['characters'] if c['id']==record.get('npc')),None)
    if opponent is None or not board_scenes.present(state,opponent) or health_status(opponent) in ('muerto','inconsciente estable'):
        raise ValueError('Revisa primero el desenlace del encuentro preparado')
    if not standing(source):raise ValueError('Un personaje inconsciente o muerto no puede dar el paso')
    if source.get('conditions','').strip() or opponent.get('conditions','').strip():raise ValueError('Las condiciones requieren revisión antes del paso automático')
    if record['definition'].get('conditions',{}).get('lighting')!='normal':raise ValueError('Este paso automático necesita luz normal verificada')
    if state['pending'] or any(not isinstance(e,dict) or not e.get('interpreted') for e in state['consequences']):
        raise ValueError('Resuelve primero las situaciones pendientes antes de automatizar el paso')
    if type(source.get('speed'))!=int or not 2<=source['speed']<=100:
        raise ValueError('El paso necesita una velocidad terrestre preparada superior a 5 pies')
    if five_foot_step_used(board,source['id']):raise ValueError('Ya has dado tu paso de 5 pies este asalto')
    spent=board['spent'].get(source['id'],{})
    if not isinstance(spent,dict) or spent.get('move'):
        raise ValueError('No se automatiza el paso tras una acción de movimiento registrada; si no hubo desplazamiento, requiere revisión excepcional')
    if not isinstance(path,list) or len(path)!=1 or not isinstance(path[0],list) or len(path[0])!=2 or any(type(v)!=int for v in path[0]):
        raise ValueError('Elige una única casilla para el paso de 5 pies')
    x,y=source['x'],source['y'];nx,ny=path[0];dx,dy=abs(nx-x),abs(ny-y)
    if not 0<=nx<20 or not 0<=ny<20 or max(dx,dy)!=1:raise ValueError('El paso necesita una casilla adyacente del tablero')
    if any(board['terrain'].get(f'{px},{py}','clear')!='clear' for px,py in ((x,y),(nx,ny))):
        raise ValueError('Esta versión solo automatiza el paso con origen y destino despejados')
    if dx and dy and (board['terrain'].get(f'{x},{ny}')=='wall' or board['terrain'].get(f'{nx},{y}')=='wall'):
        raise ValueError('No puedes dar el paso cortando la esquina de un muro')
    if any(c['id']!=source['id'] and (c['x'],c['y'])==(nx,ny) for c in board_scenes.characters(state)):
        raise ValueError('La casilla del paso está ocupada')
    return nx,ny


def adjacent(a,b):
    return a.get('sceneId')==b.get('sceneId') and max(abs(a['x']-b['x']),abs(a['y']-b['y']))==1


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


def attack_context(state,body,actor):
    """Shared read-only legality and totals; never draws dice or spends actions."""
    board=state['board']
    if not board['active']:raise ValueError('Inicia el combate antes de atacar')
    source=next((c for c in state['characters'] if c['id']==body.get('character')),None)
    target=next((c for c in state['characters'] if c['id']==body.get('target')),None)
    if source is None or target is None:raise ValueError('Selecciona atacante y objetivo')
    board_scenes.require_present(state,source,target)
    if source['owner']!=actor['id'] and not actor['host']:raise PermissionError('No controlas este personaje')
    if board['order'][board['turn']]['id']!=source['id']:raise ValueError('No es tu turno')
    if source['id']==target['id'] or source['enemy']==target['enemy']:raise ValueError('Selecciona un adversario')
    if not standing(source):raise ValueError('Un personaje inconsciente o muerto no puede atacar')
    if target['hp']<=0:raise ValueError('Atacar a un adversario caído requiere una resolución excepcional')
    source_profile,target_profile=basic_pair(source,target,board)
    spent=board['spent'].get(source['id'],{})
    if spent.get('standard') or (source['hp']<=0 and spent.get('move')):
        raise ValueError('La acción necesaria ya está gastada')
    # Old saved combats lack acted tracking: do not guess flat-footed status.
    if 'acted' not in board:raise ValueError('Reinicia este combate antiguo para activar el ataque automático')
    flat=target['id'] not in board['acted']
    armor=target_profile['flatAc'] if flat else target['ac']
    # Flanking for same-size, 5-foot-reach combatants: opposite adjacent squares.
    flanking=False
    for ally in board_scenes.characters(state):
        if ally['id']==source['id'] or ally['enemy']!=source['enemy'] or ally['hp']<=0 or ally.get('conditions','').strip():continue
        if not ally.get('meleeProfile') or not adjacent(ally,target):continue
        if (ally['x']-target['x'],ally['y']-target['y'])==(-(source['x']-target['x']),-(source['y']-target['y'])):
            flanking=True
    modifier=source['attack']+(2 if flanking else 0)
    return source,target,source_profile,spent,flat,armor,flanking,modifier


def attack(state,body,actor,dice):
    source,target,source_profile,spent,flat,armor,flanking,modifier=attack_context(state,body,actor)
    board=state['board']
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
    if damage:
        target['stable']=False;pf_recovery.clear_episode(target)
    spent={**spent,'standard':True}
    board['spent'][source['id']]=spent
    if source['hp']<=0:
        source['hp']-=1;source['stable']=False  # Strenuous standard action while disabled.
        pf_recovery.clear_episode(source)
    result={'attacker':source['id'],'target':target['id'],'roll':raw,'modifier':modifier,
            'ac':armor,'flatFooted':flat,'flanking':flanking,'hit':hit,'confirmation':confirmation,
            'critical':critical,'damageRolls':damage_rolls,'damage':damage,'targetHp':target['hp'],
            'status':health_status(target),'attackerHp':source['hp'],'attackerStatus':health_status(source),
            'origin':'físico' if physical is not None else 'servidor'}
    return result
