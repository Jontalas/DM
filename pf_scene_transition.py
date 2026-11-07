"""Explicit, zero-inference transition within the same prepared courtyard.

No travel, healing, elapsed-time estimate, player speech or NPC resurrection.
The existing neutral Perception module owns subsequent checks (Core PDF87/101).
"""
import copy
import hashlib
import json
from pathlib import Path
from rule_pack_authoring import canonical

LINK={'id':'recibo-del-patio','version':'1.0.0'}
ROUTE_LINK={'id':'envio-del-peaje','version':'1.0.0'}


def module():
    import adventure_modules
    raw=json.loads((Path(__file__).parent/'adventures'/'pf-recibo-del-patio-1.0.0.json').read_text(encoding='utf-8'))
    return adventure_modules.validate_module(raw)


def route():
    import adventure_routes
    raw=json.loads((Path(__file__).parent/'adventures'/'pf-envio-del-peaje-1.0.0.json').read_text(encoding='utf-8'))
    return adventure_routes.validate(raw)


def limitation(state,*,active=False):
    record=state.get('pfEncounter')
    if not record or record['definition'].get('continuation') not in (LINK,ROUTE_LINK):return 'Esta versión no incluye la siguiente escena.'
    routed=record['definition'].get('continuation')==ROUTE_LINK
    if state.get('pfContinuation') and not active:return 'La investigación del patio ya está iniciada.'
    if record['phase'] not in ('agreement','resolved','defeated') or state['board']['active']:return 'Resuelve primero el encuentro.'
    if not active and any(state.get(k) for k in ('adventure','adventureModule','adventureRoute')):return 'Ya hay otra aventura iniciada.'
    if routed and not active and state.get('boardScenes'):return 'La entrada no sustituye tableros ya preparados.'
    if state['pending'] or state['board']['terrain'] or any(not e.get('interpreted') for e in state['consequences']):return 'Resuelve primero las situaciones pendientes de la mesa.'
    if len(state['characters'])!=2:return 'Este enlace cubre únicamente a los dos participantes preparados.'
    actors={c['id']:c for c in state['characters']}
    actor=actors.get(record['character']);npc=actors.get(record['npc'])
    if not actor or not npc:return 'Falta un participante del encuentro.'
    if actor['hp']<=0:return 'La investigación requiere un personaje con PG positivos; no se simula su descanso.'
    if -npc['abilities'][2]<npc['hp']<0:return 'La guardiana aún necesita seguimiento de recuperación; no se omiten sus pruebas.'
    if any(c.get('conditions','').strip() for c in (actor,npc)) or actor['creation'].get('manualOverride') or npc['npcCreation'].get('manualOverride'):return 'Las condiciones o correcciones necesitan una resolución fuera de esta escena tranquila.'
    expected=state.get('adventureModule',{}).get('location') if routed and active else record['definition']['location']
    if state['location']!=expected:return 'La localización no coincide con la escena preparada.'
    if routed and active and (not state.get('boardScenes') or state['boardScenes']['current']!=state.get('routeProgress',{}).get('current')):
        return 'El tablero no coincide con la escena de la ruta.'
    return None


def enter(state,body,me):
    if body.get('type')!='continue_pf_encounter' or set(body)-{'type','id','version'}:raise ValueError('Continuación no disponible')
    import pf_encounters
    pf_encounters.validate_restored(state)
    record=state.get('pfEncounter')
    actor=next((c for c in state['characters'] if record and c['id']==record['character']),None)
    if not actor or actor['owner']!=me['id']:raise PermissionError('Solo el propietario decide si continúa investigando')
    reason=limitation(state)
    if reason:raise ValueError(reason)
    import adventure_modules
    import adventure
    from engine import log
    routed=record['definition'].get('continuation')==ROUTE_LINK
    itinerary=route() if routed else None
    content=next(v['module'] for v in itinerary['scenes'] if v['id']==itinerary['start']) if routed else module()
    if content['location']!=state['location']:raise ValueError('El enlace no puede cambiar la localización')
    result=copy.deepcopy(state)
    if routed:
        import adventure_routes
        import board_scenes
        adventure_routes.install(result,itinerary)
        board_scenes.initialize(result,itinerary['start'])
    else:adventure_modules.install(result,content)
    adventure.apply_memory(result,{'summary':content['description'],'location':content['location'],
        'goal':content['goal'],'objectives':result['objectives'],'preparation':content['preparation']},starting=True)
    result['adventure']['source']='Escena original preparada; no certifica reglas fuera de su cobertura'
    result['pfContinuation']={'format':'cronicas-pf-continuation-2' if routed else 'cronicas-pf-continuation-1','encounterSha256':record['sha256'],
        'routeSha256' if routed else 'moduleSha256':hashlib.sha256(canonical(itinerary if routed else content).encode()).hexdigest(),'entryPhase':record['phase']}
    log(result,content['description']+' No se avanza tiempo, no se recuperan PG y no se mueve ninguna ficha al consultar esta situación.')
    state.clear();state.update(result)


def validate_restored(state):
    receipt=state.get('pfContinuation')
    if receipt is None:
        if state.get('pfEncounter',{}).get('definition',{}).get('continuation') in (LINK,ROUTE_LINK) and any(state.get(k) for k in ('adventure','adventureModule','adventureRoute')):
            raise ValueError('La escena enlazada necesita su registro de continuidad')
        return
    record=state.get('pfEncounter')
    if isinstance(receipt,dict) and receipt.get('format')=='cronicas-pf-continuation-2':
        import adventure_routes
        import board_scenes
        original=route()
        if (set(receipt)!={'format','encounterSha256','routeSha256','entryPhase'} or not record
            or record['definition'].get('continuation')!=ROUTE_LINK or receipt['encounterSha256']!=record['sha256']
            or receipt['entryPhase'] not in ('agreement','resolved','defeated')
            or receipt['routeSha256']!=hashlib.sha256(canonical(original).encode()).hexdigest()
            or canonical(state.get('adventureRoute'))!=canonical(original) or not state.get('adventure') or not state.get('boardScenes')):
            raise ValueError('La ruta del patio no coincide con su contenido original')
        board_scenes.validate_restored(state);adventure_routes.validate_restored(state)
        scope=state['boardScenes'];progress=state['routeProgress']
        if scope['current']!=progress['current'] or set(scope['saved'])!=set(progress['saved']):raise ValueError('Los tableros visitados no coinciden con la ruta')
        for c in state['characters']:
            if c['id']==record['character'] and c['sceneId']!=progress['current']:raise ValueError('El PJ no está en la escena actual')
            if c['id']==record['npc'] and c['sceneId']!=original['start']:raise ValueError('La guardiana conserva su escena del patio')
        return
    content=module()
    if (not isinstance(receipt,dict) or set(receipt)!={'format','encounterSha256','moduleSha256','entryPhase'}
        or receipt['format']!='cronicas-pf-continuation-1' or not record or record['definition'].get('continuation')!=LINK
        or receipt['encounterSha256']!=record['sha256'] or receipt['entryPhase'] not in ('agreement','resolved','defeated')
        or receipt['moduleSha256']!=hashlib.sha256(canonical(content).encode()).hexdigest()
        or canonical(state.get('adventureModule'))!=canonical(content) or not state.get('adventure')):
        raise ValueError('La continuidad del patio no coincide con su escena original')
