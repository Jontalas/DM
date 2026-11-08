"""Shared bounded fictional memory for explicitly enabled PF adventures.

No rules, actor statistics or player decisions. Uses the package world's
existing validators rather than creating a second entity/visibility model.
"""
import copy
import rule_pack_world as world

CONTRACT='structured-world-memory-1'
FORMAT='cronicas-campaign-world-1'
FIELDS={'format','revision','npcs','places','relationships'}


def empty():
    return {'format':FORMAT,'revision':0,'npcs':[],'places':[],'relationships':[]}


def validate(record):
    if (not isinstance(record,dict) or set(record)!=FIELDS or record['format']!=FORMAT
        or type(record['revision'])!=int or not 0<=record['revision']<=1000000):
        raise ValueError('Memoria estructurada del mundo inválida')
    world.validate(record['npcs']);world.validate_places(record['places'])
    world.validate_relationships(record['relationships'],record['npcs'],record['places'])
    return copy.deepcopy(record)


def apply(record,updates):
    """Validate all updates before returning a new independent record."""
    result=validate(record)
    if (not isinstance(updates,dict) or set(updates)!={'npcs','places','relationships'}
        or any(not isinstance(updates[k],list) for k in updates)
        or sum(len(v) for v in updates.values())>3):
        raise ValueError('Como máximo tres notas de PNJ, lugares o relaciones por intervención')
    result['npcs']=world.merge(result['npcs'],updates['npcs'])
    result['places']=world.merge_places(result['places'],updates['places'])
    result['relationships']=world.merge_relationships(result['relationships'],updates['relationships'],result['npcs'],result['places'])
    if result!=record:result['revision']+=1
    return validate(result)


def public_view(record):
    record=validate(record)
    return {'revision':record['revision'],'npcs':world.public_view(record['npcs']),
        'places':world.public_view(record['places']),
        'relationships':world.public_relationships(record['relationships'],record['npcs'],record['places'])}


def updates_schema():
    return {'type':'object','properties':{'npcs':world.schema(),'places':world.schema(),'relationships':world.relationship_schema()},
        'required':['npcs','places','relationships'],'additionalProperties':False}


def enabled(state):
    return state.get('ruleset','pathfinder-1e')=='pathfinder-1e' and 'campaignWorld' in state


def validate_turn(state,updates,*,rules=False,starting=False,result=None):
    if rules or not enabled(state) or not (starting or state.get('adventure')):
        raise ValueError('Esta intervención no admite memoria estructurada del mundo')
    candidate=apply(state['campaignWorld'],updates)
    changed=candidate!=state['campaignWorld']
    if changed and not starting:
        last=state.get('messages',[])[-1] if state.get('messages') else {}
        if (state['board']['active'] or state['pending'] or last.get('kind') in ('ooc','private')
            or any((result or {}).get(k) for k in ('checks','investigation','proposals','routeTravel','preparedDecision','meleeAttack','turnEnd'))):
            raise ValueError('Las notas del mundo no adelantan resoluciones o decisiones pendientes')
    return candidate
