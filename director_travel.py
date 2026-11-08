"""Allowlisted route choices from an explicit player declaration, no inference here."""
import adventure_routes


def available(state):
    if (not state.get('adventureRoute') or not state.get('adventure') or state.get('ruleset','pathfinder-1e')!='pathfinder-1e'
        or state.get('mode','solo')!='solo' or state['board']['active'] or state['pending']
        or len(state.get('routeProgress',{}).get('history',[]))>=1000):return None
    actors=[c for c in state['characters'] if not c.get('enemy')]
    if len(actors)!=1 or actors[0]['hp']<=0 or actors[0].get('conditions','').strip():return None
    if state.get('pfContinuation'):
        import pf_scene_transition
        if pf_scene_transition.limitation(state,active=True):return None
    exits=adventure_routes.public_view(state)['exits']
    return {'character':actors[0]['id'],'exits':exits} if exits else None


def declaration_available(state):
    if not state.get('messages') or state['messages'][-1].get('kind')!='action':return None
    return available(state)


def apply(state,item,body,me):
    if not isinstance(item,dict) or set(item)!={'exit'} or not isinstance(item['exit'],str):
        raise ValueError('El viaje propuesto solo puede identificar una salida disponible')
    if body.get('type')!='talk' or body.get('kind')!='action':raise ValueError('El viaje requiere una declaración de acción del jugador')
    choices=declaration_available(state)
    if not choices or item.get('exit') not in {e['id'] for e in choices['exits']}:
        raise ValueError('La salida propuesta no está disponible en esta declaración')
    actor=next(c for c in state['characters'] if c['id']==choices['character'])
    if actor['owner']!=me['id'] or body.get('character') not in (None,actor['id']):
        raise PermissionError('Solo el propietario declara el viaje de su personaje')
    adventure_routes.travel(state,{'type':'travel_scene','exit':item['exit']},me)
