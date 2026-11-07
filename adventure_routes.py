"""Authored solo routes between verified quiet investigations. No travel simulation.

TREY, Spanish v1.0, PDF/printed p.12: number scenes when context changes.
Each visit is a new scene; revisiting never resets discoveries or grants FH.
"""
import copy
import json
import time
from pathlib import Path
import adventure_modules as modules


def builtin():
    return validate(json.loads((Path(__file__).parent/'adventures'/'senderos-del-archivo.json').read_text(encoding='utf-8')))


def validate(raw):
    if (not isinstance(raw,dict) or set(raw)!={'format','title','start','scenes'}
        or raw['format']!='cronicas-route-1'):
        raise ValueError('Formato de ruta incompatible: utiliza cronicas-route-1')
    if len(json.dumps(raw,ensure_ascii=False).encode('utf-8'))>192000:
        raise ValueError('La ruta supera 192.000 bytes')
    result={'format':raw['format'],'title':modules._text(raw['title'],150),'start':modules._id(raw['start']),'scenes':[]}
    if not isinstance(raw['scenes'],list) or not 2<=len(raw['scenes'])<=8:
        raise ValueError('La ruta admite de dos a ocho escenas')
    ids=set()
    for scene in raw['scenes']:
        if not isinstance(scene,dict) or set(scene)!={'id','module','exits'}:raise ValueError('Escena de ruta inválida')
        identifier=modules._id(scene['id'])
        if identifier in ids:raise ValueError('Escena duplicada')
        ids.add(identifier)
        module=modules.validate_module(scene['module'])
        if not isinstance(scene['exits'],list) or len(scene['exits'])>8:raise ValueError('Máximo ocho salidas por escena')
        exits=[];exit_ids=set();clues={v['id'] for v in module['opportunities']}
        for exit in scene['exits']:
            if not isinstance(exit,dict) or set(exit)!={'id','label','to','requires'}:raise ValueError('Salida de ruta inválida')
            eid=modules._id(exit['id']);target=modules._id(exit['to']);requirements=exit['requires']
            if eid in exit_ids or target==identifier:raise ValueError('Salida duplicada o hacia la misma escena')
            exit_ids.add(eid)
            if (not isinstance(requirements,list) or len(requirements)>8 or any(not isinstance(v,str) or v not in clues for v in requirements)
                or len(set(requirements))!=len(requirements)):raise ValueError('Requisitos de salida inválidos')
            exits.append({'id':eid,'label':modules._text(exit['label'],150),'to':target,'requires':list(requirements)})
        result['scenes'].append({'id':identifier,'module':module,'exits':exits})
    if result['start'] not in ids or any(e['to'] not in ids for s in result['scenes'] for e in s['exits']):
        raise ValueError('Destino de ruta inexistente')
    reached={result['start']}
    while True:
        updated=reached|{e['to'] for s in result['scenes'] if s['id'] in reached for e in s['exits']}
        if updated==reached:break
        reached=updated
    if reached!=ids:raise ValueError('La ruta contiene escenas inaccesibles')
    terminals={s['id'] for s in result['scenes'] if not s['exits']}
    can_finish=set(terminals)
    while True:
        updated=can_finish|{s['id'] for s in result['scenes'] if any(e['to'] in can_finish for e in s['exits'])}
        if updated==can_finish:break
        can_finish=updated
    if can_finish!=ids:raise ValueError('Toda escena debe permitir alcanzar un final')
    return result


def scene(state,identifier=None):
    key=identifier if identifier is not None else state['routeProgress']['current']
    return next(v for v in state['adventureRoute']['scenes'] if v['id']==key)


def install(state,raw):
    route=validate(raw)
    if len([c for c in state['characters'] if not c.get('enemy')])!=1:
        raise ValueError('Las rutas están disponibles solo con un personaje jugador')
    # Check every scene and exit prerequisite before modifying the campaign.
    for entry in route['scenes']:
        probe=copy.deepcopy(state);module=copy.deepcopy(entry['module'])
        required=list({v for e in entry['exits'] for v in e['requires']})
        if required:module['objectives']=[{'id':'route-check','text':'Validar acceso','requires':required}]
        modules.install(probe,module)
        modules.install(probe,entry['module'])
    state['adventureRoute']=route
    state['routeProgress']={'current':route['start'],'history':[route['start']],'saved':{}}
    modules.install(state,scene(state)['module'])


def public_view(state):
    if not state.get('adventureRoute'):return None
    current=scene(state);known={v['id'] for v in state['moduleProgress']['discoveries']}
    result={'title':state['adventureRoute']['title'],'current':current['id'],
        'visits':len(state['routeProgress']['history']),
        'completed':not current['exits'] and state['moduleProgress']['completed'],
        'exits':[{'id':e['id'],'label':e['label']} for e in current['exits'] if set(e['requires'])<=known]}
    if state.get('boardScenes'):
        all_progress={**state['routeProgress']['saved'],current['id']:state['moduleProgress']}
        result['visitedScenes']=[{'id':key,'title':scene(state,key)['module']['title'],
            'location':scene(state,key)['module']['location'],'completed':all_progress[key]['completed'],
            'discoveries':copy.deepcopy(all_progress[key]['discoveries'])}
            for key in dict.fromkeys(state['routeProgress']['history'])]
    return result


def travel(state,body,me):
    if not state.get('adventure') or not state.get('adventureRoute'):raise ValueError('No hay una ruta activa')
    if state.get('pfContinuation',{}).get('format')=='cronicas-pf-continuation-2':
        import pf_scene_transition
        reason=pf_scene_transition.limitation(state,active=True)
        if reason:raise ValueError(reason)
    if state['board']['active'] or state['pending']:raise ValueError('Resuelve el combate o las pruebas pendientes antes de cambiar de escena')
    pcs=[c for c in state['characters'] if not c.get('enemy')]
    if len(pcs)!=1:raise ValueError('El cambio de escena solo admite un personaje jugador')
    actor=pcs[0]
    if not me['host'] and actor['owner']!=me['id']:raise PermissionError('No controlas al personaje de esta ruta')
    if state.get('pfContinuation',{}).get('format')=='cronicas-pf-continuation-2' and actor['owner']!=me['id']:
        raise PermissionError('Solo el propietario decide la salida de su personaje')
    if actor.get('hp',0)<=0 or actor.get('conditions','').strip():raise ValueError('El estado del personaje requiere una resolución excepcional')
    if body.get('exit') not in {v['id'] for v in public_view(state)['exits']}:raise ValueError('Salida no disponible')
    progress=state['routeProgress']
    if len(progress['history'])>=1000:raise ValueError('Límite de 1.000 visitas por ruta alcanzado; conserva una exportación')
    exit=next(v for v in scene(state)['exits'] if v['id']==body['exit'])
    target=scene(state,exit['to']);probe=copy.deepcopy(state)
    if state.get('boardScenes'):
        import board_scenes
        if state['boardScenes']['current']!=progress['current']:raise ValueError('El tablero no coincide con la ruta actual')
        board_scenes.move_player(probe,target['id'],actor['id'],target['module']['location'])
    modules.install(probe,target['module'])  # Current sheet must still support the destination.
    if state.get('boardScenes'):
        for key in ('boardScenes','board','characters'):state[key]=probe[key]
    progress['saved'][progress['current']]=copy.deepcopy(state['moduleProgress'])
    restored=progress['saved'].pop(target['id'],None)
    progress['current']=target['id'];progress['history'].append(target['id'])
    modules.install(state,target['module'])
    if restored is not None:
        state['moduleProgress']=restored;modules.validate_restored(state)
    state['scene']+=1
    if state.get('boardScenes'):
        state['adventure'].update(summary=target['module']['description'],revision=state['adventure']['revision']+1,
            updatedAt=time.time(),source='Cambio de lugar confirmado; las búsquedas y reglas conservan su registro')
    state['messages'].append({'kind':'rules','speaker':'Motor de aventura','text':actor['name']+' elige: '+exit['label']+'. '+target['module']['description'],
        'time':time.time(),'routeTransition':{'from':progress['history'][-2],'to':target['id']},'refs':[{'book':'trey','page':12}]})


def validate_restored(state):
    if not state.get('adventureRoute'):
        if state.get('routeProgress'):raise ValueError('Progreso de ruta sin aventura')
        return
    route=validate(state['adventureRoute']);progress=state.get('routeProgress')
    if not isinstance(progress,dict) or set(progress)!={'current','history','saved'}:raise ValueError('Progreso de ruta inválido')
    history=progress['history'];ids={v['id'] for v in route['scenes']}
    if (not isinstance(history,list) or not 1<=len(history)<=1000 or any(not isinstance(v,str) or v not in ids for v in history)
        or history[0]!=route['start'] or history[-1]!=progress['current']):raise ValueError('Historial de ruta inválido')
    if type(state.get('scene'))!=int or state['scene']<len(history):raise ValueError('Numeración de escenas incompatible con las visitas')
    if not isinstance(progress['saved'],dict) or set(progress['saved'])!=set(history)-{progress['current']}:
        raise ValueError('Escenas guardadas inconsistentes')
    all_progress={**progress['saved'],progress['current']:state.get('moduleProgress')}
    for entry in route['scenes']:
        if entry['id'] not in all_progress:continue
        probe=copy.deepcopy(state);probe['adventureModule']=entry['module'];probe['moduleProgress']=all_progress[entry['id']]
        modules.validate_restored(probe)
    if state.get('adventureModule')!=scene(state)['module']:raise ValueError('El módulo activo no coincide con la ruta')
    for origin,target in zip(history,history[1:]):
        known={v['id'] for v in all_progress[origin]['discoveries']}
        if not any(e['to']==target and set(e['requires'])<=known for e in scene(state,origin)['exits']):
            raise ValueError('El historial contiene una transición no disponible')
    state['adventureRoute']=route
    if state.get('boardScenes'):
        scope=state['boardScenes']
        if scope['current']!=progress['current'] or set(scope['saved'])!=set(progress['saved']):
            raise ValueError('Los tableros no coinciden con las escenas visitadas')
