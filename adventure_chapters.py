"""Bounded original investigations in one place, with complete private history.

Only prepares a deterministic working copy. No provider, dice, persistence,
travel, elapsed-time calculation, healing, reward or character decision.
"""
import copy
import hashlib
import re
import adventure
import adventure_modules as modules
import character_builder
import campaign_world
from rule_pack_authoring import canonical

FORMAT='cronicas-adventure-chapters-1'
TRANSITION_FORMAT='cronicas-adventure-chapter-start-1'
MAX_CHAPTERS=8
MAX_ARCHIVE_BYTES=192000
ENTRY_FIELDS={'number','module','progress','summary','sha256'}


def _digest(entry):return hashlib.sha256(canonical({k:v for k,v in entry.items() if k!='sha256'}).encode('utf-8')).hexdigest()


def _validated_entry(entry,number):
    if (not isinstance(entry,dict) or set(entry)!=ENTRY_FIELDS or type(entry['number'])!=int or entry['number']!=number
        or not isinstance(entry['sha256'],str) or not re.fullmatch('[a-f0-9]{64}',entry['sha256'])
        or entry['sha256']!=_digest(entry)):
        raise ValueError('El archivo del capítulo no está íntegro')
    summary=adventure.text(entry['summary'],6000,'resumen del capítulo')
    temporary={'adventure':{'summary':summary},'adventureModule':copy.deepcopy(entry['module']),'moduleProgress':copy.deepcopy(entry['progress'])}
    modules.validate_restored(temporary)
    if not temporary['moduleProgress']['completed']:raise ValueError('Solo se archivan investigaciones completadas')
    if temporary['adventureModule']!=entry['module'] or summary!=entry['summary']:raise ValueError('El capítulo requiere su contenido original normalizado')
    return temporary


def validate_record(record):
    if (not isinstance(record,dict) or set(record)!={'format','current','completed'} or record['format']!=FORMAT
        or type(record['current'])!=int or not 2<=record['current']<=MAX_CHAPTERS
        or not isinstance(record['completed'],list) or len(record['completed'])!=record['current']-1):
        raise ValueError('Secuencia de capítulos inválida')
    if len(canonical(record).encode('utf-8'))>MAX_ARCHIVE_BYTES:raise ValueError('El archivo de capítulos alcanza su límite; conserva una copia antes de ampliar el recorrido')
    anchor=None
    for number,entry in enumerate(record['completed'],1):
        temporary=_validated_entry(entry,number);location=temporary['adventureModule']['location']
        if anchor is not None and location!=anchor:raise ValueError('Los capítulos de este recorrido permanecen en el mismo lugar')
        anchor=location
    return copy.deepcopy(record)


def validate_restored(state):
    if 'adventureChapterTransition' in state:raise ValueError('Una apertura pendiente no se importa como capítulo confirmado')
    record=state.get('adventureChapters')
    markers=[m['adventureChapterStart'] for m in state.get('messages',[]) if 'adventureChapterStart' in m]
    if record is None:
        if markers:raise ValueError('Falta el archivo de los capítulos anteriores')
        return
    record=validate_record(record)
    if not state.get('adventure') or not state.get('adventureModule'):raise ValueError('Falta la investigación del capítulo actual')
    if state['adventureModule']['location']!=record['completed'][-1]['module']['location']:
        raise ValueError('Esta continuación conserva el lugar; no representa un viaje')
    expected=[{'number':entry['number']+1,'previousSha256':entry['sha256']} for entry in record['completed']]
    if markers!=expected:raise ValueError('El registro de apertura no corresponde a los capítulos conservados')


def public_view(record):
    if record is None:return None
    record=validate_record(record);completed=[]
    for entry in record['completed']:
        view=modules.public_view(_validated_entry(entry,entry['number']))
        completed.append({'number':entry['number'],'title':view['title'],'location':view['location'],
            'goal':entry['module']['goal'],'summary':entry['summary'],'discoveries':view['discoveries'],'conclusion':view['conclusion'],'sha256':entry['sha256']})
    return {'current':record['current'],'completed':completed,
        'clockUncertain':any(entry['progress']['searchActions']>0 for entry in record['completed'])}


def _next_record(state):
    current=state.get('adventureChapters',{}).get('current',1)
    entry={'number':current,'module':copy.deepcopy(state['adventureModule']),
        'progress':copy.deepcopy(state['moduleProgress']),'summary':state['adventure']['summary']}
    entry['sha256']=_digest(entry)
    history=copy.deepcopy(state.get('adventureChapters',{}).get('completed',[]));history.append(entry)
    record=validate_record({'format':FORMAT,'current':current+1,'completed':history})
    return current,entry,record


def _context_limitation(state):
    if not state.get('adventure') or not state.get('adventureModule') or not state.get('moduleProgress',{}).get('completed'):
        return 'Termina la investigación actual antes de elegir otro objetivo.'
    if any(state.get(key) for key in ('pfEncounter','pfContinuation','adventureRoute','boardScenes')):
        return 'Esta continuación todavía no cubre rutas ni el encuentro preparado del patio.'
    if state['board']['active'] or state['pending'] or any(not e.get('interpreted') for e in state['consequences']):return 'Resuelve primero el combate o las situaciones pendientes.'
    return None


def _actor_limitation(actor):
    if (not actor.get('creation') or actor['creation'].get('manualOverride') or actor.get('conditions','').strip()
        or type(actor.get('hp'))!=int or not 0<actor['hp']<=actor['maxHp']):
        return 'Esta continuación requiere una ficha del asistente con PG positivos y sin efectos pendientes.'
    try:
        built,_=character_builder.build(actor['creation']['choices'])
        if any(actor.get(key)!=built[key] for key in ('abilities','maxHp','level','speed','skillTotals','ac','attack','damage','saves','meleeProfile')):
            return 'La ficha necesita revisar sus cambios antes de este recorrido preparado.'
    except (ValueError,TypeError,KeyError):return 'Revisa el registro de la investigación antes de continuar.'
    return None


def _history_limitation(state):
    try:
        copy_state=copy.deepcopy(state);modules.validate_restored(copy_state);validate_restored(copy_state)
    except (ValueError,TypeError,KeyError):return 'Revisa el registro de la investigación antes de continuar.'
    if state['location']!=state['adventureModule']['location']:return 'Revisa el lugar actual antes de continuar aquí.'
    if state.get('adventureChapters',{}).get('current',1)>=MAX_CHAPTERS:return 'Has alcanzado los capítulos cubiertos; conserva una copia antes de ampliar el recorrido.'
    try:_next_record(state)
    except ValueError as error:return str(error)
    except (TypeError,KeyError):return 'Revisa el archivo de la investigación antes de continuar.'
    return None


def limitation(state,me):
    if state.get('ruleset','pathfinder-1e')!='pathfinder-1e' or state.get('mode','solo')!='solo':return 'Esta continuación cubre una investigación individual de Pathfinder.'
    if not me.get('host'):return 'El propietario inicia esta continuación desde su campaña individual.'
    reason=_context_limitation(state)
    if reason:return reason
    if len(state['characters'])!=1:return 'Esta primera continuación requiere un único personaje jugador.'
    actor=state['characters'][0]
    if actor.get('enemy') or actor.get('owner')!=me['id']:return 'Solo el propietario elige el siguiente objetivo de su personaje.'
    return _actor_limitation(actor) or _history_limitation(state)


def group_limitation(state,me):
    if state.get('ruleset','pathfinder-1e')!='pathfinder-1e' or state.get('mode')!='online':
        return 'Esta continuación compartida cubre dos jugadores de Pathfinder en sus propios dispositivos.'
    reason=_context_limitation(state)
    if reason:return reason
    actors=state['characters']
    if len(actors)!=2 or any(c.get('enemy') for c in actors):return 'Esta continuación cubre dos personajes jugadores.'
    owners=[c.get('owner') for c in actors]
    if any(not isinstance(owner,str) or not owner for owner in owners) or len(set(owners))!=2:
        return 'Cada personaje necesita un propietario distinto para elegir el objetivo juntos.'
    if me['id'] not in owners:return 'Solo los propietarios eligen el siguiente objetivo de sus personajes.'
    for actor in actors:
        reason=_actor_limitation(actor)
        if reason:return reason
    return _history_limitation(state)


def prepare_next(state,body,me):
    shared=state.get('mode')=='online'
    allowed={'type','id','version','premise','worldMemoryContract','captureContract'}|({'proposalId'} if shared else set())
    if body.get('type')!='next_adventure' or set(body)-allowed:
        raise ValueError('Elige otro objetivo sin añadir consecuencias arbitrarias')
    if body.get('worldMemoryContract')!=campaign_world.CONTRACT:raise ValueError('Contrato de continuidad del mundo no disponible')
    if body.get('captureContract','pf-director-action-1')!='pf-director-action-1':raise ValueError('Contrato de captura no disponible')
    if shared:
        import adventure_goals as goals
        if body.get('captureContract')!='pf-director-action-1':raise ValueError('La continuación compartida requiere conservar el envío original')
        premise=goals.accept(state,body,me)['premise']
    else:
        if not me.get('host') or any(c.get('owner')!=me['id'] for c in state['characters'] if not c.get('enemy')):
            raise PermissionError('Solo el propietario inicia el siguiente objetivo de su campaña individual')
        reason=limitation(state,me)
        if reason:raise ValueError(reason)
        premise=adventure.text(body.get('premise'),2000,'nuevo objetivo')
    current,entry,record=_next_record(state)
    result=copy.deepcopy(state);result['adventureChapters']=record
    result.pop('chapterGoalProposal',None)
    if 'campaignWorld' not in result:result['campaignWorld']=campaign_world.empty()
    else:campaign_world.validate(result['campaignWorld'])
    result.pop('adventureModule');result.pop('moduleProgress');result.pop('adventureModuleView',None)
    result['adventureChapterTransition']={'format':TRANSITION_FORMAT,'from':current,'to':current+1,'location':state['location'],
        'previousSha256':entry['sha256'],'premise':premise}
    return result


def transition(state):
    item=state.get('adventureChapterTransition')
    if item is None:return None
    history=state.get('adventureChapters') or state.get('adventureChaptersView') or {}
    previous=history.get('completed',[])[-1] if history.get('completed') else {}
    if (not isinstance(item,dict) or set(item)!={'format','from','to','location','previousSha256','premise'}
        or item['format']!=TRANSITION_FORMAT or type(item['from'])!=int or type(item['to'])!=int
        or not 1<=item['from']<item['to']<=MAX_CHAPTERS or item['to']!=item['from']+1
        or item['to']!=history.get('current') or item['from']!=previous.get('number') or item['previousSha256']!=previous.get('sha256')
        or item['location']!=state['location'] or not isinstance(item['premise'],str) or not item['premise'].strip()
        or len(item['premise'])>2000):raise ValueError('La nueva apertura no corresponde al capítulo anterior')
    return copy.deepcopy(item)
