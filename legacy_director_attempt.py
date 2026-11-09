"""Durable response capture for the existing Pathfinder director contract.

Reuses the private paid-call store without changing the model prompt, rules,
output budget or legacy public response shape. No provider call on restore.
"""
import base64
import copy
import hashlib
import json
import re
import claude_dm
from director_prompt import system_prompt
from rule_pack_authoring import canonical

SCHEME='pf-director-v1'
CONTRACT='cronicas-pf-director-1'
ACTION_CONTRACT='pf-director-action-1'


def request_sha(request):
    identity=request.get('actionIdentity')
    if identity is None:value=keyed_request(request)
    else:
        if (not isinstance(identity,dict) or set(identity)!={'action','actor','fingerprint','version'}
            or any(not isinstance(identity[k],str) or not 1<=len(identity[k])<=200 for k in ('action','actor'))
            or not isinstance(identity['fingerprint'],str) or not re.fullmatch('[a-f0-9]{64}',identity['fingerprint'])
            or type(identity['version'])!=int or identity['version']<0):
            raise ValueError('Identidad de envío inválida')
        value={'contract':ACTION_CONTRACT,'action':identity['action'],'actor':identity['actor']}
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def compatible_input(saved,current):
    previous=keyed_request(saved);now=keyed_request(current)
    if previous.get('actionIdentity') is not None and previous.get('actionIdentity')==now.get('actionIdentity'):
        # Search may change after indexing. Replay the original private input;
        # keep game facts, history, version and submission exact.
        previous['context'].pop('sources',None);now['context'].pop('sources',None)
    return canonical(previous)==canonical(now)


def keyed_request(request):
    keyed=copy.deepcopy(request)
    for name in ('routeTravelActor','preparedDecisions','availableMeleeAttack','availableTurnEnd','preparedSceneFacts','worldMemorySelection','preparedEncounterProjection'):keyed['context'].pop(name,None)
    return keyed


def capture_input(prepared):
    original=prepared.get('captureRequest',prepared['request'])
    if 'captureRequest' not in prepared:return original
    if (not isinstance(original,dict) or not isinstance(original.get('context'),dict)
        or not isinstance(prepared['request'],dict) or original.get('contract')!=CONTRACT
        or request_sha(original)!=prepared['sha256']):
        raise ValueError('La entrada original no coincide con la huella de la captura')
    import campaign_world_context
    context=original['context'];world=context.get('directorKnowledge',{}).get('campaignWorld')
    import director_prepared_facts
    projection=context.get('preparedEncounterProjection')
    if projection is not None:
        record=context['state'].get('pfEncounter')
        if projection!=director_prepared_facts.PRESENTATION_PROJECTION or director_prepared_facts.context_record(record)==record:
            raise ValueError('La proyección del encuentro no corresponde a un original verificado')
    if world is not None:
        world_view,selection=campaign_world_context.select(world,context['request'],context['state']['location'])
        if context.get('worldMemorySelection') is not None:
            if context['worldMemorySelection']!=selection:raise ValueError('La selección de notas no corresponde a la captura completa')
        else:world_view=world  # Historical complete inputs retain their original contract.
    if canonical(original)!=canonical(prepared['request']):
        projected=copy.deepcopy(original)
        import board_scenes
        view=board_scenes.director_view(projected['context']['state'])
        if view is not None:projected['context']['state']['boardScenes']=view
        import pf_medical_evolution
        for character in projected['context']['state'].get('characters',[]):
            medical=pf_medical_evolution.director_view(character)
            if medical is not None:character['recoveryState']=medical
        if world is not None:projected['context']['directorKnowledge']['campaignWorld']=world_view
        if projection is not None:projected['context']['state']['pfEncounter']=director_prepared_facts.context_record(context['state']['pfEncounter'])
        if canonical(projected)!=canonical(prepared['request']):raise ValueError('El contexto reducido no corresponde a su entrada original')
    return original


def prepare(state,text,refs,check_actors=None,starting=False,source_text=None,action_identity=None):
    context=claude_dm.build_context(state,text,refs,check_actors=check_actors,starting=starting,source_text=source_text)
    # Distinguish genuinely new turns after the bounded history window repeats,
    # while a retry against the same uncommitted state keeps the same key.
    transcript_length=sum(1 for message in state['messages'] if message.get('visibility','public')=='public' and message.get('kind')!='private')
    request={'contract':CONTRACT,'context':copy.deepcopy(context),'transcriptLength':transcript_length}
    if action_identity is not None:request['actionIdentity']=copy.deepcopy(action_identity)
    capture=copy.deepcopy(request)
    if context.get('preparedEncounterProjection') is not None:capture['context']['state']['pfEncounter']=copy.deepcopy(state['pfEncounter'])
    if claude_dm.campaign_world.enabled(state):capture['context']['directorKnowledge']['campaignWorld']=copy.deepcopy(state['campaignWorld'])
    # Preserve old paid keys while sending only a projection of archived maps.
    if 'boardScenes' in state:capture['context']['state']['boardScenes']=copy.deepcopy(state['boardScenes'])
    originals={c['id']:c for c in state['characters']}
    for character in capture['context']['state']['characters']:
        if character.get('recoveryState',{}).get('format')=='cronicas-pf-medical-context-1':
            character['recoveryState']=copy.deepcopy(originals[character['id']]['recoveryState'])
    if len(canonical(request).encode('utf-8'))>300000:raise ValueError('El contexto de esta aventura supera el límite; no se ha llamado a IA')
    return {'request':request,'captureRequest':capture,'sha256':request_sha(capture),'sourceScheme':SCHEME,
        'promptSha256':hashlib.sha256(system_prompt(False,starting,world_memory=claude_dm.campaign_world.enabled(state),world_projection='worldMemorySelection' in context,chapter_start=bool(state.get('adventureChapterTransition'))).encode('utf-8')).hexdigest()}


def restore(prepared,payload,scheme):
    if scheme!=SCHEME or prepared['request'].get('contract')!=CONTRACT:raise ValueError('Contrato de captura Pathfinder incompatible')
    if not isinstance(payload,dict) or set(payload)!={'kind','value','latencyMs'}:raise ValueError('Captura Pathfinder inválida')
    context=prepared['request']['context'];state=copy.deepcopy(context['state'])
    if context.get('preparedEncounterProjection') is not None:
        import director_prepared_facts
        original=prepared.get('captureRequest',{}).get('context',{}).get('state',{}).get('pfEncounter')
        if context['preparedEncounterProjection']!=director_prepared_facts.PRESENTATION_PROJECTION or original is None:
            raise ValueError('Falta el original de la proyección del encuentro')
        if state.get('pfEncounter')!=original:
            if director_prepared_facts.context_record(original)!=state.get('pfEncounter'):raise ValueError('El encuentro reducido no corresponde a su captura privada')
            state['pfEncounter']=copy.deepcopy(original)
    module=context.get('directorKnowledge',{}).get('adventureModule')
    if module is not None:state['adventureModule']=copy.deepcopy(module)
    world=context.get('directorKnowledge',{}).get('campaignWorld')
    if world is not None:
        import campaign_world_context
        if world.get('format')==campaign_world_context.FORMAT:
            complete=prepared.get('captureRequest',{}).get('context',{}).get('directorKnowledge',{}).get('campaignWorld')
            if complete is None:raise ValueError('Falta la memoria completa de la captura privada')
            projected,selection=campaign_world_context.select(complete,context['request'],state['location'])
            if canonical(projected)!=canonical(world) or selection!=context.get('worldMemorySelection'):
                raise ValueError('Las notas reducidas no corresponden a la captura privada')
            world=complete
        state['campaignWorld']=copy.deepcopy(world)
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
    attack={}
    if context.get('availableMeleeAttack') and context.get('history') and context['history'][-1].get('kind')=='action' and context['operation']=='narrate':
        attack=context['availableMeleeAttack']
    turn={}
    if context.get('availableTurnEnd') and context.get('history') and context['history'][-1].get('kind')=='action' and context['operation']=='narrate':turn=context['availableTurnEnd']
    result=claude_dm.parse_response(state,raw,rules=False,starting=context['operation']=='startAdventure',route_travel_context=route_travel,prepared_decision_context=decisions,melee_attack_context=attack,turn_end_context=turn,world_memory_selection=context.get('worldMemorySelection'))
    if payload['kind']=='report':
        # Reports already passed through the adapter. Validate their structure,
        # but preserve the stored narration instead of repairing it twice.
        narration=payload['value'].get('narration')
        if not isinstance(narration,str) or not narration.strip() or len(narration)>30000:raise ValueError('Narración guardada inválida')
        result['narration']=narration
    return result
