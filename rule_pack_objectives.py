"""Adventure opportunities with completion bound to one confirmed engine action.

This first block supports an unconditional stored boolean output of an action.
It never interprets prose as evidence or defines mechanics/rewards for a game.
"""
import copy
import hashlib
import re
from rule_pack_runtime import RulePackError
from rule_pack_authoring import canonical

MAX_OBJECTIVES=12
DESCRIPTOR={'id','title','detail','known','private'}


def descriptors(items):
    if not isinstance(items,list) or len(items)>MAX_OBJECTIVES:raise RulePackError('Objetivos fuera de límites')
    seen=set()
    for item in items:
        if not isinstance(item,dict) or set(item)!=DESCRIPTOR:raise RulePackError('El director solo puede proponer descripciones de objetivos, no resolverlos')
        identifier=item['id']
        if not isinstance(identifier,str) or not re.fullmatch('[a-z][a-z0-9-]{0,47}',identifier) or identifier in seen:raise RulePackError('Identidad de objetivo inválida o repetida')
        seen.add(identifier)
        if type(item['known'])!=bool:raise RulePackError('Visibilidad de objetivo inválida')
        for key,limit in [('title',120),('detail',600),('private',700)]:
            if not isinstance(item[key],str) or len(item[key])>limit or key=='title' and not item[key].strip():raise RulePackError('Texto de objetivo fuera de límites')
    return copy.deepcopy(items)


def merge(previous,updates,message):
    if not isinstance(updates,list) or len(updates)>2:raise RulePackError('Como máximo dos objetivos nuevos o actualizados por intervención')
    result={item['id']:copy.deepcopy(item) for item in previous}
    for descriptor in descriptors(updates):
        prior=result.get(descriptor['id'])
        if prior:
            if prior['known'] and not descriptor['known']:raise RulePackError('No se puede retirar un objetivo conocido')
            if any(prior[key]!=descriptor[key] for key in ('title','detail')):raise RulePackError('No se puede cambiar retrospectivamente la definición de un objetivo; usa otra identidad')
            result[descriptor['id']]={**prior,**descriptor}
        else:result[descriptor['id']]={**descriptor,'status':'open','introducedAt':message,'evidence':None}
    if len(result)>MAX_OBJECTIVES:raise RulePackError('La aventura alcanza su límite de objetivos')
    return list(result.values())


def check_spec(check,action,items,package):
    if not isinstance(check,dict) or set(check)!={'objective','field'}:raise RulePackError('Vínculo de objetivo inválido')
    objective=next((item for item in items if item['id']==check['objective']),None)
    if objective is None or not objective['known'] or objective['status']!='open':raise RulePackError('El objetivo vinculado debe estar abierto y ser conocido')
    if not isinstance(action,str) or action not in package['actions']:raise RulePackError('El objetivo necesita una solicitud mecánica concreta')
    field=check['field']
    if not isinstance(field,str) or field not in package['fields']:raise RulePackError('Campo de evidencia no disponible')
    spec=package['fields'][field]
    if spec['type']!='boolean' or 'initial' not in spec:raise RulePackError('Este bloque de objetivos requiere un resultado booleano almacenado del paquete')
    if not any(effect['field']==field and effect.get('when',True) is True for effect in package['actions'][action]['effects']):
        raise RulePackError('La acción debe calcular ese resultado booleano de forma incondicional')
    return copy.deepcopy(check)


def inputs_hash(inputs):return hashlib.sha256(canonical(inputs).encode('utf-8')).hexdigest()


def context_package(request):
    # An action can only write stored fields in a valid package. Its existing
    # effect definitions and typed current values suffice without enlarging
    # legacy contexts or changing their paid-attempt hashes.
    return {'actions':request['rules']['actions'],'fields':{
        key:{'type':'boolean','initial':value} for key,value in request['character']['sheet']['fields'].items() if type(value)==bool}}


def resolve(items,pending,event,sheet,message,package):
    result=copy.deepcopy(items);check=pending.get('objectiveCheck')
    if check is None:return result,None
    check_spec(check,pending['action'],result,package)
    matched=inputs_hash(event['inputs'])==inputs_hash(pending['inputs'])
    met=matched and sheet['fields'][check['field']] is True
    proof={**check,'request':pending['id'],'inputsSha256':inputs_hash(pending['inputs']),
        'matchedInputs':matched,'met':met,'sheetRevision':sheet['revision']}
    if met:
        objective=next(item for item in result if item['id']==check['objective'])
        objective['status']='completed';objective['evidence']={'message':message,'packageSha256':sheet['package']['sha256'],**proof}
    return result,proof


def validate_proof(proof,event,sheet,package):
    keys={'objective','field','request','inputsSha256','matchedInputs','met','sheetRevision'}
    if not isinstance(proof,dict) or set(proof)!=keys:raise RulePackError('Evidencia de objetivo inválida')
    for key in ('objective','request'):
        if not isinstance(proof[key],str) or not 1<=len(proof[key])<=100:raise RulePackError('Vínculo de evidencia inválido')
    sha=proof['inputsSha256']
    if not isinstance(sha,str) or not re.fullmatch('[a-f0-9]{64}',sha):raise RulePackError('Huella de decisiones inválida')
    dummy=[{'id':proof['objective'],'known':True,'status':'open'}]
    check_spec({key:proof[key] for key in ('objective','field')},event['action'],dummy,package)
    matched=inputs_hash(event['inputs'])==sha
    if type(proof['matchedInputs'])!=bool or proof['matchedInputs']!=matched:raise RulePackError('La evidencia no coincide con las decisiones resueltas')
    if type(proof['met'])!=bool or proof['met']!=(matched and sheet['fields'][proof['field']] is True):raise RulePackError('El cierre no coincide con el resultado confirmado')
    if type(proof['sheetRevision'])!=int or proof['sheetRevision']!=sheet['revision']:raise RulePackError('Evidencia ligada a otra revisión de ficha')


def validate(items,state,pack):
    if not isinstance(items,list) or len(items)>MAX_OBJECTIVES:raise RulePackError('Objetivos guardados fuera de límites')
    descriptors([{key:item[key] for key in DESCRIPTOR} for item in items if isinstance(item,dict) and DESCRIPTOR<=set(item)])
    seen=set();messages=state['messages']
    for item in items:
        if not isinstance(item,dict) or set(item)!=DESCRIPTOR|{'status','introducedAt','evidence'}:raise RulePackError('Memoria de objetivo inválida')
        if item['id'] in seen:raise RulePackError('Objetivo guardado repetido')
        seen.add(item['id']);index=item['introducedAt']
        if type(index)!=int or not 0<=index<len(messages) or messages[index]['kind']!='pack-director':raise RulePackError('Objetivo sin intervención de origen')
        if item['status']=='open':
            if item['evidence'] is not None:raise RulePackError('Un objetivo abierto no tiene cierre confirmado')
        elif item['status']=='completed':
            evidence=item['evidence']
            if not isinstance(evidence,dict) or set(evidence)!={'message','packageSha256','objective','field','request','inputsSha256','matchedInputs','met','sheetRevision'}:raise RulePackError('Objetivo completado sin evidencia válida')
            position=evidence['message']
            if type(position)!=int or not index<position<len(messages):raise RulePackError('El objetivo no puede cerrarse con una acción anterior a su introducción')
            event=messages[position]
            if event.get('kind')!='pack-action' or event.get('objectiveResolution')!={key:value for key,value in evidence.items() if key not in ('message','packageSha256')}:
                raise RulePackError('El objetivo apunta a otra resolución')
            if evidence['objective']!=item['id'] or evidence['packageSha256']!=pack.digest or evidence['met'] is not True or not item['known']:
                raise RulePackError('Evidencia de objetivo incompatible')
        else:raise RulePackError('Estado de objetivo inválido')
    by_id={item['id']:item for item in items}
    for index,event in enumerate(messages):
        proof=event.get('objectiveResolution')
        if proof is None:continue
        if not isinstance(proof,dict) or not {'objective','met'}<=set(proof) or not isinstance(proof['objective'],str):raise RulePackError('Resolución de objetivo inválida')
        item=by_id.get(proof['objective'])
        if item is None or item['introducedAt']>=index:raise RulePackError('Resolución de objetivo sin definición previa')
        if item['status']=='completed' and item['evidence']['message']<index:raise RulePackError('Un objetivo ya completado no admite otra resolución vinculada')
        if proof['met'] and (item['status']!='completed' or item['evidence']['message']!=index):raise RulePackError('El registro y el estado del objetivo difieren')


def public_view(items):
    return [{key:copy.deepcopy(item[key]) for key in ('id','title','detail','status','evidence')} for item in items if item['known']]


def schema():
    return {'type':'array','items':{'type':'object','properties':{
        **{key:{'type':'string'} for key in ('id','title','detail','private')},'known':{'type':'boolean'}},
        'required':['id','title','detail','known','private'],'additionalProperties':False}}
