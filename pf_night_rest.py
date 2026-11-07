"""One authored safe night, not a general campaign time controller.

Core PDF192/printed191: eight hours of sleep, one HP per level.
Core PDF151/printed150: light armor does not cause sleep fatigue.
The scenario supplies safety/NPC activity. No RNG, provider or storage here.
"""
import copy
import hashlib
import character_builder
import npc_catalog
import pf_rest
from rule_pack_authoring import canonical

SCOPE='courtyard-safe-night-1'
FORMAT='cronicas-pf-night-rest-1'
START_TIME='Inicio de la noche del patio'
END_TIME='8 horas desde el comienzo del descanso en el patio'


def _participants(state):
    record=state.get('pfEncounter',{})
    actor=next((c for c in state['characters'] if c['id']==record.get('character')),None)
    npc=next((c for c in state['characters'] if c['id']==record.get('npc')),None)
    return actor,npc


def _profile(actor,npc,definition):
    if not actor or not npc:return 'Falta un participante del encuentro.'
    if actor.get('enemy') or actor.get('creation',{}).get('manualOverride') or not actor.get('creation'):
        return 'Este descanso requiere el personaje del asistente sin correcciones de perfil.'
    if actor['creation'].get('choices',{}).get('armor') not in ('leather','studded','chainshirt'):
        return 'Dormir con esta armadura necesita efectos de fatiga todavía no cubiertos; no se avanza tiempo.'
    try:expected,_=character_builder.build(actor['creation']['choices'])
    except (ValueError,KeyError,TypeError):return 'Las opciones del personaje necesitan revisión antes de dormir.'
    if any(canonical(actor.get(k))!=canonical(v) for k,v in expected.items() if k not in ('hp','notes')):
        return 'La ficha cambió respecto al personaje preparado; revisa sus correcciones.'
    if type(actor.get('hp'))!=int or not 0<actor['hp']<=actor['maxHp']:
        return 'Este descanso cubre únicamente personajes con PG positivos; la recuperación negativa sigue otro recorrido.'
    if npc.get('npcCreation',{}).get('template')!=definition['npc']['template'] or npc.get('npcCreation',{}).get('manualOverride'):
        return 'La guardiana necesita su perfil original para resolver esta noche.'
    try:npc_catalog.validate_character(npc,'pathfinder-1e')
    except ValueError:return 'La ficha de la guardiana necesita revisión antes de avanzar la noche.'
    if npc['hp']!=npc['maxHp'] and npc['hp']>-npc['abilities'][2]:
        return 'La guardiana está herida y necesita seguimiento propio antes de avanzar la noche.'
    if any(c.get('conditions','').strip() or any(k in c for k in ('recoveryCare','recoveryState')) for c in (actor,npc)):
        return 'Hay condiciones o seguimiento médico que este descanso todavía no resuelve.'
    return None


def limitation(state):
    record=state.get('pfEncounter')
    if not record or record['definition'].get('restScope')!=SCOPE:return 'Esta escena no incluye una noche de descanso preparada.'
    if state.get('pfNightRest'):return 'La noche preparada ya está resuelta; no se repite la curación.'
    if record['phase'] not in ('agreement','resolved') or state['board']['active']:return 'Resuelve primero el encuentro.'
    if any(state.get(k) for k in ('adventure','adventureModule','adventureRoute','pfContinuation','boardScenes')):
        return 'Esta noche se ofrece antes de investigar o salir del patio.'
    if len(state['characters'])!=2:return 'Hay otros participantes cuyo descanso y sucesos necesitan seguimiento.'
    if state['pending'] or state['board']['terrain'] or any(not e.get('interpreted') for e in state['consequences']):
        return 'Resuelve las situaciones pendientes antes de dormir.'
    if state['location']!=record['definition']['location'] or state['worldTime']!=START_TIME:
        return 'El lugar o el reloj cambiaron; no se supone una noche segura sin comprobarlos.'
    if any(k in record for k in ('recoveryOutcome','recoveryStart','recoveryLimit')):
        return 'El reloj médico necesita continuar su propio seguimiento; esta noche no lo sustituye.'
    if (state['board'].get('combatSerial',0)!=(1 if record['phase']=='resolved' else 0)
        or type(state['board']['round'])!=int or not 1<=state['board']['round']<=100):
        return 'Esta noche cubre solo el primer encuentro corto; el tiempo adicional necesita seguimiento.'
    return _profile(*_participants(state),record['definition'])


def _result(start,definition):
    if (not isinstance(start,dict) or set(start)!={'choices','hp','npcHp','worldTime','combatSerial','round','phase'}
        or start['worldTime']!=START_TIME or type(start['combatSerial'])!=int
        or start['combatSerial']!=(1 if start['phase']=='resolved' else 0)
        or type(start['round'])!=int or not 1<=start['round']<=100
        or start['phase'] not in ('agreement','resolved')):raise ValueError('Origen de descanso inválido')
    actor,_=character_builder.build(start['choices'])
    actor['hp']=start['hp'];actor['creation']={'choices':start['choices']}
    npc,source=npc_catalog.prepare(definition['npc']['template'],'pathfinder-1e',name=definition['npc']['name'])
    npc.update(id='receipt-npc',owner='director',enemy=True,x=1,y=0,hp=start['npcHp'],npcCreation={**source,'manualOverride':False})
    reason=_profile(actor,npc,definition)
    if reason:raise ValueError(reason)
    if start['phase']=='agreement' and npc['hp']!=npc['maxHp']:raise ValueError('El acuerdo no contiene una muerte de combate')
    return {'healing':pf_rest.night_healing(actor,elapsed_seconds=28800),'seconds':28800,
        'npcActivity':'dead' if npc['hp']<=-npc['abilities'][2] else 'awake-watch',
        'npcHpAfter':npc['hp'],'worldTimeAfter':END_TIME}


def rest(state,body,me):
    if body.get('type')!='rest_pf_night' or set(body)-{'type','id','version'}:raise ValueError('Elige la noche preparada; no se admiten horas o PG arbitrarios')
    actor,npc=_participants(state)
    if not actor or actor['owner']!=me['id']:raise PermissionError('Solo el propietario decide si su personaje duerme')
    import pf_encounters
    pf_encounters.validate_restored(state)
    reason=limitation(state)
    if reason:raise ValueError(reason)
    record=state['pfEncounter']
    start={'choices':copy.deepcopy(actor['creation']['choices']),'hp':actor['hp'],'npcHp':npc['hp'],
        'worldTime':state['worldTime'],'combatSerial':state['board'].get('combatSerial',0),'round':state['board']['round'],'phase':record['phase']}
    result=_result(start,record['definition'])
    receipt={'format':FORMAT,'encounterSha256':record['sha256'],'character':actor['id'],'npc':npc['id'],'start':start,'result':result}
    updated=copy.deepcopy(state)
    next(c for c in updated['characters'] if c['id']==actor['id'])['hp']=result['healing']['hpAfter']
    updated['worldTime']=result['worldTimeAfter'];updated['pfNightRest']=receipt
    from engine import log
    amount=result['healing']['amount']
    log(updated,actor['name']+' elige dormir la noche preparada: 8 horas sin interrupciones. Recupera '+str(amount)
        +' PG ('+str(actor['hp'])+' → '+str(result['healing']['hpAfter'])+'). '
        +('La guardiana permanece despierta y no recupera PG.' if result['npcActivity']=='awake-watch' else 'La guardiana permanece muerta.')
        +' Las heridas restantes y los objetos se conservan.',
        refs=[{'book':'reglas','page':192},{'book':'reglas','page':151}],
        nightRestSha256=hashlib.sha256(canonical(receipt).encode()).hexdigest())
    validate_restored(updated)
    state.clear();state.update(updated)


def validate_restored(state):
    receipt=state.get('pfNightRest');markers=[m['nightRestSha256'] for m in state.get('messages',[]) if 'nightRestSha256' in m]
    if receipt is None:
        if markers or (state.get('worldTime')==END_TIME and state.get('pfEncounter',{}).get('definition',{}).get('restScope')==SCOPE):
            raise ValueError('Falta el recibo de la noche registrada')
        return
    record=state.get('pfEncounter');actor,npc=_participants(state)
    if (not isinstance(receipt,dict) or set(receipt)!={'format','encounterSha256','character','npc','start','result'}
        or receipt['format']!=FORMAT or not record or record['definition'].get('restScope')!=SCOPE
        or receipt['encounterSha256']!=record['sha256'] or not actor or not npc
        or receipt['character']!=actor['id'] or receipt['npc']!=npc['id']):raise ValueError('La noche no corresponde al encuentro y sus participantes')
    if canonical(receipt['result'])!=canonical(_result(receipt['start'],record['definition'])):raise ValueError('La curación o el tiempo no coinciden con la noche registrada')
    if state['board'].get('combatSerial',0)<receipt['start']['combatSerial']:raise ValueError('La noche pertenece a un combate posterior al reloj de esta copia')
    if markers!=[hashlib.sha256(canonical(receipt).encode()).hexdigest()]:raise ValueError('El descanso no coincide con su registro de juego')


def public_view(state):
    if state.get('pfEncounter',{}).get('definition',{}).get('restScope')!=SCOPE:return None
    receipt=state.get('pfNightRest')
    return {'completed':bool(receipt),'reason':limitation(state),
        'result':copy.deepcopy(receipt['result']) if receipt else None}
