"""Small, public authored facts; never action permissions or hidden clues."""


def public_facts(state):
    record=state.get('pfEncounter') or {};definition=record.get('definition') or {}
    if ((definition.get('version'),definition.get('explorationScope')) not in
        (('1.12.0','zero-hp-light-exploration-1'),('1.13.0','conscious-light-exploration-1'),('1.14.0','conscious-assisted-light-exploration-1'),('1.15.0','conscious-assisted-light-exploration-1'),('1.16.0','conscious-assisted-light-exploration-1'))
        or record.get('phase') not in ('agreement','resolved','defeated') or state['board']['active']):return None
    import pf_encounters
    from rule_pack_authoring import canonical
    if canonical(definition)!=canonical(pf_encounters.definition(definition['version'])):return None
    npc=next((c for c in state['characters'] if c['id']==record.get('npc')),None)
    if not npc or npc.get('conditions','').strip():return None
    import pf_recovery
    if not pf_recovery.is_conscious(npc):return None
    if npc['hp']<0:
        import pf_light_exploration
        if not pf_light_exploration.can_remain_awake(state,npc):return None
    return {'format':'cronicas-prepared-public-facts-1','npc':npc['id'],
        'publicDocumentsAccess':'already-permitted',
        'fact':'La guardiana permite consultar los papeles públicos del peaje: el registro y el recibo del patio. No exige una nueva negociación, justificación, favor, pago ni tirada para ese permiso.',
        'boundary':'El jugador todavía elige si investiga y qué revisa. Tener permiso no descubre pistas ni realiza búsquedas, desplazamientos, curación o descanso. El motor valida cada acción.'}
