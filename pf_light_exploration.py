"""Quiet move-action searches/walking for the authored 1.12/1.13 scenes.

Core PDF190/568: disabled movement is not strenuous; PDF101: deliberate
Perception is a move action. Negative HP requires the exact shared recovery
proof. No combat timing, rest, healing or new medical calendar is certified.
"""
SCOPE='zero-hp-light-exploration-1'
AWAKE_SCOPE='conscious-light-exploration-1'
ASSISTED_SCOPE='conscious-assisted-light-exploration-1'


def can_remain_awake(state,character):
    import pf_npc_wait
    if pf_npc_wait.can_remain_awake(state,character):return True
    record=state.get('pfEncounter') or {}
    if ((record.get('definition',{}).get('explorationScope'),record.get('definition',{}).get('version')) not in ((AWAKE_SCOPE,'1.13.0'),(ASSISTED_SCOPE,'1.14.0'))
        or character.get('id') not in (record.get('character'),record.get('npc'))):return False
    import pf_awake_party
    return pf_awake_party.verified(state)


def eligible(state,character):
    record=state.get('pfEncounter') or {}
    definition=record.get('definition') or {}
    if ((definition.get('explorationScope'),definition.get('version')) not in ((SCOPE,'1.12.0'),(AWAKE_SCOPE,'1.13.0'),(ASSISTED_SCOPE,'1.14.0'))
        or record.get('phase') not in ('agreement','resolved','defeated')
        or state['board']['active'] or state['board']['terrain']
        or len(state['characters'])!=2 or character.get('id')!=record.get('character')
        or type(character.get('hp'))!=int or not -character['abilities'][2]<character['hp']<=0 or character.get('enemy')):return False
    if character['hp']<0:
        import pf_awake_party
        if definition.get('explorationScope') not in (AWAKE_SCOPE,ASSISTED_SCOPE) or not pf_awake_party.verified(state):return False
    if any(c.get('conditions','').strip() or c.get('creation',{}).get('manualOverride')
        or c.get('npcCreation',{}).get('manualOverride') for c in state['characters']):return False
    if any(not event.get('interpreted') for event in state['consequences']):return False
    npc=next((c for c in state['characters'] if c['id']==record.get('npc')),None)
    if npc is None:return False
    if -npc['abilities'][2]<npc['hp']<0:
        if not can_remain_awake(state,npc):return False
    # Rebuild relevant immutable statistics; never grant coverage from a view or
    # a manually edited sheet merely carrying creator metadata.
    try:
        import character_builder
        built,_=character_builder.build(character['creation']['choices'])
        return all(character.get(key)==built[key] for key in ('abilities','maxHp','level','speed','skillTotals'))
    except (KeyError,TypeError,ValueError):return False


def public_view(state):
    record=state.get('pfEncounter') or {}
    if (record.get('definition') or {}).get('explorationScope') not in (SCOPE,AWAKE_SCOPE,ASSISTED_SCOPE):return None
    character=next((c for c in state['characters'] if c['id']==record.get('character')),None)
    return {'character':record.get('character'),'canExplore':bool(character and eligible(state,character))}
