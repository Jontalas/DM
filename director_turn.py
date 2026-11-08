"""Explicitly end the owner's turn in the prepared two-participant encounter.

Reuses engine turn advancement and deterministic NPC automation. Core PDF179,
printed178: initiative cycle; no delay, ready, surprise or player action chosen.
"""
import board_scenes


def available(state):
    record=state.get('pfEncounter');board=state['board']
    if (not record or record['phase']!='combat' or state.get('mode','solo')!='solo'
        or state.get('ruleset','pathfinder-1e')!='pathfinder-1e' or not board['active']
        or not board.get('autoEnemies') or board.get('autoPaused') or state['pending']
        or state['location']!=record['definition']['location'] or board.get('terrain')):return None
    actors={c['id']:c for c in board_scenes.characters(state)}
    if set(actors)!={record['character'],record['npc']} or len(board['order'])!=2 or {v['id'] for v in board['order']}!=set(actors):return None
    actor=actors[record['character']];npc=actors[record['npc']]
    if (board['order'][board['turn']]['id']!=actor['id'] or actor.get('enemy') or not npc.get('enemy') or actor['hp']<0 or npc['hp']<=0
        or not actor.get('creation') or not npc.get('npcCreation') or not npc.get('meleeProfile')
        or any(c.get('conditions','').strip() or c.get('creation',c.get('npcCreation',{})).get('manualOverride') for c in (actor,npc))):return None
    try:board_scenes.require_no_remote_events(state)
    except ValueError:return None
    return {'character':actor['id']}


def declaration_available(state):
    if not state.get('messages') or state['messages'][-1].get('kind')!='action':return None
    choice=available(state)
    if choice:
        actor=next(c for c in state['characters'] if c['id']==choice['character'])
        if state['messages'][-1].get('owner')!=actor['owner']:return None
    return choice


def apply(state,item,body,me):
    if not isinstance(item,dict) or set(item)!={'character'} or not isinstance(item['character'],str):raise ValueError('El fin de turno identifica únicamente al personaje actual')
    if body.get('type')!='talk' or body.get('kind')!='action':raise ValueError('Terminar turno requiere una declaración de acción')
    choice=declaration_available(state)
    if not choice or item!=choice:raise ValueError('No puedes terminar ese turno mediante esta declaración')
    actor=next(c for c in state['characters'] if c['id']==item['character'])
    if actor['owner']!=me['id'] or body.get('character') not in (None,actor['id']):raise PermissionError('Solo el propietario decide terminar su turno')
    from engine import apply_action
    apply_action(state,{'type':'turn'},me)
