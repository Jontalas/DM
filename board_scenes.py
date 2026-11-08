"""Optional scene scope for the existing board; no IO, RNG or travel clock.

Unscoped campaigns retain their existing single-board behavior. A caller must
authorize a narrative transition before moving its one player between scenes.
"""
import copy
import re

FORMAT='cronicas-board-scenes-1'


def director_view(state):
    """Current board stays in state.board; archives supply names/positions only."""
    scenes=state.get('boardScenes')
    if not isinstance(scenes,dict) or scenes.get('format')!=FORMAT:return None
    return {'format':'cronicas-board-scenes-context-1','current':scenes['current'],
        'knownScenes':{key:{'name':entry['name'],'positions':copy.deepcopy(entry['positions'])}
            for key,entry in scenes['saved'].items()}}


def _id(value):
    if not isinstance(value,str) or not re.fullmatch(r'[a-z][a-z0-9_-]{0,39}',value):raise ValueError('Identificador de tablero inválido')
    return value


def _point(value):
    if not isinstance(value,(list,tuple)) or len(value)!=2 or any(type(v)!=int or not 0<=v<20 for v in value):raise ValueError('Posición de escena fuera del tablero')
    return list(value)


def _terrain(value):
    if not isinstance(value,dict) or len(value)>400:raise ValueError('Terreno de escena inválido')
    for key,tile in value.items():
        if not isinstance(key,str) or not re.fullmatch(r'(?:[0-9]|1[0-9]),(?:[0-9]|1[0-9])',key) or tile not in ('clear','wall','difficult'):
            raise ValueError('Casilla de escena inválida')


def characters(state):
    scenes=state.get('boardScenes')
    return state['characters'] if scenes is None else [c for c in state['characters'] if c.get('sceneId')==scenes['current']]


def present(state,character):
    return state.get('boardScenes') is None or character.get('sceneId')==state['boardScenes']['current']


def require_present(state,*participants):
    if any(not present(state,c) for c in participants):raise ValueError('La ficha pertenece a otra escena; no puede actuar en este tablero')


def require_no_remote_events(state):
    if state.get('boardScenes') is None:return
    import pf_light_exploration
    for character in state['characters']:
        if not present(state,character) and (character.get('conditions','').strip()
            or -character['abilities'][2]<character['hp']<0 and not pf_light_exploration.can_remain_awake(state,character)):
            raise ValueError('Un participante de otra escena necesita resolver recuperación o condiciones; no se omite su seguimiento')


def validate_restored(state):
    if not isinstance(state.get('characters'),list) or any(not isinstance(c,dict) for c in state['characters']):raise ValueError('Lista de fichas inválida')
    scenes=state.get('boardScenes')
    if scenes is None:
        if any('sceneId' in c for c in state['characters']):raise ValueError('Ficha con escena pero sin tableros guardados')
        return
    if (not isinstance(scenes,dict) or set(scenes)!={'format','current','saved'} or scenes['format']!=FORMAT
        or not isinstance(scenes['saved'],dict) or len(scenes['saved'])>31):raise ValueError('Estado de tableros inválido')
    current=_id(scenes['current']);saved=scenes['saved']
    if current in saved:raise ValueError('El tablero actual no duplica un tablero archivado')
    for key in saved:_id(key)
    identifiers=[c.get('id') for c in state['characters']]
    if any(not isinstance(v,str) or not v for v in identifiers):raise ValueError('Identidades de ficha inválidas')
    ids=set(identifiers);occupied=set()
    if len(ids)!=len(identifiers):raise ValueError('Identidades de ficha duplicadas')
    _terrain(state['board']['terrain'])
    for c in state['characters']:
        scene_id=c.get('sceneId');_id(scene_id)
        if scene_id!=current and scene_id not in saved:raise ValueError('La ficha pertenece a una escena inexistente')
        point=_point([c.get('x'),c.get('y')]);place=(scene_id,*point)
        if place in occupied:raise ValueError('Dos fichas ocupan la misma casilla de una escena')
        occupied.add(place)
    for key,entry in saved.items():
        if (not isinstance(entry,dict) or set(entry)!={'name','terrain','positions'}
            or not isinstance(entry['name'],str) or not entry['name'].strip() or len(entry['name'])>200
            or not isinstance(entry['positions'],dict) or len(entry['positions'])>400 or not set(entry['positions'])<=ids):
            raise ValueError('Tablero archivado inválido')
        _terrain(entry['terrain']);points=[tuple(_point(v)) for v in entry['positions'].values()]
        if len(points)!=len(set(points)):raise ValueError('Posiciones archivadas superpuestas')
        for c in state['characters']:
            if c['sceneId']==key and entry['positions'].get(c['id'])!=[c['x'],c['y']]:raise ValueError('La ficha ausente no coincide con su posición guardada')
    if state['board']['active']:
        order=state['board']['order'];present_ids={c['id'] for c in characters(state)}
        if (not isinstance(order,list) or not order or any(not isinstance(v,dict) or v.get('id') not in present_ids for v in order)
            or len({v['id'] for v in order})!=len(order)
            or type(state['board']['turn'])!=int or not 0<=state['board']['turn']<len(order)):
            raise ValueError('La iniciativa contiene fichas de otra escena o un turno inválido')


def initialize(state,scene_id):
    _id(scene_id)
    validate_restored(state)
    if state.get('boardScenes') is not None:raise ValueError('Los tableros ya están inicializados')
    if state['board']['active'] or state['pending']:raise ValueError('Resuelve primero combate y pruebas pendientes')
    updated=copy.deepcopy(state)
    updated['boardScenes']={'format':FORMAT,'current':scene_id,'saved':{}}
    for c in updated['characters']:c['sceneId']=scene_id
    validate_restored(updated);state.clear();state.update(updated)


def move_player(state,destination,character_id,name,entry=(0,0)):
    """Internal transition only; the caller owns permissions and exit legality."""
    validate_restored(state);_id(destination);entry=_point(entry)
    scenes=state.get('boardScenes')
    if scenes is None:raise ValueError('La ruta no tiene tableros preparados')
    if destination==scenes['current']:raise ValueError('Ya estás en este tablero')
    if not isinstance(name,str) or not name.strip() or len(name)>200:raise ValueError('Nombre de escena inválido')
    if state['board']['active'] or state['pending']:raise ValueError('No se cambia de tablero con combate o pruebas pendientes')
    import pf_light_exploration
    if any(c.get('conditions','').strip() or -c['abilities'][2]<c['hp']<0 and not pf_light_exploration.can_remain_awake(state,c) for c in state['characters']):
        raise ValueError('El cambio requiere resolver primero recuperación o condiciones; no se omite su reloj')
    actor=next((c for c in characters(state) if c['id']==character_id and not c.get('enemy')),None)
    import pf_light_exploration
    if actor is None or actor['hp']<=0 and not pf_light_exploration.eligible(state,actor):raise ValueError('El viajero necesita un estado cubierto para caminar entre escenas')
    if len(scenes['saved'])>=31 and destination not in scenes['saved']:raise ValueError('Límite de32 tableros alcanzado')
    updated=copy.deepcopy(state);scope=updated['boardScenes'];origin=scope['current']
    target=scope['saved'].pop(destination,{'name':name,'terrain':{},'positions':{}})
    if target['name']!=name:raise ValueError('El destino no coincide con su nombre guardado')
    scope['saved'][origin]={'name':state['location'],'terrain':copy.deepcopy(state['board']['terrain']),
        'positions':{c['id']:[c['x'],c['y']] for c in characters(state)}}
    traveller=next(c for c in updated['characters'] if c['id']==character_id)
    traveller['sceneId']=destination;traveller['x'],traveller['y']=target['positions'].get(character_id,entry)
    scope['current']=destination
    board=updated['board'];board.update(active=False,round=1,turn=0,order=[],spent={},acted=[],terrain=copy.deepcopy(target['terrain']))
    board.pop('autoPaused',None);updated['location']=name
    validate_restored(updated);state.clear();state.update(updated)
