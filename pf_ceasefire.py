"""Voluntary truce in an authored scene; never a general Diplomacy resolver.

Core PDF184/183 and PDF189/188: a few spoken words are a free action.
Bestiary PDF167/166: this unchanged goblin speaks goblin only.
"""
import copy
import hashlib
from rule_pack_authoring import canonical
import combat

SCOPE='wounded-goblin-truce-1'
SHARED_SCOPE='wounded-common-guard-truce-1'
FORMAT='cronicas-pf-ceasefire-1'
SHARED_FORMAT='cronicas-pf-ceasefire-2'


def supported(definition):return isinstance(definition,dict) and definition.get('ceasefireScope') in (SCOPE,SHARED_SCOPE)


def offer_language(definition):return 'Común' if definition.get('ceasefireScope')==SHARED_SCOPE else 'Goblin'


def _shared_language(actor,npc,definition):
    choices=actor.get('creation',{}).get('choices',{})
    known=set(choices.get('languages',[]))
    if definition.get('ceasefireScope')==SCOPE:return 'Goblin' if 'Goblin' in known else None
    if choices.get('race','human')=='human':known.add('Común')
    npc_known=npc.get('npcCreation',{}).get('profile',{}).get('languages',[])
    language=offer_language(definition)
    return language if language in known and language in npc_known else None


def limitation(state):
    record=state.get('pfEncounter')
    if not record or not supported(record.get('definition')):
        return 'Esta escena no incluye una tregua preparada.'
    if record['phase']!='combat' or not state['board']['active'] or record.get('ceasefire'):
        return 'La tregua corresponde al enfrentamiento todavía activo.'
    import pf_encounters
    if not pf_encounters.participants_present(state,record) or len(state['characters'])!=2:
        return 'La tregua requiere a ambos participantes presentes en el patio.'
    actor=next(c for c in state['characters'] if c['id']==record['character'])
    npc=next(c for c in state['characters'] if c['id']==record['npc'])
    if not _shared_language(actor,npc,record['definition']):
        return 'Esta conversación breve requiere conocer el idioma goblin.' if record['definition'].get('ceasefireScope')==SCOPE else 'Esta tregua requiere un idioma compartido verificado.'
    if actor['hp']<0:
        return 'Este recorrido preparado no cubre todavía la respuesta con PG negativos.'
    if not combat.standing(actor) or not 0<npc['hp']<npc['maxHp']:
        return 'La guardiana ofrece esta tregua cuando está herida y ambos podéis responder.'
    if any(c.get('conditions','').strip() or c.get('creation',{}).get('manualOverride')
        or c.get('npcCreation',{}).get('manualOverride') for c in (actor,npc)):
        return 'Las condiciones o correcciones requieren revisar esta conversación.'
    board=state['board']
    if (board.get('combatSerial')!=1 or type(board['round'])!=int or not 1<=board['round']<=100
        or not board['order'] or board['order'][board['turn']]['id']!=actor['id']):
        return 'Esta respuesta preparada se ofrece en tu turno del primer combate corto.'
    if state['pending'] or board['terrain'] or any(not e.get('interpreted') for e in state['consequences']):
        return 'Resuelve las situaciones pendientes antes de acordar la tregua.'
    return None


def accept(state,body,me):
    if body.get('type')!='accept_pf_ceasefire' or set(body)-{'type','id','version'}:
        raise ValueError('Elige aceptar la tregua sin añadir consecuencias arbitrarias')
    import pf_encounters
    pf_encounters.validate_restored(state)
    record=state.get('pfEncounter') or {}
    actor=next((c for c in state['characters'] if c['id']==record.get('character')),None)
    if not actor or actor['owner']!=me['id']:raise PermissionError('Solo el propietario decide si acepta la tregua')
    reason=limitation(state)
    if reason:raise ValueError(reason)
    npc=next(c for c in state['characters'] if c['id']==record['npc'])
    shared=record['definition'].get('ceasefireScope')==SHARED_SCOPE
    language=_shared_language(actor,npc,record['definition'])
    receipt={'format':SHARED_FORMAT if shared else FORMAT,'encounterSha256':record['sha256'],'character':actor['id'],'npc':npc['id'],
        'actorHp':actor['hp'],'npcHp':npc['hp'],'combatSerial':1,'round':state['board']['round']}
    if shared:receipt['sharedLanguage']=language
    result=copy.deepcopy(state)
    result['pfEncounter'].update(phase='agreement',ceasefire=receipt)
    result['board']['active']=False;result['board'].pop('autoPaused',None)
    from engine import log
    acceptance=(actor['name']+' acepta con unas palabras la tregua que la guardiana herida ofrece en común. ' if shared
        else actor['name']+' acepta con unas palabras en goblin la tregua que ofrece la guardiana herida. ')
    log(result,acceptance
        +'Ambos dejan de combatir. Las heridas, objetos y posiciones se conservan; no pasa tiempo adicional. '
        +'La guardiana permite el paso. Tú decides si continúas.',
        refs=[{'book':'reglas','page':184},{'book':'reglas','page':189},{'book':'bestiario','page':167}],
        ceasefireSha256=hashlib.sha256(canonical(receipt).encode()).hexdigest())
    validate_restored(result)
    state.clear();state.update(result)


def validate_restored(state):
    record=state.get('pfEncounter') or {}
    if not isinstance(record,dict):record={}
    receipt=record.get('ceasefire')
    definition=record.get('definition') or {}
    if not isinstance(definition,dict):definition={}
    markers=[m['ceasefireSha256'] for m in state.get('messages',[]) if 'ceasefireSha256' in m]
    if receipt is None:
        if markers:raise ValueError('Falta el registro de la tregua aceptada')
        if (supported(definition) and record.get('phase')=='agreement'
            and state['board'].get('combatSerial',0)>0):
            raise ValueError('El acuerdo tras combatir necesita su registro de tregua')
        return
    shared=definition.get('ceasefireScope')==SHARED_SCOPE
    fields={'format','encounterSha256','character','npc','actorHp','npcHp','combatSerial','round'}|({'sharedLanguage'} if shared else set())
    if (not isinstance(receipt,dict) or set(receipt)!=fields or receipt['format']!=(SHARED_FORMAT if shared else FORMAT)
        or not supported(definition)
        or receipt['encounterSha256']!=record.get('sha256')
        or receipt['character']!=record.get('character') or receipt['npc']!=record.get('npc')
        or type(receipt['combatSerial'])!=int or receipt['combatSerial']!=1
        or type(receipt['round'])!=int or not 1<=receipt['round']<=100):
        raise ValueError('La tregua no corresponde al encuentro preparado')
    actor=next((c for c in state['characters'] if c['id']==receipt['character']),None)
    npc=next((c for c in state['characters'] if c['id']==receipt['npc']),None)
    if (not actor or not npc or not _shared_language(actor,npc,definition)
        or shared and receipt['sharedLanguage']!=_shared_language(actor,npc,definition)
        or type(receipt['actorHp'])!=int or not 0<=receipt['actorHp']<=actor['maxHp']
        or type(receipt['npcHp'])!=int or not 0<receipt['npcHp']<npc['maxHp']
        or state['board'].get('combatSerial',0)<1
        or record['phase']=='offered'
        or markers!=[hashlib.sha256(canonical(receipt).encode()).hexdigest()]):
        raise ValueError('La tregua no coincide con sus participantes o su registro')
