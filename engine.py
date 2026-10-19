"""Motor determinista: ninguna respuesta narrativa puede escribir el estado."""
import math, secrets, time, copy
import combat
import tactics
import checks
import character_builder

def initial_state(config):
    return {'scene':1,'location':config.get('location','Por decidir'),'worldTime':'Comienzo de la aventura','goal':config.get('goal','Definir el objetivo con el grupo'),'objectives':[], 'allies':[],'enemies':[],'facts':{},'unknowns':[],'consequences':[], 'tokens':0,'threshold':int(config.get('threshold',15)),'turned':False,'voluntaryScene':0,'characters':[],'messages':[],'pending':[],'bookmarks':[],'private':{},'secrets':'','notes':'','tone':config.get('tone','Fantasía aventurera'),'limits':config.get('limits',''),'difficulty':config.get('difficulty','Estándar; encuentros pendientes de validar'),'mode':config.get('mode','solo'),'agreement':'Adaptación multijugador: reserva común de FH; el anfitrión registra el consentimiento unánime antes del gasto. Decisiones colectivas por consenso. No se alteran estadísticas para equilibrar encuentros.','criteria':['TREY p.25: el ejemplo d8=7 dice objetivo en curso; la tabla p.23 indica objetivo final. Se usa la tabla.','TREY p.25: ejemplo d6=5 dice retrasado; se aplica demorado, tabla p.23.','Pathfinder 1e: las ventajas de FH son una adaptación TREY; requieren adjudicación manual y registro.'],'board':{'active':False,'round':1,'turn':0,'order':[],'terrain':{},'spent':{}},'oracleLog':[]}
def log(s,text,kind='rules',**extra):
    s['messages'].append({'kind':kind,'speaker':'Motor de reglas' if kind=='rules' else 'Mesa','text':text,'time':time.time(),**extra})
def host(me):
    if not me['host']: raise PermissionError('Esta operación corresponde al anfitrión')
def char(s,cid,me):
    c=next((c for c in s['characters'] if c['id']==cid),None)
    if not c: raise ValueError('Personaje inexistente')
    if c['owner']!=me['id'] and not me['host']: raise PermissionError('No controlas este personaje')
    return c
def dice(sides,values=None):
    if values is not None:
        if len(values)!=len(sides) or any(type(v)!=int or not 1<=v<=d for v,d in zip(values,sides)): raise ValueError('Dados físicos fuera de rango')
        return values[:]
    return [secrets.randbelow(d)+1 for d in sides]
def oracle(raw,probability):
    a,b,c=raw
    mods={'neutral':0,'probable':math.ceil(c/2),'muy probable':c,'improbable':-math.ceil(c/2),'muy improbable':-c}
    if probability not in mods: raise ValueError('Probabilidad inválida')
    total=max(1,min(10,a+mods[probability])); result='No excepcional' if total==1 else 'No' if total<=5 else 'Sí excepcional' if total==10 else 'Sí'
    return total,result,3 if len(set(raw))==1 else 2 if len(set(raw))==2 else 0
def event(s,exceptional=False,values=None,award=None):
    raw=dice([10,8,6],values); a,b,c=raw
    outcome=('Muy negativo' if a<=5 else 'Muy positivo') if exceptional else ('Muy negativo' if a==1 else 'Negativo' if a<=5 else 'Muy positivo' if a==10 else 'Positivo')
    targets=['Afecta a tu personaje','Afecta a un PNJ cercano','Un PNJ cercano hace algo inesperado','Reaparece un PNJ conocido' if s['turned'] else 'Nuevo PNJ','Nuevo objeto' if s['turned'] else 'Nuevo objeto o pista','Objetivo en curso','Objetivo final','Giro de guion' if s['turned'] else 'Algo más inesperado']
    e={'raw':raw,'outcome':outcome,'target':targets[b-1],'when':['Inmediatamente','Pronto','Demorado'][(c-1)//2],'page':33 if s['turned'] else 23,'interpreted':False}
    gain=award if award is not None else 3 if exceptional else 2
    if not s['turned']:
        s['tokens']+=gain
        if s['tokens']>=s['threshold']: s['turned']=True
    s['consequences'].append(e)
    return e


def begin_turn(s):
    board=s['board'];upcoming=board['order'][board['turn']]['id']
    debt=board['spent'].get(upcoming,{}).get('swiftDebt')
    board['spent'][upcoming]={'swift':True} if debt else {}
    if 'acted' in board and upcoming not in board['acted']:board['acted'].append(upcoming)
    patient=next(c for c in s['characters'] if c['id']==upcoming)
    if patient.get('meleeProfile') and patient['hp']<0 and combat.health_status(patient)=='moribundo':
        if patient.get('conditions','').strip():
            log(s,patient['name']+': estabilización pendiente; las condiciones requieren resolución excepcional.')
        else:
            raw=dice([20])[0];modifier=(patient['abilities'][2]-10)//2+patient['hp']
            if raw==20 or raw+modifier>=10:patient['stable']=True
            else:patient['hp']-=1
            log(s,f"{patient['name']}: estabilización d20 {raw} {modifier:+} contra CD 10 → {combat.health_status(patient)}; PG {patient['hp']}.",refs=[{'book':'reglas','page':191}])


def advance_turn(s):
    board=s['board'];board['turn']+=1
    if board['turn']>=len(board['order']):board['turn']=0;board['round']+=1
    begin_turn(s)
    log(s,f"Siguiente turno · asalto {board['round']}")


def run_automatic_turns(s):
    board=s['board']
    if not board['active'] or not board.get('autoEnemies'):return
    board.pop('autoPaused',None)
    def pause(character,reason):
        board['autoPaused']={'character':character['id'],'reason':reason}
        log(s,character['name']+': automatización pausada. '+reason)
    # At most one initiative cycle; never loop through an all-unconscious party.
    for _ in range(len(board['order'])):
        current=next(c for c in s['characters'] if c['id']==board['order'][board['turn']]['id'])
        if not any(not c['enemy'] and c['hp']>=0 for c in s['characters']):
            pause(current,'No quedan personajes jugadores conscientes; revisa el desenlace y la asistencia a los caídos.')
            return
        if current['hp']<0:
            if combat.health_status(current)=='moribundo' and (not current.get('meleeProfile') or current.get('conditions','').strip()):
                pause(current,'La estabilización requiere una resolución excepcional.');return
            log(s,current['name']+': sin acciones por su estado; se conserva su iniciativa.')
            advance_turn(s);continue
        if not current['enemy']:return  # Never choose a player's actions.
        spent=board['spent'].get(current['id'],{})
        try:
            if not spent.get('standard') and not (current['hp']==0 and spent.get('move')):
                decision=tactics.plan(s,current,allow_move=not spent.get('move'))
                controller={'id':current['owner'],'name':'Motor táctico','host':True}
                if decision['path']:
                    apply_action(s,{'type':'move','character':current['id'],'path':decision['path'],'acknowledge':True},controller)
                if decision['target']:
                    apply_action(s,{'type':'attack','character':current['id'],'target':decision['target']},controller)
                elif not decision['path']:log(s,current['name']+': espera; no hay un ataque básico disponible.')
        except ValueError as exc:
            pause(current,str(exc));return
        log(s,current['name']+': termina su turno automático.')
        advance_turn(s)
    pause(current,'Ciclo automático detenido para revisar la iniciativa.')


def apply_action(s,b,me):
    kind=b['type']
    if kind=='talk':
        text=str(b['text']).strip()
        if not text or len(text)>12000: raise ValueError('Escribe entre 1 y 12000 caracteres')
        speaker=me['name']; cid=b.get('character')
        if cid: speaker=char(s,cid,me)['name']+' · '+me['name']
        k=b.get('kind','action')
        if k not in ['action','dialogue','ooc','private']: raise ValueError('Tipo de mensaje inválido')
        log(s,text,k,speaker=speaker,owner=me['id'],visibility='private' if k=='private' else 'public')
    elif kind=='create_character':
        if s['board']['active']:raise ValueError('Finaliza el combate antes de crear un personaje')
        if type(b.get('enemy',False))!=bool:raise ValueError('Tipo de participante inválido')
        if b.get('enemy'):host(me)
        data,creation=character_builder.build(b.get('choices'))
        data['enemy']=b.get('enemy',False);data['owner']=me['id']
        apply_action(s,{'type':'character','character':data},me)
        created=s['characters'][-1];created['creation']=creation
        log_entry=s['messages'][-1];log_entry['text']='Personaje creado automáticamente: '+created['name']+'. Humano guerrero 1; características, dotes, equipo, habilidades y perfil de combate calculados y validados.'
        log_entry['refs']=[{'book':'reglas','page':n} for n in (17,25,59,87,141,152,170)]
    elif kind=='character':
        d=copy.deepcopy(b['character']); cid=d.get('id')
        if cid:
            old=char(s,cid,me)
            if s['board']['active']: raise ValueError('Edita fichas fuera del combate; usa resoluciones asistidas durante el combate')
        else: old=None
        attrs=d.get('abilities',[10]*6)
        if len(attrs)!=6 or any(type(v)!=int or not 1<=v<=60 for v in attrs): raise ValueError('Características inválidas')
        hp=int(d.get('maxHp',10)); speed=int(d.get('speed',6))
        if not 1<=hp<=10000 or not 1<=speed<=100: raise ValueError('PG o velocidad inválidos')
        owner=d.get('owner',me['id'])
        if not me['host']: owner=me['id']
        data={'id':cid or secrets.token_hex(6),'name':str(d.get('name','Aventurero'))[:80],'owner':owner,'race':str(d.get('race','Humano')),'class':str(d.get('class','Sin clase')),'level':int(d.get('level',1)),'abilities':attrs,'hp':int(d.get('hp',hp)),'maxHp':hp,'ac':int(d.get('ac',10)),'saves':d.get('saves',[0,0,0]),'speed':speed,'initiative':int(d.get('initiative',(attrs[1]-10)//2)),'attack':int(d.get('attack',0)),'damage':str(d.get('damage','1d6')),'skills':d.get('skills',''),'feats':d.get('feats',''),'equipment':d.get('equipment',''),'spells':d.get('spells',''),'resources':d.get('resources',''),'conditions':d.get('conditions',''),'load':d.get('load',''),'notes':d.get('notes',''),'x':old['x'] if old else len(s['characters'])%12,'y':old['y'] if old else 0,'enemy':bool(d.get('enemy',False))}
        if data['enemy']: host(me)
        saves=data['saves']
        if not isinstance(saves,list) or len(saves)!=3:raise ValueError('Indica Fortaleza, Reflejos y Voluntad como tres totales')
        for value in saves:checks.integer(value)
        data['skillTotals']=checks.skill_totals(d.get('skillTotals',old.get('skillTotals',[]) if old else []))
        if old and old.get('creation'):data['creation']={**copy.deepcopy(old['creation']),'manualOverride':True}
        if d.get('meleeProfile') is not None:
            data['meleeProfile']=copy.deepcopy(d['meleeProfile']);combat.profile(data)
        if old: s['characters'][s['characters'].index(old)]=data
        else:
            occupied={(v['x'],v['y']) for v in s['characters']}
            free=next(((x,y) for y in range(20) for x in range(20) if (x,y) not in occupied and s['board']['terrain'].get(f'{x},{y}')!='wall'),None)
            if free is None: raise ValueError('Tablero de 20×20 lleno; libera una casilla antes de incorporar otra ficha')
            data['x'],data['y']=free; s['characters'].append(data)
        log(s,'Ficha manual guardada: '+data['name']+'. Clase, dotes y modificadores requieren verificación; no es un pregenerado certificado.')
    elif kind=='request_check':
        host(me);c=char(s,b['character'],me)
        checks.modifier(c,b['checkKind'],b['key']);dc=checks.integer(b.get('dc'),0,1000)
        reason=str(b.get('reason','')).strip()
        if not reason or len(reason)>500:raise ValueError('Describe el motivo de la prueba en hasta 500 caracteres')
        if sum('check' in p for p in s['pending'])>=30:raise ValueError('Resuelve o cancela las pruebas pendientes antes de solicitar más')
        s['pending'].append({'reason':reason,'source':'Prueba solicitada por el anfitrión',
            'check':{'id':secrets.token_hex(12),'character':c['id'],'kind':b['checkKind'],'key':b['key'],'dc':dc}})
        log(s,c['name']+': prueba solicitada. '+reason)
    elif kind=='cancel_check':
        host(me);pending=next((p for p in s['pending'] if p.get('check') and p['check']['id']==b.get('request')),None)
        if pending is None:raise ValueError('Esta prueba ya no está pendiente')
        s['pending'].remove(pending);log(s,'Prueba cancelada: '+pending['reason'])
    elif kind=='check':
        pending=None
        if b.get('request'):
            pending=next((p for p in s['pending'] if p.get('check',{}).get('id')==b['request']),None)
            if pending is None:raise ValueError('Esta prueba ya fue resuelta o cancelada')
            spec=pending['check'];c=char(s,spec['character'],me);dc=spec['dc']
        else:
            c=char(s,b['character'],me);spec={'kind':b['checkKind'],'key':b['key']};dc=None
        checks.modifier(c,spec['kind'],spec['key'])  # Validate before generating any dice.
        if b.get('physical') is not None:host(me)
        raw=dice([20],b.get('physical'))[0];result=checks.resolve(c,spec['kind'],spec['key'],raw,dc)
        if pending:s['pending'].remove(pending)
        outcome='' if dc is None else f" contra CD {dc}: {'éxito' if result['success'] else 'fallo'}"
        if result['natural']:outcome+=' ('+result['natural']+')'
        reason=' · '+pending['reason'] if pending else ''
        log(s,f"{c['name']} · {result['name']}: d20 {raw} {result['modifier']:+} = {result['total']}{outcome}{reason}. {result['basis']}. Origen: {'físico' if b.get('physical') is not None else 'servidor'}. No aplica efectos ni coste de acción por sí sola.",check=result,refs=[{'book':'reglas','page':182 if spec['kind']=='save' else 87 if spec['kind']=='skill' else 17}])
    elif kind=='roll':
        n=int(b.get('n',1)); sides=int(b.get('sides',20)); mod=int(b.get('modifier',0))
        if not 1<=n<=30 or sides not in [2,3,4,6,8,10,12,20,100] or abs(mod)>1000: raise ValueError('Tirada inválida')
        raw=dice([sides]*n,b.get('physical')); total=sum(raw)+mod
        visibility=b.get('visibility','public')
        if visibility!='public': host(me)
        log(s,f"{b.get('label','Tirada')}: {n}d{sides} {raw} {mod:+} = {total}. Origen: {'físico' if b.get('physical') is not None else 'servidor'}. Modificador declarado: {b.get('source','manual')}",visibility=visibility)
    elif kind=='oracle':
        host(me); q=str(b['question']).strip(); key=q.casefold().strip('¿? .')
        if not key: raise ValueError('Escribe la pregunta')
        if key in s['facts']: raise ValueError('Esta pregunta ya está establecida. No se repite para forzar otro resultado.')
        if not b.get('uncertain'): raise ValueError('Confirma que es un hecho incierto y que Pathfinder no regula la resolución')
        raw=dice([10,8,6],b.get('physical')); total,result,matches=oracle(raw,b.get('probability','neutral'))
        groups={'Accesibilidad':['Fácil','Normal','Difícil'],'Calidad':['Mala','Normal','Buena'],'Cantidad':['Uno','Algunos','Muchos'],'Complejidad':['Simple','Media','Compleja'],'Dificultad':['Fácil','Media','Difícil'],'Disponibilidad':['Común','Estándar','Rara'],'Fuerza':['Débil','Promedio','Fuerte'],'Información':['Mala','Promedio','Buena'],'Peligrosidad':['Baja','Media','Alta'],'Pista':['Pobre','Promedio','Buena'],'Seguridad':['Débil','Promedio','Fuerte'],'Tamaño':['Pequeño','Mediano','Grande']}
        group=b.get('group','Sin detalle'); detail=groups.get(group,['Sin detalle']*3)[0 if raw[1]<=2 else 1 if raw[1]<=6 else 2] if total>=6 else None
        entry={'question':q,'raw':raw,'total':total,'result':result,'probability':b.get('probability','neutral'),'detail':detail,'group':group,'page':19,'scene':s['scene'],'interpretation':b.get('interpretation','Pendiente de interpretación'),'origin':'físico' if b.get('physical') is not None else 'servidor'}
        if matches: entry['event']=event(s,matches==3,b.get('eventPhysical'))
        s['facts'][key]={'answer':result,'interpretation':entry['interpretation']}; s['oracleLog'].append(entry)
        log(s,q+': '+result+' · d10/d8/d6 '+str(raw)+' → '+str(total)+' · TREY PDF p.19'+(' · Evento inesperado; ver diario' if matches else ''))
    elif kind=='npc':
        host(me); raw=dice([10,8,6],b.get('physical')); total,_,_=oracle(raw,b.get('probability','neutral'))
        behaviors=['Violento','Agresivo','Irritado','Distante','Indiferente','Indiferente','Educado','Agradable','Bondadoso','Cariñoso']
        personalities=['Tímido, retraído, tranquilo, cuidadoso','Social, extrovertido, alegre, entusiasta','Antisocial, quejica, insatisfecho, deprimido','Intimidante, manipulador, dominante, opresivo','Enojado, apasionado, celoso, competitivo','Paranoico, suspicaz, asustado, emocional','Seguro, tranquilo, solidario, estable','Apático, lánguido, sin interés, sin emociones']
        far=b.get('farthest')
        if far not in ['d10','d8','d6',None]: raise ValueError('Dado más alejado inválido')
        capacity={'d10':'Más capaz','d8':'Igual de capaz','d6':'Menos capaz'}.get(far,'Sin determinar: indica la posición física de los dados; no se deduce de sus valores')
        text=f"{b['name']}: {behaviors[total-1]}; {personalities[raw[1]-1]}; {capacity}. Dados {raw}; comportamiento ajustado {total}. TREY PDF pp.26–27. No sustituye Diplomacia de Pathfinder."
        s['allies'].append(text);log(s,text,refs=[{'book':'trey','page':27}])
    elif kind=='voluntary':
        host(me)
        if s['voluntaryScene']==s['scene']: raise ValueError('Solo un evento voluntario por escena, TREY p.32')
        exceptional=bool(b.get('exceptional')); event(s,exceptional,b.get('physical'),s['scene']*(2 if exceptional else 1)); s['voluntaryScene']=s['scene']; log(s,'Evento voluntario registrado · TREY p.32')
    elif kind=='spend':
        host(me)
        costs={'repetir habilidad':2,'éxito habilidad':4,'acción adicional':2,'éxito combate':4,'evitar muerte':6,'invertir oráculo':6,'reducir excepcional':4,'grado detalle':4,'evento positivo':6,'reducir evento':4,'grado comportamiento':2,'grado capacidad':4,'objeto útil':2,'ayuda':6}
        benefit=b['benefit']; cost=costs[benefit]
        if not s['turned'] or s['tokens']<cost: raise ValueError('Requiere punto de giro y FH suficientes')
        if not b.get('consent') or not b.get('interpretation'): raise ValueError('Registra consentimiento e interpretación del beneficio')
        s['tokens']-=cost; s['pending'].append({'reason':benefit+': '+b['interpretation'],'source':'TREY p.34; adaptación a Pathfinder, aplicación manual pendiente'})
        log(s,f"Gasto de {cost} FH: {benefit}. Consenso registrado. {b['interpretation']}. Pendiente de aplicar con resolución asistida.")
    elif kind=='journal':
        host(me)
        for key in ['location','worldTime','goal','notes','secrets']:
            if key in b: s[key]=str(b[key])[:30000]
        for key in ['objectives','allies','enemies','unknowns']:
            if key in b: s[key]=[str(v)[:1000] for v in b[key]][:1000]
        log(s,'Diario actualizado')
    elif kind=='scene':
        host(me); s['scene']+=1; s['location']=str(b.get('location',s['location'])); log(s,'Comienza la escena '+str(s['scene']))
    elif kind=='bookmark':
        book=b['book']; page=int(b['page'])
        if book not in ['trey','reglas','bestiario'] or page<1: raise ValueError('Referencia inválida')
        s['bookmarks'].append({'book':book,'page':page,'label':str(b.get('label','Marcador'))[:100]})
    elif kind=='attack':
        result=combat.attack(s,b,me,dice)
        source=next(c for c in s['characters'] if c['id']==result['attacker'])
        target=next(c for c in s['characters'] if c['id']==result['target'])
        outcome='crítico confirmado' if result['critical'] else 'impacto' if result['hit'] else 'fallo'
        detail=(' Objetivo desprevenido.' if result['flatFooted'] else '')+(' Flanqueo +2.' if result['flanking'] else '')
        if result['confirmation'] is not None:detail+=f" Confirmación: d20 {result['confirmation']} {result['modifier']:+}."
        if source['hp']<0:detail+=f" {source['name']}: {result['attackerHp']} PG, {result['attackerStatus']}."
        log(s,f"{source['name']} ataca a {target['name']}: d20 {result['roll']} {result['modifier']:+} contra CA {result['ac']} → {outcome}. Daño {result['damage']} (dados {result['damageRolls']}); PG {result['targetHp']} ({result['status']}). Acción estándar gastada.{detail}",combat=result,refs=[{'book':'reglas','page':180},{'book':'reglas','page':185}])
    elif kind=='combat':
        host(me)
        if s['board']['active']: raise ValueError('Ya hay combate activo')
        if not s['characters']: raise ValueError('Añade participantes en la ficha')
        automatic=b.get('automateEnemies',False)
        if type(automatic)!=bool:raise ValueError('El control automático debe ser verdadero o falso')
        if automatic and not any(not c['enemy'] for c in s['characters']):raise ValueError('Añade al menos un personaje jugador')
        order=[{'id':c['id'],'roll':dice([20])[0],'modifier':c['initiative'],'dex':c['abilities'][1]} for c in s['characters']]
        order.sort(key=lambda v:(v['roll']+v['modifier'],v['modifier'],secrets.randbits(16)),reverse=True)
        s['board'].update(active=True,round=1,turn=0,order=order,spent={},acted=[],autoEnemies=automatic)
        s['board'].pop('autoPaused',None);begin_turn(s)
        log(s,'Iniciativa d20 + modificador declarado: '+str(order)+'. Empates: modificador total y después azar. Reglas básicas: Iniciativa, impresa p.178 / PDF p.179. Sorpresa: resolución excepcional. CA desprevenido automática en ataques básicos con perfil preparado.',refs=[{'book':'reglas','page':179}])
    elif kind=='endcombat':
        host(me); s['board']['active']=False;s['board'].pop('autoPaused',None)
        log(s,'Combate finalizado; negociación, retirada o conclusión registradas por la mesa')
    elif kind=='automation':
        host(me);board=s['board']
        if not board['active']:raise ValueError('No hay combate')
        if type(b.get('enabled'))!=bool:raise ValueError('El control automático debe ser verdadero o falso')
        if b['enabled'] and 'acted' not in board:raise ValueError('Reinicia este combate antiguo antes de activar la automatización')
        board['autoEnemies']=b['enabled'];board.pop('autoPaused',None)
        log(s,'Control de adversarios: '+('automático' if b['enabled'] else 'anfitrión'))
    elif kind=='turn':
        board=s['board']
        if not board['active']: raise ValueError('No hay combate')
        current=board['order'][board['turn']]['id']; char(s,current,me)
        advance_turn(s)
    elif kind=='terrain':
        host(me)
        x,y=int(b['x']),int(b['y']); t=b['terrain']
        if not 0<=x<20 or not 0<=y<20 or t not in ['wall','difficult','clear']: raise ValueError('Terreno inválido')
        if t=='wall' and any(c['x']==x and c['y']==y for c in s['characters']): raise ValueError('Hay una ficha en esa casilla')
        s['board']['terrain'][f'{x},{y}']=t; log(s,f'Terreno {t} en {x},{y}; adjudicación de escenario manual')
    elif kind=='move':
        c=char(s,b['character'],me); board=s['board']; path=b['path']
        if c['hp']<0:raise ValueError('Un personaje inconsciente o muerto no puede moverse')
        if not 1<=len(path)<=100: raise ValueError('Recorrido inválido')
        if not b.get('acknowledge'): raise ValueError('Confirma las consecuencias y las reglas pendientes')
        if board['active'] and board['order'][board['turn']]['id']!=c['id']: raise ValueError('No es tu turno')
        x,y=c['x'],c['y']; diagonals=0; cost=0
        for point in path:
            nx,ny=map(int,point); dx,dy=abs(nx-x),abs(ny-y)
            if not 0<=nx<20 or not 0<=ny<20 or max(dx,dy)!=1: raise ValueError('Recorrido discontinuo o fuera del tablero')
            tile=board['terrain'].get(f'{nx},{ny}','clear')
            if tile=='wall': raise ValueError('El recorrido atraviesa un obstáculo')
            if dx and dy:
                if board['terrain'].get(f'{x},{ny}')=='wall' or board['terrain'].get(f'{nx},{y}')=='wall': raise ValueError('No puedes cortar la esquina de un muro')
                diagonals+=1; step=2 if diagonals%2==0 else 1
            else: step=1
            if any(o['id']!=c['id'] and o['x']==nx and o['y']==ny for o in s['characters']): raise ValueError('Casilla ocupada; cruce de aliados requiere resolución manual')
            cost+=(3 if dx and dy else 2) if tile=='difficult' else step; x,y=nx,ny
        if board['active']:
            used=board['spent'].get(c['id'],{})
            if c['hp']==0 and used.get('standard'):raise ValueError('Incapacitado: solo una acción estándar o de movimiento')
            if used.get('move'): raise ValueError('Acción de movimiento gastada. Más movimiento requiere resolución asistida')
            if cost>c['speed']: raise ValueError('El recorrido supera una acción de movimiento')
            used['move']=True; board['spent'][c['id']]=used
        c.update(x=x,y=y); log(s,f"{c['name']} se mueve {cost*5} pies a ({x},{y}). Recorrido {path}. Diagonales 5/10 pies; diagonal difícil 15 pies. Reglas básicas, Movimiento, posición y distancia: impresa p.193 / PDF p.194. AdO, alcance y visibilidad especiales se resuelven aparte.",refs=[{'book':'reglas','page':194}])
    elif kind=='manual':
        host(me); reason=str(b['reason']).strip(); resolution=str(b['resolution']).strip()
        if not reason or not resolution: raise ValueError('Indica motivo y resolución')
        cid=b.get('character')
        if cid:
            c=char(s,cid,me)
            cost=b.get('actionCost','none'); board=s['board']
            if cost not in ['none','standard','move','full','swift','immediate']: raise ValueError('Tipo de acción inválido')
            if cost!='none':
                if not board['active']: raise ValueError('No hay combate activo')
                if cost!='immediate' and board['order'][board['turn']]['id']!=cid: raise ValueError('No es el turno del personaje; declara fuera de turno y resuelve manualmente cuando corresponda')
                spent=board['spent'].get(cid,{})
                outside=board['order'][board['turn']]['id']!=cid
                needs=['standard','move'] if cost=='full' else ['swiftDebt'] if cost=='immediate' and outside else ['swift'] if cost=='immediate' else [cost]
                if any(spent.get(v) for v in needs): raise ValueError('La acción necesaria ya está gastada')
                for v in needs: spent[v]=True
                board['spent'][cid]=spent
            if 'hpDelta' in b:
                delta=max(-10000,min(10000,int(b['hpDelta'])))
                c['hp']+=delta
                if delta:c['stable']=delta>0
            if 'conditions' in b: c['conditions']=str(b['conditions'])
            if 'resources' in b: c['resources']=str(b['resources'])
        log(s,'RESOLUCIÓN MANUAL ASISTIDA · '+reason+' · '+resolution+' · Coste de acción: '+str(b.get('actionCost','none'))+' · Referencia: '+str(b.get('reference','Sin verificar; criterio provisional')))
        if b.get('pendingIndex') is not None: s['pending'].pop(int(b['pendingIndex']))
    else: raise ValueError('Acción no implementada; usa resolución manual asistida')
    if kind in ('combat','turn','automation'):run_automatic_turns(s)
