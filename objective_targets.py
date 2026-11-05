"""Preparation-time target/choice matching, not yet a campaign resolution path.

Routes select evidence from a verified engine action, never an AI interpretation
or a prior success. Presence, permissions and action requirements still belong
to target_context and the runtime at the moment of execution.
"""
import copy
from rule_pack_authoring import canonical
from rule_pack_runtime import RulePackError
import rule_pack_objectives as objectives

MAX_ROUTES=12
MAX_BYTES=18000


def compile_routes(routes,pack,goals,actors):
    if not isinstance(routes,list) or not 1<=len(routes)<=MAX_ROUTES:
        raise RulePackError('Vínculos de objetivos dirigidos fuera de límites')
    try:size=len(canonical(routes).encode('utf-8'))
    except (TypeError,ValueError,RecursionError):raise RulePackError('Vínculos dirigidos no serializables') from None
    if size>MAX_BYTES:raise RulePackError('Vínculos de objetivos dirigidos fuera de límites')
    document=pack.document();npcs={actor['npc'] for actor in actors};known_goals={g['id']:g for g in goals}
    result=[];selectors=set()
    for route in routes:
        if not isinstance(route,dict) or set(route)!={'objective','action','field','npc','inputs'}:
            raise RulePackError('Vínculo de objetivo dirigido incompleto')
        if not isinstance(route['npc'],str) or route['npc'] not in npcs:
            raise RulePackError('El objetivo dirigido requiere un PNJ con perfil preparado')
        goal=known_goals.get(route['objective']) if isinstance(route['objective'],str) else None
        if goal is None:raise RulePackError('El vínculo requiere un objetivo de la preparación')
        action=document['actions'].get(route['action']) if isinstance(route['action'],str) else None
        if action is None or route['action'] in pack.reserved_creation_actions or action.get('permission','owner')!='owner' or 'targetContext' not in action:
            raise RulePackError('El vínculo requiere una acción dirigida jugable')
        # Shape/output validation is independent of whether the opportunity is
        # currently known or completed. Availability is checked on selection.
        objectives.check_spec({key:route[key] for key in ('objective','field')},route['action'],
            [goal|{'known':True,'status':'open'}],document)
        inputs=pack.action_inputs(route['action'],route['inputs'])
        selector=(route['action'],route['npc'],objectives.inputs_hash(inputs))
        if selector in selectors:raise RulePackError('Dos vínculos reclaman la misma acción, PNJ y decisiones')
        selectors.add(selector);result.append(copy.deepcopy(route|{'inputs':inputs}))
    if len(canonical(result).encode('utf-8'))>MAX_BYTES:raise RulePackError('Las decisiones normalizadas superan el límite de vínculos')
    return result


def select(routes,goals,action,npc,inputs):
    """Match already compiled routes after runtime has normalized choices."""
    available={goal['id'] for goal in goals if goal['known'] and goal['status']=='open'}
    matches=[route for route in routes if route['objective'] in available and route['action']==action
        and route['npc']==npc and objectives.inputs_hash(route['inputs'])==objectives.inputs_hash(inputs)]
    if len(matches)>1:raise RulePackError('Vínculo dirigido ambiguo')
    return {key:matches[0][key] for key in ('objective','field')} if matches else None
