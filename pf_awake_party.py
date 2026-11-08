"""Match today's patients to the replayed first shared recovery episode.

This certificate does not advance time or certify a rest/daily healing action.
The caller must separately authorize the scene and player decision.
"""
import pf_recovery
import pf_shared_recovery


def verified(state):
    record=state.get('pfEncounter') or {}
    if (record.get('phase')!='defeated' or record.get('definition',{}).get('recoveryScope')!='shared-patients-1'
        or state['board'].get('combatSerial')!=1 or state['board']['active']
        or len(state['characters'])!=2 or record.get('recoveryLimit')):return False
    try:
        result=pf_shared_recovery.validate_record(record)
        if not result or result['status']!='conscious' or record['recoveryStart']['epoch']!=1:return False
        pf_recovery.validate_restored(state)
        current={c['id']:c for c in state['characters']}
        for expected in result['patients']:
            character=current[expected['id']]
            if any(character.get(key)!=expected.get(key) for key in ('hp','recoveryCare','recoveryState')):return False
            if bool(character.get('stable',False))!=expected['stable'] or character['abilities'][2]!=expected['abilities'][2]:return False
            if (character.get('conditions','').strip() or character.get('creation',{}).get('manualOverride')
                or character.get('npcCreation',{}).get('manualOverride')):return False
            if character['hp']>-character['abilities'][2] and not pf_recovery.is_conscious(character):return False
        return True
    except (ValueError,TypeError,KeyError,IndexError):return False
