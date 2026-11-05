"""Preparation-time target/choice matching, not yet a campaign resolution path.

Routes select evidence from a verified engine action, never an AI interpretation
or a prior success. Presence, permissions and action requirements still belong
to target_context and the runtime at the moment of execution.
"""
import copy
import hashlib
from rule_pack_authoring import canonical
from rule_pack_runtime import RulePackError
import rule_pack_objectives as objectives

MAX_ROUTES=12
MAX_BYTES=18000
FORMAT='cronicas-objective-targets-1'


def digest(store):return hashlib.sha256(canonical(store).encode('utf-8')).hexdigest()


def compile_routes(routes,pack,goals,actors):
    if not isinstance(routes,list) or not 1<=len(routes)<=MAX_ROUTES:
        raise RulePackError('Vínculos de objetivos dirigidos fuera de límites')
    try:size=len(canonical(routes).encode('utf-8'))
    except (TypeError,ValueError,RecursionError):raise RulePackError('Vínculos dirigidos no serializables') from None
    if size>MAX_BYTES:raise RulePackError('Vínculos de objetivos dirigidos fuera de límites')
    if not isinstance(actors,list) or len(actors)>16 or any(not isinstance(actor,dict) or not isinstance(actor.get('npc'),str) for actor in actors):
        raise RulePackError('Registro de PNJ inválido para los vínculos')
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


def binding(state,action,npc,inputs):
    memory=state.get('narrative') or {};store=memory.get('objectiveTargets')
    return select(store['routes'],memory.get('objectives',[]),action,npc,inputs) if store else None


def check_request(state,pending,npc=None):
    memory=state.get('narrative') or {};store=memory.get('objectiveTargets');check=pending.get('objectiveCheck')
    expected=binding(state,pending['action'],npc,pending['inputs'])
    if npc is not None:
        if check!=expected:raise RulePackError('La solicitud no conserva el vínculo preparado para ese PNJ y decisiones')
    elif check and store and any(route['objective']==check['objective'] for route in store['routes']):
        raise RulePackError('Este objetivo requiere su acción dirigida y PNJ preparados')
    return expected


def validate_store(state,pack):
    memory=state.get('narrative') or {};store=memory.get('objectiveTargets')
    marker=(memory.get('discoveries') or {}).get('objectiveTargetsSha256')
    if store is None:
        if marker is not None:raise RulePackError('Falta el vínculo dirigido de la preparación')
        return
    if not isinstance(store,dict) or set(store)!={'format','routes','installedAt'} or store['format']!=FORMAT:
        raise RulePackError('Preparación de objetivos dirigidos inválida')
    compiled=compile_routes(store['routes'],pack,memory.get('objectives',[]),state.get('actors',[]))
    if marker!=digest(store):raise RulePackError('Los vínculos dirigidos difieren de la preparación registrada')
    if canonical(compiled)!=canonical(store['routes']):raise RulePackError('Las decisiones de los vínculos no están normalizadas')
    index=store['installedAt'];messages=state['messages']
    if type(index)!=int or not 0<=index<len(messages) or messages[index].get('kind')!='system':raise RulePackError('Vínculos dirigidos sin preparación registrada')
    for route in compiled:
        goal=next(goal for goal in memory['objectives'] if goal['id']==route['objective'])
        actor=next(actor for actor in state['actors'] if actor['npc']==route['npc'])
        if goal['introducedAt']>=index or type(actor.get('introducedAt'))!=int or actor['introducedAt']>index:
            raise RulePackError('El vínculo precede a la preparación del objetivo o PNJ')
    for position,event in enumerate(messages):
        proof=event.get('objectiveResolution')
        if proof is None:continue
        routes=[route for route in compiled if route['objective']==proof.get('objective')]
        if not routes:continue
        reference=event.get('targetRef');reference=reference if isinstance(reference,dict) else {}
        if position<=index or not any(event.get('action')==route['action'] and reference.get('npc')==route['npc']
            and proof.get('field')==route['field'] and proof.get('inputsSha256')==objectives.inputs_hash(route['inputs']) for route in routes):
            raise RulePackError('La evidencia no corresponde al PNJ, acción y decisiones preparados')
