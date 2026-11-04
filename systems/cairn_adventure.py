"""Native Cairn scene mechanics; original scene, no Pathfinder checks.

Rules: Cairn 1e SRD (Yochai Gal, CC BY-SA 4.0), Saves, Healing, Ability Score Loss;
first-edition FAQ / How is damage awarded outside of combat?
https://cairnrpg.com/first-edition/frequently-asked-questions/
Changes: deterministic application to an explicitly authored non-combat risk.
"""
import copy
import json
import secrets
import time
from functools import lru_cache
from pathlib import Path
from systems import cairn_1e as rules,cairn_creator as creator


@lru_cache(maxsize=1)
def _module():
    return json.loads((Path(__file__).resolve().parents[1]/'adventures'/'cairn-la-pasarela.json').read_text(encoding='utf-8'))


def module():return copy.deepcopy(_module())


def status(character):
    values=character['abilities']
    return {'dead':values['STR']==0,'paralyzed':values['DEX']==0,'delirious':values['WIL']==0,
        'canAct':all(values[k]>0 for k in rules.ABILITIES)}


def _actor(state,identifier,me):
    actor=next((c for c in state['characters'] if c['id']==identifier),None)
    if actor is None:raise ValueError('Personaje no disponible')
    if actor['owner']!=me['id']:raise PermissionError('No controlas este personaje')
    return actor


def _log(state,text,identifier):
    state['messages'].append({'kind':'rules','speaker':'Motor de Cairn','text':text,'time':time.time(),'character':identifier})


def replay(character,events):
    """Replay only supported mechanics from canonical creation, including recovery."""
    current=creator.finalize(character['creation']['draft'],character['creation']['choices'],character['owner'])
    completed=False;days=0;results=[]
    if not isinstance(events,list) or len(events)>2000:raise ValueError('Registro de consecuencias inválido')
    routes={r['id']:r for r in _module()['routes']}
    for event in events:
        if not isinstance(event,dict):raise ValueError('Suceso de Cairn inválido')
        if event.get('kind')=='rest':
            if set(event)!={'kind'} or current['abilities']['STR']==0:raise ValueError('Recuperación no disponible')
            current['abilities']=copy.deepcopy(current['maxAbilities'])
            current['hitProtection']=0 if current['inventorySlots']==10 else current['maxHitProtection']
            days+=7;results.append({'kind':'rest','days':7})
            continue
        if set(event)!={'kind','route','raw','damage'} or event['kind']!='route' or completed:
            raise ValueError('Consecuencia de ruta inválida')
        if not isinstance(event['route'],str) or event['route'] not in routes or not status(current)['canAct']:
            raise ValueError('Ruta o estado del personaje no disponible')
        route=routes[event['route']];damage=event['damage']
        if type(damage)!=int:raise ValueError('Lesión de escena inválida')
        if route['save'] is None:
            if event['raw'] is not None or damage!=0:raise ValueError('El sendero seguro no requiere dados')
            completed=True;results.append({'kind':'route','route':route['id'],'success':True})
        else:
            result=rules.save(current,'DEX',event['raw'])
            if result['success']:
                if damage!=0:raise ValueError('Un éxito no aplica la lesión del fallo')
                completed=True
            else:
                if not 1<=damage<=4:raise ValueError('La lesión debe proceder del d4 anunciado')
                current['abilities']['DEX']=max(0,current['abilities']['DEX']-damage)
            results.append({'kind':'route','route':route['id'],**result,'effectApplied':True,'damage':damage,'dexAfter':current['abilities']['DEX']})
    return current,completed,days,results


def apply(state,body,me,draw=None):
    action={k:v for k,v in body.items() if k not in ('id','version')};kind=action.get('type')
    draw=draw or (lambda sides:secrets.randbelow(sides)+1)
    result=copy.deepcopy(state)
    if kind=='start_cairn_adventure':
        if set(action)!={'type','character'}:raise ValueError('Inicio de escena inválido')
        if not me['host']:raise PermissionError('Solo el anfitrión inicia la aventura compartida')
        if state.get('adventure'):raise ValueError('La aventura ya está iniciada')
        if len(state['characters'])!=1:raise ValueError('Esta primera escena admite un personaje jugador')
        actor=next((c for c in state['characters'] if c['id']==action['character']),None)
        if not actor or not status(actor)['canAct']:raise ValueError('Selecciona un personaje listo para actuar')
        result['adventure']={'module':'la-pasarela','character':actor['id'],'events':[],'pending':None,'completed':False,'elapsedDays':0}
        _log(result,_module()['description'],actor['id']);return result
    progress=result.get('adventure')
    if not progress:raise ValueError('Inicia primero una aventura de Cairn')
    actor=_actor(result,progress['character'],me)
    if kind=='choose_route':
        if set(action)!={'type','route'}:raise ValueError('Elección de ruta inválida')
        if progress['pending'] or progress['completed'] or not status(actor)['canAct']:raise ValueError('No puedes iniciar ahora otra ruta')
        route=next((r for r in _module()['routes'] if r['id']==action['route']),None)
        if route is None:raise ValueError('Ruta no disponible')
        if route['save'] is not None:
            progress['pending']={'id':secrets.token_hex(12),'route':route['id'],'character':actor['id']}
            _log(result,'Declaras: '+route['label']+'. '+route['risk'],actor['id']);return result
        event={'kind':'route','route':route['id'],'raw':None,'damage':0}
    elif kind=='resolve_save':
        if set(action)-{'type','request','physical'} or not {'type','request'}<=set(action):raise ValueError('Resolución de salvación inválida')
        pending=progress['pending']
        if not pending or action['request']!=pending['id']:raise ValueError('Salvación pendiente no disponible')
        if pending['character']!=actor['id'] or pending['route']!='pasarela' or not status(actor)['canAct']:
            raise ValueError('La solicitud no coincide con la escena o el personaje')
        raw=action['physical'] if 'physical' in action else draw(20)
        saved=rules.save(actor,'DEX',raw)
        damage=0 if saved['success'] else draw(4)
        rules._dice([damage],1,4) if not saved['success'] else None
        event={'kind':'route','route':pending['route'],'raw':raw,'damage':damage}
    elif kind=='rest_and_recover':
        if set(action)!={'type'} or progress['pending'] or actor['abilities']['STR']==0:raise ValueError('El descanso no está disponible en este estado')
        if actor['abilities']==actor['maxAbilities'] and (actor['hitProtection']==actor['maxHitProtection'] or actor['inventorySlots']==10):
            raise ValueError('No hay pérdida de características o protección que recuperar')
        event={'kind':'rest'}
    else:raise ValueError('Acción de escena no implementada')
    progress['events'].append(event)
    restored,completed,days,results=replay(actor,progress['events'])
    actor['abilities']=restored['abilities'];actor['hitProtection']=restored['hitProtection']
    progress.update(completed=completed,elapsedDays=days,pending=None)
    last=results[-1]
    if last['kind']=='rest':text='Descansas una semana con los cuidados, comida y agua de Arda. Se recuperan tus características y la protección que permite tu carga.'
    elif last['success']:text=next(r['success'] for r in _module()['routes'] if r['id']==last['route'])
    else:text='La salvación de DEX falla. No completas el cruce; pierdes '+str(last['damage'])+' DEX y conservas '+str(last['dexAfter'])+'. No es daño de combate ni provoca otra salvación de daño crítico.'
    if 'raw' in last:text='Salvación de DEX: d20 '+str(last['raw'])+' frente a DEX '+str(last['target'])+' (éxito con valor igual o menor; 1 siempre sí, 20 siempre no). '+text
    _log(result,text,actor['id']);return result


def public_view(state):
    progress=state.get('adventure')
    if not progress:return None
    actor=next(c for c in state['characters'] if c['id']==progress['character'])
    _,_,_,results=replay(actor,progress['events'])
    return {'title':_module()['title'],'description':_module()['description'],'goal':_module()['goal'],
        'routes':copy.deepcopy(_module()['routes']),'healing':_module()['healing'],
        'character':actor['id'],'pending':copy.deepcopy(progress['pending']),'completed':progress['completed'],
        'elapsedDays':progress['elapsedDays'],'results':results[-10:]}


def validate_restored(state):
    progress=state.get('adventure')
    if progress is None:
        for actor in state['characters']:
            baseline=creator.finalize(actor['creation']['draft'],actor['creation']['choices'],actor['owner'])
            if actor['abilities']!=baseline['abilities'] or actor['hitProtection']!=baseline['hitProtection']:
                raise ValueError('Cambios mecánicos sin consecuencias registradas')
        return
    if (not isinstance(progress,dict) or set(progress)!={'module','character','events','pending','completed','elapsedDays'}
        or progress['module']!='la-pasarela'):raise ValueError('Progreso de Cairn inválido')
    actor=next((c for c in state['characters'] if c['id']==progress['character']),None)
    if actor is None:raise ValueError('La escena no tiene personaje válido')
    baseline,completed,days,_=replay(actor,progress['events'])
    if (type(progress['completed'])!=bool or progress['completed']!=completed or type(progress['elapsedDays'])!=int or progress['elapsedDays']!=days
        or actor['abilities']!=baseline['abilities'] or actor['hitProtection']!=baseline['hitProtection']):raise ValueError('Consecuencias de Cairn inconsistentes')
    pending=progress['pending']
    if pending is not None:
        if (not isinstance(pending,dict) or set(pending)!={'id','route','character'} or pending['route']!='pasarela'
            or pending['character']!=actor['id'] or not isinstance(pending['id'],str) or not 1<=len(pending['id'])<=100
            or completed or not status(actor)['canAct']):raise ValueError('Salvación importada inválida')
    for other in state['characters']:
        if other['id']!=actor['id']:
            validate_restored({'characters':[other],'adventure':None})
