"""Pure first-aid episode for an authored, positive-HP adjacent NPC.

Not yet a general NPC policy: caller must verify the definition, prepared
skill and both original profiles. The helper uses its next free standard
action; the dying PC keeps its own initiative checks. No movement or IA.
"""
import copy
import hashlib
import checks
import combat
import pf_first_aid
import pf_stabilization

SCOPE='npc-first-aid-on-defeat-1'
FORMAT='cronicas-pf-first-aid-episode-1'
TEMPLATE='pf1-common-speaking-first-aid-guard-1'


def _participants(start):
    if (not isinstance(start,dict) or set(start)!={'epoch','round','initiative','order','patient','helper','spent'}
        or type(start['epoch'])!=int or start['epoch']!=1 or type(start['round'])!=int or not 1<=start['round']<=550
        or not isinstance(start['order'],list) or len(start['order'])!=2
        or any(not isinstance(v,str) or not 1<=len(v)<=80 for v in start['order'])
        or len(set(start['order']))!=2 or start['initiative'] not in start['order']):raise ValueError('Reloj del auxilio preparado inválido')
    pc,npc=start['patient'],start['helper']
    if (not isinstance(pc,dict) or set(pc)!={'id','hp','constitution','x','y'}
        or not isinstance(npc,dict) or set(npc)!={'id','hp','heal','x','y'}
        or any(not isinstance(c['id'],str) or not 1<=len(c['id'])<=80 for c in (pc,npc))
        or pc['id']==npc['id'] or {pc['id'],npc['id']}!=set(start['order'])
        or type(pc['constitution'])!=int or not 1<=pc['constitution']<=20
        or type(pc['hp'])!=int or not -pc['constitution']<pc['hp']<0
        or type(npc['hp'])!=int or not 1<=npc['hp']<=10000
        or any(type(c[key])!=int or not 0<=c[key]<20 for c in (pc,npc) for key in ('x','y'))):raise ValueError('Participantes del auxilio preparado inválidos')
    checks.integer(npc['heal'])
    spent=start['spent'];allowed={'move','standard','swift','immediate','swiftDebt'}
    if (not isinstance(spent,dict) or not set(spent)<=set(start['order'])
        or any(not isinstance(v,dict) or not set(v)<=allowed or any(type(value)!=bool for value in v.values()) for v in spent.values())):raise ValueError('Presupuesto de auxilio inválido')
    patient={**pc,'abilities':[10,10,pc['constitution'],10,10,10],'stable':False,'conditions':''};patient.pop('constitution')
    helper={k:v for k,v in npc.items() if k!='heal'}
    helper.update(abilities=[10]*6,skillTotals=[{'name':'Curar','total':npc['heal']}],conditions='')
    pf_first_aid.validate(helper,patient,{},round_number=start['round'],order=start['order'],epoch=start['epoch'])
    return patient,helper


def simulate(start,draw):
    """draw(kind) supplies one d20; no draw after stability or death."""
    patient,helper=_participants(start);order=start['order'][:];round_number=start['round'];index=order.index(start['initiative'])
    spent=copy.deepcopy(start['spent']);rolls=[];audit=[];begun=[]
    for _ in range((patient['abilities'][2]+1)*2+2):
        if combat.health_status(patient)!='moribundo':break
        if order[index]==helper['id'] and not spent.get(helper['id'],{}).get('standard'):
            pf_first_aid.validate(helper,patient,spent.get(helper['id'],{}),round_number=round_number,order=order,epoch=1)
            raw=draw('first-aid');result=pf_first_aid.resolve(helper,patient,spent.get(helper['id'],{}),die=raw,round_number=round_number,order=order,epoch=1)
            rolls.append(['first-aid',raw]);patient=result['patient'];helper=result['helper'];spent[helper['id']]=result['spent']
            audit.append({'kind':'first-aid','round':round_number,'initiative':helper['id'],'check':result['check'],'patient':patient['id']})
            if combat.health_status(patient)!='moribundo':break
        index+=1
        if index==len(order):index=0;round_number+=1
        current=order[index];budget=spent.get(current,{})
        spent[current]={'swift':True} if budget.get('swiftDebt') else {};begun.append(current)
        if current==patient['id']:
            raw=draw('stabilization');result=pf_stabilization.resolve(patient,die=raw,round_number=round_number,order=order,epoch=1)
            patient=result['patient'];rolls.append(['stabilization',raw])
            audit.append({'kind':'stabilization','round':round_number,'initiative':current,**{k:v for k,v in result.items() if k!='patient'}})
    else:raise ValueError('El auxilio excedió su límite sin desenlace verificable')
    if combat.health_status(patient)=='moribundo':raise ValueError('El auxilio no puede confirmar una espera parcial')
    return {'patient':patient,'helper':helper,'round':round_number,'initiative':order[index],'spent':spent,
        'rolls':rolls,'audit':audit,'begunTurns':begun,'assisted':patient.get('recoveryCare',{}).get('assisted')}


def supported(definition):return isinstance(definition,dict) and definition.get('npcAidScope')==SCOPE and definition.get('npc',{}).get('template')==TEMPLATE


def _snapshot(state):
    record=state['pfEncounter'];board=state['board'];pc=next(c for c in state['characters'] if c['id']==record['character']);npc=next(c for c in state['characters'] if c['id']==record['npc'])
    return {'epoch':board.get('combatSerial'),'round':board['round'],'initiative':board['order'][board['turn']]['id'],
        'order':[v['id'] for v in board['order']],
        'patient':{key:pc[key] for key in ('id','hp','x','y')}|{'constitution':pc['abilities'][2]},
        'helper':{key:npc[key] for key in ('id','hp','x','y')}|{'heal':checks.modifier(npc,'skill','Curar')[0]},'spent':copy.deepcopy(board['spent'])}


def limitation(state):
    record=state.get('pfEncounter') or {};board=state['board']
    if not supported(record.get('definition')):return 'Esta guardiana no tiene el auxilio automático preparado.'
    if record.get('phase')!='combat' or not board['active'] or record.get('npcAidEpisode'):return 'El auxilio corresponde al primer desenlace del combate.'
    if len(state['characters'])!=2:return 'Este auxilio cubre únicamente a los dos participantes preparados.'
    import board_scenes
    pc=next(c for c in state['characters'] if c['id']==record['character']);npc=next(c for c in state['characters'] if c['id']==record['npc'])
    if not all(board_scenes.present(state,c) for c in (pc,npc)):return 'El auxilio necesita ambos participantes presentes.'
    if combat.health_status(pc)!='moribundo' or npc['hp']<=0:return 'El auxilio necesita PJ moribundo y guardiana con PG positivos.'
    if (any(c.get('conditions','').strip() or c.get('creation',{}).get('manualOverride') or c.get('npcCreation',{}).get('manualOverride') for c in (pc,npc))
        or board['terrain'] or state['pending'] or any(not e.get('interpreted') for e in state['consequences'])
        or pc.get('recoveryState') or pc.get('recoveryCare')):return 'El auxilio necesita perfiles y circunstancias sin situaciones pendientes.'
    try:
        import character_builder,npc_catalog
        original,_=character_builder.build(pc['creation']['choices'])
        if any(pc.get(key)!=original[key] for key in ('abilities','maxHp','level','speed','skillTotals')):return 'El auxilio necesita la ficha original verificada.'
        npc_catalog.validate_character(npc,'pathfinder-1e');_participants(_snapshot(state))
    except (ValueError,KeyError,TypeError,IndexError):return 'El auxilio necesita el primer combate corto y un paciente adyacente.'
    return None


def _receipt(record,start,result):
    patient=result['patient']
    return {'format':FORMAT,'encounterSha256':record['sha256'],'start':copy.deepcopy(start),'rolls':copy.deepcopy(result['rolls']),
        'end':{'hp':patient['hp'],'stable':bool(patient.get('stable',False)),'care':copy.deepcopy(patient.get('recoveryCare')),
            'round':result['round'],'initiative':result['initiative'],'attempts':sum(kind=='first-aid' for kind,_ in result['rolls'])}}


def apply(state):
    reason=limitation(state)
    if reason:raise ValueError(reason)
    import game_randomness
    from rule_pack_authoring import canonical
    start=_snapshot(state);result=simulate(start,lambda kind:game_randomness.draw(20));updated=copy.deepcopy(state);record=updated['pfEncounter']
    pc=next(c for c in updated['characters'] if c['id']==record['character']);npc=next(c for c in updated['characters'] if c['id']==record['npc'])
    for key in ('hp','stable','recoveryCare','recoveryState'):
        if key in result['patient']:pc[key]=copy.deepcopy(result['patient'][key])
        else:pc.pop(key,None)
    board=updated['board'];board['round']=result['round'];board['turn']=start['order'].index(result['initiative']);board['spent']=result['spent']
    if 'acted' in board:
        for identifier in result['begunTurns']:
            if identifier not in board['acted']:board['acted'].append(identifier)
    receipt=_receipt(record,start,result);record['npcAidEpisode']=receipt
    from engine import log
    for event in result['audit']:
        if event['kind']=='first-aid':
            check=event['check'];text=npc['name']+': primeros auxilios, d20 '+str(check['die'])+' '+str(check['modifier'])+' = '+str(check['total'])+' contra CD15. '+('El personaje queda estable sin recuperar PG.' if check['success'] else 'El personaje sigue moribundo; fallar no añade daño.')
            log(updated,'Asalto '+str(event['round'])+' · '+text,check=check|{'patient':pc['id']},refs=[{'book':'reglas','page':90},{'book':'reglas','page':93},{'book':'reglas','page':94}])
        else:
            check={'character':pc['id'],'kind':'ability','key':'con','name':'Estabilización','die':event['die'],'modifier':event['modifier'],'total':event['total'],'dc':10,'success':event['success'],'natural':'éxito automático' if event['die']==20 else None}
            log(updated,'Asalto '+str(event['round'])+' · '+pc['name']+': estabilización; PG '+str(event['hpBefore'])+' → '+str(event['hpAfter'])+'.',check=check,refs=[{'book':'reglas','page':191}])
    outcome='La guardiana estabiliza al personaje con primeros auxilios.' if result['assisted'] else 'El personaje se estabiliza mediante su propia comprobación.' if pc['stable'] else 'El personaje muere por sus heridas.'
    log(updated,outcome+' Se conservan las heridas y las decisiones del jugador.',npcAidSha256=hashlib.sha256(canonical(receipt).encode()).hexdigest(),refs=[{'book':'reglas','page':191}])
    # Automatic combat holds references to the live board. Commit the validated
    # delta in place so ending the encounter also updates that caller's board.
    live_patient=next(c for c in state['characters'] if c['id']==record['character'])
    live_patient.clear();live_patient.update(copy.deepcopy(pc))
    for key in ('round','turn','spent','acted'):
        if key in board:state['board'][key]=copy.deepcopy(board[key])
    state['pfEncounter']['npcAidEpisode']=copy.deepcopy(receipt)
    state['messages'][:]=updated['messages']


def validate_restored(state):
    from rule_pack_authoring import canonical
    record=state.get('pfEncounter') or {};record=record if isinstance(record,dict) else {}
    receipt=record.get('npcAidEpisode');markers=[m['npcAidSha256'] for m in state.get('messages',[]) if 'npcAidSha256' in m]
    if receipt is None:
        if markers:raise ValueError('Falta el episodio de auxilio registrado')
        start=record.get('recoveryStart') or {}
        rows=start.get('patients',[]) if isinstance(start,dict) else []
        first=rows[0] if isinstance(rows,list) and rows and isinstance(rows[0],dict) else {}
        pc=next((c for c in state.get('characters',[]) if c['id']==record.get('character')),{})
        current_care=pc.get('recoveryCare')
        assisted=(isinstance(first.get('care'),dict) and first['care'].get('assisted') is True) or (isinstance(current_care,dict) and current_care.get('assisted') is True)
        if supported(record.get('definition')) and assisted:raise ValueError('La asistencia del PJ necesita su episodio de auxilio')
        return None
    if (not supported(record.get('definition')) or not isinstance(receipt,dict) or set(receipt)!={'format','encounterSha256','start','rolls','end'}
        or receipt['format']!=FORMAT or receipt['encounterSha256']!=record.get('sha256')
        or not isinstance(receipt['rolls'],list) or not 1<=len(receipt['rolls'])<=42 or state['board'].get('combatSerial',0)<1):raise ValueError('Episodio de auxilio incompatible')
    start=receipt['start'];_participants(start)
    if start['patient']['id']!=record.get('character') or start['helper']['id']!=record.get('npc'):raise ValueError('El auxilio no corresponde a sus participantes')
    import npc_catalog
    original,_=npc_catalog.prepare(TEMPLATE,'pathfinder-1e')
    if start['helper']['hp']>original['maxHp'] or start['helper']['heal']!=checks.modifier(original,'skill','Curar')[0]:raise ValueError('El auxilio necesita el perfil original del PNJ')
    index=0
    def replay(kind):
        nonlocal index
        if index>=len(receipt['rolls']):raise ValueError('Faltan comprobaciones del auxilio')
        row=receipt['rolls'][index];index+=1
        if not isinstance(row,list) or len(row)!=2 or row[0]!=kind:raise ValueError('Orden de auxilio inválido')
        return row[1]
    result=simulate(start,replay)
    if index!=len(receipt['rolls']) or canonical(receipt)!=canonical(_receipt(record,start,result)) or markers!=[hashlib.sha256(canonical(receipt).encode()).hexdigest()]:raise ValueError('El auxilio no coincide con sus comprobaciones')
    if state['board'].get('combatSerial')==1:
        outcome=record.get('outcome') or {};pc=result['patient']
        if not isinstance(outcome,dict):raise ValueError('Desenlace del auxilio inválido')
        if (record.get('phase')!='defeated' or (pc['hp'],bool(pc.get('stable',False)),start['patient']['constitution'],start['helper']['hp'],result['round'])
            !=(outcome.get('hp'),outcome.get('stable'),outcome.get('constitution'),outcome.get('npcHp'),outcome.get('round'))):raise ValueError('El auxilio no coincide con su desenlace')
        recovery_start=record.get('recoveryStart') or {}
        if recovery_start:
            if (not isinstance(recovery_start,dict) or not isinstance(recovery_start.get('patients'),list) or not recovery_start['patients']
                or not isinstance(recovery_start['patients'][0],dict) or recovery_start['patients'][0].get('care')!=pc.get('recoveryCare')):raise ValueError('La recuperación perdió la asistencia verificada')
    return result
