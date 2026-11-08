"""Durable response capture for the existing Pathfinder director contract.

Reuses the private paid-call store without changing the model prompt, rules,
output budget or legacy public response shape. No provider call on restore.
"""
import base64
import copy
import hashlib
import json
import claude_dm
from director_prompt import system_prompt
from rule_pack_authoring import canonical

SCHEME='pf-director-v1'
CONTRACT='cronicas-pf-director-1'


def prepare(state,text,refs,check_actors=None,starting=False,source_text=None):
    context=claude_dm.build_context(state,text,refs,check_actors=check_actors,starting=starting,source_text=source_text)
    # Distinguish genuinely new turns after the bounded history window repeats,
    # while a retry against the same uncommitted state keeps the same key.
    transcript_length=sum(1 for message in state['messages'] if message.get('visibility','public')=='public' and message.get('kind')!='private')
    request={'contract':CONTRACT,'context':copy.deepcopy(context),'transcriptLength':transcript_length}
    keyed=copy.deepcopy(request)
    # A derived action hint must not invalidate an already paid response.
    # Old captures keep their original narration and do not gain a new action.
    keyed['context'].pop('routeTravelActor',None)
    keyed['context'].pop('preparedDecisions',None)
    raw=canonical(keyed).encode('utf-8')
    if len(raw)>300000:raise ValueError('El contexto de esta aventura supera el límite; no se ha llamado a IA')
    return {'request':request,'sha256':hashlib.sha256(raw).hexdigest(),'sourceScheme':SCHEME,
        'promptSha256':hashlib.sha256(system_prompt(False,starting).encode('utf-8')).hexdigest()}


def restore(prepared,payload,scheme):
    if scheme!=SCHEME or prepared['request'].get('contract')!=CONTRACT:raise ValueError('Contrato de captura Pathfinder incompatible')
    if not isinstance(payload,dict) or set(payload)!={'kind','value','latencyMs'}:raise ValueError('Captura Pathfinder inválida')
    context=prepared['request']['context'];state=copy.deepcopy(context['state'])
    module=context.get('directorKnowledge',{}).get('adventureModule')
    if module is not None:state['adventureModule']=copy.deepcopy(module)
    if payload['kind']=='raw':
        try:raw=base64.b64decode(payload['value'],validate=True)
        except (TypeError,ValueError):raise ValueError('Captura de respuesta dañada; no se ha repetido IA') from None
    elif payload['kind']=='report':raw=json.dumps({'stop_reason':'end_turn','content':[{'type':'text','text':json.dumps(payload['value'])}]}).encode('utf-8')
    else:raise ValueError('Tipo de captura Pathfinder desconocido')
    route_travel={}
    if (context.get('routeTravelActor') and context.get('history') and context['history'][-1].get('kind')=='action'
        and context['operation']=='narrate'):
        route_travel={'character':context['routeTravelActor'],'exits':state.get('adventureRouteView',{}).get('exits',[])}
    decisions={}
    if context.get('preparedDecisions') and context.get('history') and context['history'][-1].get('kind')=='action' and context['operation']=='narrate':
        decisions=context['preparedDecisions']
    result=claude_dm.parse_response(state,raw,rules=False,starting=context['operation']=='startAdventure',route_travel_context=route_travel,prepared_decision_context=decisions)
    if payload['kind']=='report':
        # Reports already passed through the adapter. Validate their structure,
        # but preserve the stored narration instead of repairing it twice.
        narration=payload['value'].get('narration')
        if not isinstance(narration,str) or not narration.strip() or len(narration)>30000:raise ValueError('Narración guardada inválida')
        result['narration']=narration
    return result
