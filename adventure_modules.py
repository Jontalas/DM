"""Single-location investigations: private authored content, deterministic discoveries.

Perception uses the existing prepared-skill engine. PF1 Devir, PDF p.101,
deliberate search is a move action; retry while stimulus remains.
No combat, opposed checks, hazards, distances or situational modifiers in this block.
"""
import copy
import json
from pathlib import Path
import checks
import rulesets

MODULE_SCHEMA={'type':'object','properties':{
    'format':{'type':'string','enum':['cronicas-adventure-1']},
    'ruleset':{'type':'string','enum':['pathfinder-1e']},
    'scope':{'type':'string','enum':['single-scene-neutral-perception']},
    **{key:{'type':'string'} for key in ('title','premise','location','description','goal','preparation','conclusion')},
    'opportunities':{'type':'array','items':{'type':'object','properties':{
        **{key:{'type':'string'} for key in ('id','label','discovery','failure')},'dc':{'type':'integer'},
        'requires':{'type':'array','items':{'type':'string'}}},
        'required':['id','label','discovery','failure','dc','requires'],'additionalProperties':False}},
    'objectives':{'type':'array','items':{'type':'object','properties':{
        'id':{'type':'string'},'text':{'type':'string'},'requires':{'type':'array','items':{'type':'string'}}},
        'required':['id','text','requires'],'additionalProperties':False}}},
    'required':['format','ruleset','scope','title','premise','location','description','goal','preparation','conclusion','opportunities','objectives'],
    'additionalProperties':False}

GENERATED_SCHEMA={'type':'object','properties':{
    **{key:{'type':'string'} for key in ('title','premise','location','description','goal','preparation','conclusion')},
    **{key:{'type':'object','properties':{'label':{'type':'string'},'dc':{'type':'integer'},
            'discovery':{'type':'string'},'failure':{'type':'string'}},
            'required':['label','dc','discovery','failure'],'additionalProperties':False} for key in ('firstSearch','secondSearch')}},
    'required':['title','premise','location','description','goal','preparation','conclusion','firstSearch','secondSearch'],
    'additionalProperties':False}


def from_generated(raw):
    """The model writes prose; IDs, dependencies and completion belong to code."""
    if not isinstance(raw,dict) or set(raw)!=set(GENERATED_SCHEMA['required']):raise ValueError('Contenido generado incompleto')
    module={key:raw[key] for key in ('title','premise','location','description','goal','preparation','conclusion')}
    module.update(format='cronicas-adventure-1',ruleset='pathfinder-1e',scope='single-scene-neutral-perception',opportunities=[])
    for index,key in enumerate(('firstSearch','secondSearch'),1):
        item=raw[key]
        if not isinstance(item,dict) or set(item)!={'label','dc','discovery','failure'}:raise ValueError('Búsqueda generada inválida')
        module['opportunities'].append({**item,'id':'search-'+str(index),'requires':[] if index==1 else ['search-1']})
    module['objectives']=[{'id':'discovery-goal','text':raw['goal'],'requires':['search-2']}]
    return validate_module(module)


def _text(value,limit):
    if not isinstance(value,str) or not value.strip() or len(value)>limit:raise ValueError('Texto de aventura inválido')
    return value.strip()


def _id(value):
    import re
    if not isinstance(value,str) or not re.fullmatch('[a-z][a-z0-9_-]{0,39}',value):raise ValueError('Identificador de aventura inválido')
    return value


def validate_module(raw):
    if not isinstance(raw,dict) or set(raw)!=set(MODULE_SCHEMA['required']) or raw['format']!='cronicas-adventure-1':
        raise ValueError('Formato de aventura incompatible; utiliza cronicas-adventure-1')
    if len(json.dumps(raw,ensure_ascii=False).encode('utf-8'))>64000:raise ValueError('La aventura supera 64 KiB')
    if raw['ruleset']!='pathfinder-1e' or raw['scope']!='single-scene-neutral-perception':raise ValueError('La aventura requiere un sistema o mecánicas fuera del bloque soportado')
    result={'format':raw['format'],'ruleset':raw['ruleset'],'scope':raw['scope']}
    for key,limit in [('title',150),('premise',2000),('location',200),('description',3000),('goal',500),('preparation',6000),('conclusion',2000)]:
        result[key]=_text(raw[key],limit)
    opportunities=raw['opportunities'];objectives=raw['objectives']
    if not isinstance(opportunities,list) or not 1<=len(opportunities)<=8:raise ValueError('La aventura admite de una a ocho investigaciones')
    if not isinstance(objectives,list) or not 1<=len(objectives)<=4:raise ValueError('La aventura admite de uno a cuatro objetivos')
    ids=set();result['opportunities']=[]
    for item in opportunities:
        if not isinstance(item,dict) or set(item)!={'id','label','discovery','failure','dc','requires'}:raise ValueError('Investigación inválida')
        identifier=_id(item['id'])
        if identifier in ids:raise ValueError('Investigación duplicada')
        ids.add(identifier)
        if type(item['dc'])!=int or not 0<=item['dc']<=40:raise ValueError('CD de aventura fuera del bloque soportado (0–40)')
        result['opportunities'].append({'id':identifier,'label':_text(item['label'],150),
            'discovery':_text(item['discovery'],1500),'failure':_text(item['failure'],500),'dc':item['dc'],
            'requires':item['requires']})
    for item in result['opportunities']:
        requirements=item['requires']
        if (not isinstance(requirements,list) or len(requirements)>8 or any(not isinstance(v,str) or v not in ids for v in requirements)
            or len(set(requirements))!=len(requirements) or item['id'] in requirements):raise ValueError('Requisitos de investigación inválidos')
    # Reject inaccessible cyclic graphs, including cycles reachable from an otherwise valid root.
    available=set()
    while True:
        next_available=available|{item['id'] for item in result['opportunities'] if set(item['requires'])<=available}
        if next_available==available:break
        available=next_available
    if available!=ids:raise ValueError('La aventura contiene investigaciones inaccesibles o cíclicas')
    objective_ids=set();result['objectives']=[]
    for item in objectives:
        if not isinstance(item,dict) or set(item)!={'id','text','requires'}:raise ValueError('Objetivo de aventura inválido')
        identifier=_id(item['id']);requirements=item['requires']
        if identifier in objective_ids:raise ValueError('Objetivo duplicado')
        objective_ids.add(identifier)
        if (not isinstance(requirements,list) or not requirements or len(requirements)>8
            or any(not isinstance(v,str) or v not in ids for v in requirements) or len(set(requirements))!=len(requirements)):
            raise ValueError('Requisitos de objetivo inválidos')
        result['objectives'].append({'id':identifier,'text':_text(item['text'],300),'requires':requirements})
    return copy.deepcopy(result)


def builtin(identifier):
    if identifier!='la-carta-perdida':raise ValueError('Aventura de catálogo desconocida')
    return validate_module(json.loads((Path(__file__).parent/'adventures'/'la-carta-perdida.json').read_text(encoding='utf-8')))


def install(state,module):
    rulesets.require(state.get('ruleset',rulesets.DEFAULT))
    module=validate_module(module)
    bonuses=[]
    import board_scenes
    import pf_light_exploration
    for character in board_scenes.characters(state):
        if character.get('enemy') or character.get('hp',0)<=0 and not pf_light_exploration.eligible(state,character):continue
        try:bonuses.append(checks.modifier(character,'skill','Percepción')[0])
        except (ValueError,KeyError,TypeError):continue
    if not bonuses:raise ValueError('La aventura requiere un personaje con Percepción preparada y sin condiciones pendientes')
    required={key for objective in module['objectives'] for key in objective['requires']}
    while True:
        expanded=required|{key for opportunity in module['opportunities'] if opportunity['id'] in required for key in opportunity['requires']}
        if expanded==required:break
        required=expanded
    if any(v['id'] in required and v['dc']>20+max(bonuses) for v in module['opportunities']):
        raise ValueError('Las pistas obligatorias superan la Percepción alcanzable del grupo dentro del bloque soportado; no se ha alterado la CD')
    state['adventureModule']=module
    state['moduleProgress']={'discoveries':[],'attempts':{},'searchActions':0,'completed':False}
    state['location']=module['location'];state['goal']=module['goal']
    state['objectives']=[item['text'] for item in module['objectives']]


def validate_restored(state):
    if not state.get('adventureModule'):
        if state.get('moduleProgress'):raise ValueError('Progreso de investigación sin aventura')
        return
    module=validate_module(state['adventureModule']);progress=state.get('moduleProgress')
    if not state.get('adventure') or not isinstance(progress,dict) or set(progress)!={'discoveries','attempts','searchActions','completed'}:
        raise ValueError('Progreso de aventura incompleto')
    items={v['id']:v for v in module['opportunities']};known=set()
    if not isinstance(progress['discoveries'],list) or len(progress['discoveries'])>len(items):raise ValueError('Pistas importadas inválidas')
    for found in progress['discoveries']:
        if not isinstance(found,dict) or set(found)!={'id','text','character'}:raise ValueError('Pista importada inválida')
        identifier=found['id']
        if (not isinstance(identifier,str) or identifier not in items or identifier in known
            or found['text']!=items[identifier]['discovery'] or not set(items[identifier]['requires'])<=known
            or not isinstance(found['character'],str)):
            raise ValueError('La pista importada no coincide con la aventura')
        known.add(identifier)
    attempts=progress['attempts']
    if (not isinstance(attempts,dict) or any(k not in items or type(v)!=int or not 1<=v<=1000000 for k,v in attempts.items())
        or not known<=set(attempts)):
        raise ValueError('Registro de intentos inválido')
    if (type(progress['searchActions'])!=int or not sum(attempts.values())<=progress['searchActions']<=20*sum(attempts.values())
        or type(progress['completed'])!=bool
        or progress['completed']!=all(set(v['requires'])<=known for v in module['objectives'])):
        raise ValueError('Progreso de investigación inconsistente')
    state['adventureModule']=module
    state['location']=module['location'];state['goal']=module['goal']
    state['objectives']=[v['text'] for v in module['objectives'] if not set(v['requires'])<=known]


def public_view(state):
    module=state.get('adventureModule')
    if not module:return None
    progress=state['moduleProgress'];known={item['id'] for item in progress['discoveries']}
    return {'title':module['title'],'location':module['location'],'description':module['description'],
        'opportunities':[{'id':item['id'],'label':item['label']} for item in module['opportunities']
                         if item['id'] not in known and set(item['requires'])<=known],
        'objectives':[{'id':item['id'],'text':item['text'],'completed':set(item['requires'])<=known} for item in module['objectives']],
        'discoveries':copy.deepcopy(progress['discoveries']),'completed':progress['completed'],
        'searchActions':progress['searchActions'],
        'conclusion':module['conclusion'] if progress['completed'] else ''}


def investigation(state,body,me):
    if not state.get('adventure') or not state.get('adventureModule'):raise ValueError('No hay una investigación estructurada activa')
    import board_scenes
    board_scenes.require_no_remote_events(state)
    if state.get('pfContinuation'):
        import pf_scene_transition
        reason=pf_scene_transition.limitation(state,active=True)
        if reason:raise ValueError(reason)
    if state['board']['active']:raise ValueError('Este bloque de investigación no admite combate activo')
    if any(not p.get('investigation') for p in state['pending']):raise ValueError('Resuelve primero las pruebas o excepciones pendientes antes de buscar en condiciones tranquilas')
    if state['moduleProgress']['completed']:raise ValueError('La investigación ya está completada')
    character=next((c for c in state['characters'] if c['id']==body.get('character')),None)
    if not character or character.get('enemy'):raise ValueError('Selecciona un personaje jugador')
    board_scenes.require_present(state,character)
    if character['owner']!=me['id']:raise PermissionError('Solo el propietario elige qué investiga su personaje')
    if state.get('pfContinuation',{}).get('format')=='cronicas-pf-continuation-2' and character['owner']!=me.get('id'):
        raise PermissionError('Solo el propietario elige qué investiga su personaje en esta ruta')
    import pf_light_exploration
    if character['hp']<=0 and not pf_light_exploration.eligible(state,character):raise ValueError('El estado del personaje requiere una resolución excepcional')
    checks.modifier(character,'skill','Percepción')
    item=next((v for v in state['adventureModule']['opportunities'] if v['id']==body.get('opportunity')),None)
    known={v['id'] for v in state['moduleProgress']['discoveries']}
    if not item or item['id'] in known or not set(item['requires'])<=known:raise ValueError('Investigación no disponible')
    if any(p.get('investigation') for p in state['pending']):raise ValueError('Resuelve primero la investigación pendiente')
    return {'character':character['id'],'checkKind':'skill','key':'Percepción','dc':item['dc'],
            'reason':item['label']+'. CD adjudicada por la aventura; entorno sin modificadores adicionales.',
            'opportunity':item['id']}


def validate_pending(state,pending):
    if not pending.get('investigation'):return
    spec=pending['check']
    # Revalidate before RNG: stale imports, scene changes or edited pending records cannot grant clues.
    owner=next((c['owner'] for c in state['characters'] if c['id']==spec['character']),None)
    expected=investigation({**state,'pending':[]},{'character':spec['character'],'opportunity':pending['investigation']},{'host':True,'id':owner})
    if spec['kind']!='skill' or spec['key']!='Percepción' or spec['dc']!=expected['dc']:
        raise ValueError('La investigación pendiente no coincide con la aventura')


def resolve(state,pending,result):
    if not pending.get('investigation'):return None
    module=state['adventureModule'];progress=state['moduleProgress']
    item=next(v for v in module['opportunities'] if v['id']==pending['investigation'])
    progress['searchActions']+=20 if result.get('method')=='take20' else 1
    progress['attempts'][item['id']]=progress['attempts'].get(item['id'],0)+1
    if result['success']:
        progress['discoveries'].append({'id':item['id'],'text':item['discovery'],'character':result['character']})
    known={v['id'] for v in progress['discoveries']}
    progress['completed']=all(set(v['requires'])<=known for v in module['objectives'])
    state['objectives']=[v['text'] for v in module['objectives'] if not set(v['requires'])<=known]
    return item['discovery'] if result['success'] else item['failure']
