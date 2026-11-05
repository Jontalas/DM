"""Describe a pending-resolution seed independently of the HTTP room version.

Not wired to storage or execution yet. This descriptor is not a legality check:
the normal pending/ownership/context preflight must still run before any draw,
and a future commit must confirm this exact key atomically with the state.
"""
import hashlib
from rule_pack_authoring import canonical
from rule_pack_runtime import RulePackError

SCOPE='pending-resolution-v2'


def describe(state,action,me,pack):
    pending=(state.get('narrative') or {}).get('pending')
    if not isinstance(pending,dict) or 'randomnessScope' not in pending:return None
    if pending['randomnessScope']!=SCOPE:raise RulePackError('Ámbito de reserva de dados desconocido')
    if action.get('type')!='resolve_pack_request' or action.get('request')!=pending.get('id'):
        raise RulePackError('La reserva requiere la misma solicitud pendiente')
    identifier=pending.get('id')
    if not isinstance(identifier,str) or not 1<=len(identifier)<=100:raise RulePackError('Identidad de solicitud inválida')
    character=next((c for c in state['characters'] if c['id']==pending.get('character')),None)
    if character is None or character['owner']!=me['id']:raise PermissionError('La reserva pertenece a otro personaje')
    inputs=pack.action_inputs(pending['action'],action.get('inputs',pending['inputs']))
    physical=action.get('physical');physical={} if physical is None else physical
    if not isinstance(physical,dict):raise RulePackError('Dados físicos inválidos para la reserva')
    memory=state['narrative'];target=None
    if 'targetBinding' in pending:
        binding=pending['targetBinding']
        if not isinstance(binding,dict):raise RulePackError('Referencia de objetivo inválida')
        target=next((actor for actor in state.get('actors',[]) if actor['id']==binding.get('target')),None)
        if target is None:raise RulePackError('Actor objetivo ausente de la reserva')
    snapshot={'scope':SCOPE,'pending':pending,'character':character['sheet'],'target':target,
        'package':{'sha256':pack.digest,'policy':state['package']['policy']},'inputs':inputs,'physical':physical,
        'world':{key:memory.get(key) for key in ('npcs','places','relationships','objectives','discoveries','objectiveTargets')}}
    key='pending:'+hashlib.sha256(canonical({'actor':me['id'],'request':identifier}).encode('utf-8')).hexdigest()
    return {'key':key,'fingerprint':hashlib.sha256(canonical(snapshot).encode('utf-8')).hexdigest(),'version':0}
