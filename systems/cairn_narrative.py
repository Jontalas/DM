"""Validated Cairn declarations and memory. Mechanics remain in cairn_adventure."""
import copy
import time
from systems import cairn_adventure as adventure,cairn_director as director


def initial_memory():
    return {'summary':'','preparation':'','revision':0,'eventsSeen':0,
        'usage':{'responses':0,'measuredResponses':0,'inputTokens':0,'outputTokens':0,'latencyMs':0}}


def _message(kind,speaker,text,actor):
    return {'kind':kind,'speaker':speaker,'text':text,'time':time.time(),'character':actor}


def apply(state,body,me):
    action={k:v for k,v in body.items() if k not in ('id','version')}
    if not state.get('adventure'):raise ValueError('Inicia primero una escena de Cairn')
    actor=next(c for c in state['characters'] if c['id']==state['adventure']['character'])
    operation='continue' if action.get('type')=='continue_cairn_adventure' else 'talk'
    memory=state.get('narrative',initial_memory());events=len(state['adventure']['events'])
    if operation=='continue':
        if set(action)!={'type'}:raise ValueError('Continuación de Cairn inválida')
        if actor['owner']!=me['id']:raise PermissionError('Solo quien controla al personaje continúa sus resultados')
        if state['adventure']['pending'] or events<=memory['eventsSeen']:raise ValueError('No hay consecuencias nuevas resueltas que narrar')
        text='Narra las consecuencias ya confirmadas por el motor sin pedir otra tirada ni elegir acciones del personaje.';kind='continue';use_ai=True
    else:
        if (set(action)-{'type','character','text','kind','director'} or not {'type','text'}<=set(action)
            or not isinstance(action['text'],str) or not action['text'].strip() or len(action['text'])>2000):raise ValueError('Intervención de Cairn inválida')
        text=action['text'].strip();kind=action.get('kind','dialogue');use_ai=action.get('director',True)
        if kind not in ('action','dialogue','ooc') or type(use_ai)!=bool:raise ValueError('Tipo de intervención inválido')
        if kind=='ooc':
            if action.get('character') not in (None,''):raise ValueError('Fuera de personaje no atribuye palabras a un PJ')
            result=copy.deepcopy(state);result['messages'].append(_message('ooc',me['name'],text,''));return result
        if actor['owner']!=me['id'] or action.get('character')!=actor['id']:raise PermissionError('No controlas al personaje de esta escena')
        if not adventure.status(actor)['canAct']:raise ValueError('El personaje necesita recuperarse antes de actuar; puedes elegir los cuidados disponibles')
        if kind=='action' and state['adventure']['pending']:raise ValueError('Resuelve primero la salvación pendiente')
    result=copy.deepcopy(state)
    if operation=='talk':result['messages'].append(_message(kind,actor['name'],text,actor['id']))
    if not use_ai:return result
    reply=director.validate_reply(director.ai_reply(state,actor,text,kind,operation),state,actor,operation,kind,transport_metadata=True)
    result['messages'].append(_message('director','Director de Cairn',reply['narration'],actor['id']))
    if reply['limitation']:result['messages'].append(_message('limit','Cobertura del motor',reply['limitation'],actor['id']))
    intent=reply['intent']
    if intent['type']!='none':
        spec={'type':intent['type']}
        if intent['type']=='choose_route':spec['route']=intent['route']
        result=adventure.apply(result,spec,me)
    previous=memory['usage'];usage=copy.deepcopy(previous);usage['responses']+=1
    if '_usage' in reply:
        usage['measuredResponses']+=1
        for key in ('inputTokens','outputTokens','latencyMs'):usage[key]+=reply['_usage'][key]
    result['narrative']={**reply['memory'],'revision':memory['revision']+1,'eventsSeen':events,'usage':usage}
    return result


def validate_restored(state):
    memory=state.get('narrative')
    if not isinstance(memory,dict) or set(memory)!=set(initial_memory()):raise ValueError('Memoria narrativa de Cairn inválida')
    for key,limit in [('summary',4000),('preparation',6000)]:
        if not isinstance(memory[key],str) or len(memory[key])>limit:raise ValueError('Texto de memoria de Cairn inválido')
    events=len(state['adventure']['events']) if state.get('adventure') else 0
    if (type(memory['revision'])!=int or not 0<=memory['revision']<=1000000
        or type(memory['eventsSeen'])!=int or not 0<=memory['eventsSeen']<=events):raise ValueError('Revisión de memoria incompatible')
    if memory['revision']!=sum(m['kind']=='director' for m in state['messages']):raise ValueError('El historial no coincide con la revisión narrativa')
    usage=memory['usage']
    if (not isinstance(usage,dict) or set(usage)!=set(initial_memory()['usage'])
        or any(type(v)!=int or v<0 for v in usage.values()) or not usage['measuredResponses']<=usage['responses']==memory['revision']):
        raise ValueError('Medición narrativa incompatible')
