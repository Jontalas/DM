"""Quiet move-action searches/walking at zero HP, only the authored 1.12 scene.

Core PDF190/568: disabled movement is not strenuous; PDF101: deliberate
Perception is a move action. No combat timing, rest, healing or negative-HP
medical calendar is certified by this capability.
"""
SCOPE='zero-hp-light-exploration-1'


def eligible(state,character):
    record=state.get('pfEncounter') or {}
    definition=record.get('definition') or {}
    if (definition.get('explorationScope')!=SCOPE or definition.get('version')!='1.12.0'
        or record.get('phase') not in ('agreement','resolved','defeated')
        or state['board']['active'] or state['board']['terrain']
        or len(state['characters'])!=2 or character.get('id')!=record.get('character')
        or character.get('hp')!=0 or character.get('enemy')):return False
    if any(c.get('conditions','').strip() or c.get('creation',{}).get('manualOverride')
        or c.get('npcCreation',{}).get('manualOverride') for c in state['characters']):return False
    if any(not event.get('interpreted') for event in state['consequences']):return False
    npc=next((c for c in state['characters'] if c['id']==record.get('npc')),None)
    if npc is None:return False
    if -npc['abilities'][2]<npc['hp']<0:
        import pf_npc_wait
        if not pf_npc_wait.can_remain_awake(state,npc):return False
    # Rebuild relevant immutable statistics; never grant coverage from a view or
    # a manually edited sheet merely carrying creator metadata.
    try:
        import character_builder
        built,_=character_builder.build(character['creation']['choices'])
        return all(character.get(key)==built[key] for key in ('abilities','maxHp','level','speed','skillTotals'))
    except (KeyError,TypeError,ValueError):return False


def public_view(state):
    record=state.get('pfEncounter') or {}
    if (record.get('definition') or {}).get('explorationScope')!=SCOPE:return None
    character=next((c for c in state['characters'] if c['id']==record.get('character')),None)
    return {'character':record.get('character'),'canExplore':bool(character and eligible(state,character))}
