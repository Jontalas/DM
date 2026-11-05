"""Compile explicitly provided adventure preparation, never executable rules."""
import hashlib
import json
import adventure_source
import adventure_discoveries
import rule_pack_objectives as objectives
from rule_pack_authoring import canonical
from rule_pack_runtime import RulePackError

FORMAT='cronicas-adventure-plan-1'
ACTORS_FORMAT='cronicas-adventure-plan-2'
TARGETS_FORMAT='cronicas-adventure-plan-3'


def compile_plan(plan,pack,policy):
    if policy!='provided-adventure':raise RulePackError('Confirma el permiso de uso de la preparación aportada')
    try:size=len(canonical(plan).encode('utf-8'))
    except (TypeError,ValueError,RecursionError):raise RulePackError('Preparación de aventura no serializable') from None
    if size>60000:raise RulePackError('Preparación de aventura demasiado grande')
    keys={'format','source','package','objectives','discoveries'}
    actor_plan=isinstance(plan,dict) and plan.get('format') in (ACTORS_FORMAT,TARGETS_FORMAT)
    if actor_plan:keys.add('npcPreparation')
    target_plan=isinstance(plan,dict) and plan.get('format')==TARGETS_FORMAT
    if target_plan:keys.add('objectiveTargets')
    if not isinstance(plan,dict) or set(plan)!=keys or plan['format'] not in (FORMAT,ACTORS_FORMAT,TARGETS_FORMAT):
        raise RulePackError('Formato de preparación de aventura incompatible')
    if plan['package']!={'id':pack.id,'version':pack.version,'sha256':pack.digest}:
        raise RulePackError('La preparación requiere otra versión exacta del paquete de reglas')
    if 'action-results' not in pack.document()['requires']:raise RulePackError('La preparación requiere resultados explícitos de acción')
    source=plan['source']
    if not isinstance(source,dict) or set(source)!={'title','text'}:raise RulePackError('Fuente de preparación incompleta')
    original=adventure_source.create(source['title'],source['text'],policy)
    goals=objectives.descriptors(plan['objectives'])
    if not goals:raise RulePackError('La preparación necesita al menos un objetivo')
    catalog=adventure_discoveries.prepare(source['text'],plan['discoveries'],policy)
    npc_preparation=None;target_routes=[]
    if actor_plan:
        from adventure_actors import compile_preparation
        npc_preparation=compile_preparation(plan['npcPreparation'],pack,'provided-profile')
    if target_plan:
        from objective_targets import compile_routes
        target_routes=compile_routes(plan['objectiveTargets'],pack,goals,npc_preparation['actors'])
    by_id={g['id']:g for g in goals};package=pack.document()
    for definition in catalog['definitions']:
        goal=by_id.get(definition['objective'])
        if goal is None or not goal['known']:raise RulePackError('El descubrimiento necesita un objetivo conocido de esta preparación')
        check={key:definition[key] for key in ('objective','field')};supported=False
        routed=any(route['objective']==definition['objective'] for route in target_routes)
        for action,spec in package['actions'].items():
            if action in pack.reserved_creation_actions or spec.get('permission','owner')!='owner':continue
            if routed:
                if not any(route['objective']==definition['objective'] and route['field']==definition['field'] and route['action']==action for route in target_routes):continue
            elif spec.get('target'):continue
            try:objectives.check_spec(check,action,[goal|{'status':'open'}],package);supported=True;break
            except RulePackError:pass
        if not supported:raise RulePackError('Ninguna acción disponible calcula el resultado requerido por el descubrimiento')
    result={'source':original,'objectives':goals,'catalog':catalog,
        'sha256':hashlib.sha256(canonical(plan).encode('utf-8')).hexdigest()}
    if actor_plan:
        result['npcPreparation']=npc_preparation
    if target_plan:
        result['objectiveTargets']=target_routes
    # Deep copies prevent the caller from mutating imported preparation later.
    return json.loads(canonical(result))
