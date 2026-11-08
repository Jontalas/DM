"""One declared basic melee attack in the existing source-backed PF encounter."""
import board_scenes
import combat


def available(state):
    record=state.get('pfEncounter')
    if (not record or record['phase']!='combat' or state.get('mode','solo')!='solo'
        or state.get('ruleset','pathfinder-1e')!='pathfinder-1e' or not state['board']['active']
        or state['pending'] or state['location']!=record['definition']['location']):return None
    import pf_encounters
    if not pf_encounters.participants_present(state,record):return None
    actor=next((c for c in state['characters'] if c['id']==record['character']),None)
    if not actor or not actor.get('creation') or actor['creation'].get('manualOverride') or actor.get('enemy'):return None
    try:board_scenes.require_no_remote_events(state)
    except ValueError:return None
    targets=[]
    for target in board_scenes.characters(state):
        if (target['id']!=record['npc'] or not target.get('npcCreation')
            or target['npcCreation'].get('manualOverride')):continue
        try:combat.attack_context(state,{'character':actor['id'],'target':target['id']},{'id':actor['owner'],'host':False})
        except (ValueError,PermissionError):continue
        targets.append(target['id'])
    return {'character':actor['id'],'targets':targets,'exertionHpCost':int(actor['hp']<=0)} if targets else None


def declaration_available(state):
    if not state.get('messages') or state['messages'][-1].get('kind')!='action':return None
    return available(state)


def apply(state,item,body,me):
    if not isinstance(item,dict) or set(item)!={'target'} or not isinstance(item['target'],str):
        raise ValueError('El ataque solo identifica a un adversario preparado disponible')
    if body.get('type')!='talk' or body.get('kind')!='action':raise ValueError('El ataque requiere una declaración de acción')
    choices=declaration_available(state)
    if not choices or item['target'] not in choices['targets']:raise ValueError('Ese ataque no está disponible ahora')
    actor=next(c for c in state['characters'] if c['id']==choices['character'])
    if actor['owner']!=me['id'] or body.get('character') not in (None,actor['id']):raise PermissionError('Solo el propietario decide atacar con su personaje')
    from engine import apply_action
    apply_action(state,{'type':'attack','character':actor['id'],'target':item['target']},me)
