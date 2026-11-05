"""Compile explicitly provided adventure preparation, never executable rules."""
import hashlib
import json
import adventure_source
import adventure_discoveries
import rule_pack_objectives as objectives
from rule_pack_authoring import canonical
from rule_pack_runtime import RulePackError

FORMAT='cronicas-adventure-plan-1'


def compile_plan(plan,pack,policy):
    if policy!='provided-adventure':raise RulePackError('Confirma el permiso de uso de la preparación aportada')
    try:size=len(canonical(plan).encode('utf-8'))
    except (TypeError,ValueError,RecursionError):raise RulePackError('Preparación de aventura no serializable') from None
    if size>60000:raise RulePackError('Preparación de aventura demasiado grande')
    if not isinstance(plan,dict) or set(plan)!={'format','source','package','objectives','discoveries'} or plan['format']!=FORMAT:
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
    by_id={g['id']:g for g in goals};package=pack.document()
    for definition in catalog['definitions']:
        goal=by_id.get(definition['objective'])
        if goal is None or not goal['known']:raise RulePackError('El descubrimiento necesita un objetivo conocido de esta preparación')
        check={key:definition[key] for key in ('objective','field')};supported=False
        for action,spec in package['actions'].items():
            if action in pack.creation_steps or spec.get('permission','owner')!='owner':continue
            try:objectives.check_spec(check,action,[goal|{'status':'open'}],package);supported=True;break
            except RulePackError:pass
        if not supported:raise RulePackError('Ninguna acción disponible calcula el resultado requerido por el descubrimiento')
    # Deep copies prevent the caller from mutating imported preparation later.
    return json.loads(canonical({'source':original,'objectives':goals,'catalog':catalog,
        'sha256':hashlib.sha256(canonical(plan).encode('utf-8')).hexdigest()}))
