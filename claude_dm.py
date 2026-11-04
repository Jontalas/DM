"""Director narrativo: API Messages de Anthropic, exclusivamente Claude Haiku."""
import json
import copy
import os
import urllib.request
import urllib.error
from adventure import MEMORY_SCHEMA, validate_memory
from narrative_text import normalize_response, repair_text
import adventure_modules
from director_prompt import system_prompt

DEFAULT_MODEL='claude-haiku-5-5'
SCHEMA={'type':'object','properties':{'narration':{'type':'string'},'proposals':{'type':'array','items':{'type':'object','properties':{'type':{'type':'string','enum':['manual']},'reason':{'type':'string'}},'required':['type','reason'],'additionalProperties':False}}},'required':['narration','proposals'],'additionalProperties':False}
SCHEMA['properties']['checks']={'type':'array','items':{'type':'object','properties':{
    'character':{'type':'string'},'kind':{'type':'string','enum':['ability','save','skill']},
    'key':{'type':'string'},'dc':{'type':'integer'},'reason':{'type':'string'}},
    'required':['character','kind','key','dc','reason'],'additionalProperties':False}}
SCHEMA['properties']['memory']=MEMORY_SCHEMA
SCHEMA['properties']['adventureModule']=adventure_modules.MODULE_SCHEMA
SCHEMA['properties']['investigation']={'type':'object','properties':{
    'requested':{'type':'boolean'},'character':{'type':'string'},'opportunity':{'type':'string'}},
    'required':['requested','character','opportunity'],'additionalProperties':False}
def model_name():
    name=os.environ.get('ANTHROPIC_MODEL',DEFAULT_MODEL)
    if not name.startswith('claude-haiku-'):raise ValueError('ANTHROPIC_MODEL debe ser un modelo Claude Haiku')
    return name


def response_schema(state,rules=False,starting=False):
    """The provider cannot propose player actions in an opening or rules lookup."""
    schema=copy.deepcopy(SCHEMA)
    allowed={'narration','proposals'}
    if starting:
        allowed.discard('proposals');schema['required']=['narration']
        allowed.add('memory');schema['required'].append('memory')
        if not state.get('adventureModule'):
            allowed.add('adventureModule');schema['required'].append('adventureModule')
    elif not rules:
        allowed.add('checks')
        if state.get('adventure'):allowed.add('memory')
        if (state.get('adventureModule') and not state['moduleProgress']['completed'] and not state['pending']
            and state['messages'] and state['messages'][-1].get('kind')=='action'):
            allowed.add('investigation')
    schema['properties']={k:v for k,v in schema['properties'].items() if k in allowed}
    return schema


def build_context(state,text,refs,rules=False,check_actors=None,starting=False):
    """Separate player-visible state, director knowledge and personal privacy."""
    public={k:v for k,v in state.items() if k not in {'secrets','directorNotes','directorMemory','adventureModule','private','messages'}}
    if state.get('adventureModule'):public['adventureModuleView']=adventure_modules.public_view(state)
    public['characters']=[{k:v for k,v in c.items() if k!='creation'} for c in state.get('characters',[])]
    history=[{'speaker':m['speaker'],'kind':m['kind'],'text':repair_text(m['text']) if m.get('kind')=='director' else m['text'],
              **({'check':m['check']} if m.get('kind')=='rules' and m.get('check') else {})} for m in state['messages'][-30:]
             if m.get('visibility','public')=='public' and m.get('kind')!='private']
    context={'state':public,'history':history,'sources':[{'book':r['book'],'pdf_page':r['page'],'text':r['text'][:6500]} for r in refs],
             'request':text,'rulesOnly':rules,'checkActors':check_actors or [],
             'operation':'rules' if rules else 'startAdventure' if starting else 'narrate'}
    if not rules:
        declarations=[i for i,m in enumerate(history) if m['kind'] in ('action','dialogue')]
        context['playerAgency']={'declarationsInHistory':declarations,
                                 'activeDeclaration':declarations[-1] if declarations and declarations[-1]==len(history)-1 else None}
        if starting or state.get('adventureModule'):
            context['verifiedRules']=[{'book':'reglas','pdf_pages':[87,101],'coverage':'Percepcion preparada: d20 mas total contra CD de la aventura. Buscar es accion de movimiento; reintentar si persiste el estimulo. Elegir 10 sin amenazas/distracciones; elegir 20 con tiempo y sin consecuencias de fallo, invirtiendo veinte veces el esfuerzo.'}]
        if starting:
            totals=[row['total'] for c in state['characters'] if not c.get('enemy') and c.get('hp',0)>0 and not c.get('conditions','').strip()
                    for row in c.get('skillTotals',[]) if row.get('name')=='Percepción' and type(row.get('total'))==int]
            context['investigationLimits']={'maxReachableDc':20+max(totals) if totals else None}
    # Rules consultations do not need adventure spoilers. Personal notes never go to the provider.
    if not rules:
        knowledge={key:state[field] for key,field in [('preparation','directorNotes'),('memory','directorMemory')] if state.get(field)}
        if state.get('adventureModule'):knowledge['adventureModule']=state['adventureModule']
        if knowledge:context['directorKnowledge']=knowledge
    return context


def ai_reply(state,text,refs,rules=False,check_actors=None,starting=False):
    key=os.environ.get('ANTHROPIC_API_KEY')
    if not key:raise ValueError('Claude Haiku sin configurar: falta ANTHROPIC_API_KEY en el servidor. La acción no se ha guardado')
    context=build_context(state,text,refs,rules,check_actors,starting)
    budget=4500 if starting and not state.get('adventureModule') else 3000
    body={'model':model_name(),'max_tokens':budget,'system':system_prompt(rules,starting),'messages':[{'role':'user','content':json.dumps(context,ensure_ascii=False)}],'output_config':{'format':{'type':'json_schema','schema':response_schema(state,rules,starting)}}}
    req=urllib.request.Request('https://api.anthropic.com/v1/messages',data=json.dumps(body).encode(),headers={'Content-Type':'application/json','x-api-key':key,'anthropic-version':'2023-06-01'})
    stage='transport';stop_reason=None
    try:
        with urllib.request.urlopen(req,timeout=120) as response:output=json.load(response)
        stage='completion';stop_reason=output.get('stop_reason')
        if output.get('stop_reason')!='end_turn':raise ValueError('Claude no completó la respuesta')
        stage='json'
        text=''.join(block['text'] for block in output.get('content',[]) if block.get('type')=='text')
        result=normalize_response(json.loads(text))
        if starting and isinstance(result,dict) and 'proposals' not in result:result['proposals']=[]
        stage='narration'
        if not isinstance(result,dict) or not isinstance(result.get('narration'),str) or not result['narration'].strip() or not isinstance(result.get('proposals'),list):raise ValueError('Respuesta inválida')
        if len(result['narration'])>30000 or any(not isinstance(p,dict) or p.get('type')!='manual' or not isinstance(p.get('reason'),str) for p in result['proposals']):raise ValueError('Propuestas inválidas')
        requests=result.get('checks',[])
        stage='checks'
        if not isinstance(requests,list) or len(requests)>3:raise ValueError('Pruebas inválidas')
        for item in requests:
            if (not isinstance(item,dict) or item.get('kind') not in ('ability','save','skill')
                or any(not isinstance(item.get(k),str) or not item[k].strip() for k in ('character','key','reason'))
                or len(item['reason'])>500 or type(item.get('dc'))!=int or not 0<=item['dc']<=1000):raise ValueError('Pruebas inválidas')
        if 'memory' in result:
            stage='memory'
            if rules:raise ValueError('Una consulta de reglas no puede actualizar la aventura')
            result['memory']=validate_memory(result['memory'])
        if 'investigation' in result:
            stage='investigation'
            item=result['investigation']
            if (rules or starting or not isinstance(item,dict) or set(item) not in ({'character','opportunity'},{'requested','character','opportunity'})
                or type(item.get('requested',True))!=bool):
                raise ValueError('Investigación inválida')
            if item.get('requested',True) is False:result.pop('investigation')
            elif result.get('checks') or any(not isinstance(item.get(k),str) or not item[k].strip() or len(item[k])>200 for k in ('character','opportunity')):
                raise ValueError('Investigación inválida')
        if 'adventureModule' in result:
            stage='module'
            if rules or not starting or state.get('adventureModule'):raise ValueError('El director no puede sustituir una aventura aportada o iniciada')
            result['adventureModule']=adventure_modules.validate_module(result['adventureModule'])
        return result
    except urllib.error.HTTPError as exc:
        code=exc.code;exc.close()
        raise ValueError(f'Claude Haiku devolvió HTTP {code}. Comprueba clave, permisos, modelo y cuota. La acción no se ha aplicado') from None
    except (OSError,KeyError,TypeError,ValueError,AttributeError) as exc:
        if stage=='completion' and stop_reason=='max_tokens':
            raise ValueError('El director agotó el límite de salida antes de completar la aventura. La acción no se ha aplicado (director:output_limit)') from None
        if stage=='module' and type(exc)==ValueError:
            # This stage only calls our allowlisted module validator; its errors never quote source prose.
            raise ValueError('El director entregó una aventura incompatible: '+str(exc)+'. La acción no se ha aplicado (director:module)') from None
        raise ValueError('Claude Haiku no entregó una respuesta completa y válida. La acción no se ha aplicado (director:'+stage+')') from None
