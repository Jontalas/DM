"""Servidor desechable SOLO para Playwright, sin credenciales ni servicios remotos."""
import os
import json
import engine
import server
from test_support import TestStore
from wsgi import application


def main():
    from waitress.server import create_server
    os.environ.pop('ANTHROPIC_API_KEY',None)
    os.environ.pop('FIREBASE_STORAGE_BUCKET',None)
    server.STORE=TestStore()
    if os.environ.get('TEST_RULE_PACK_FIXTURE')=='1':
        import rulesets
        rulesets.SYSTEMS['rule-pack']={'id':'rule-pack','name':'Paquete de reglas (test only)','status':'experimental'}
        import rule_pack_authoring as authoring
        import test_rule_pack_authoring as authoring_fixture
        os.environ['ANTHROPIC_API_KEY']='fixture-only-never-sent'
        def fixture_prepare(prepared,response_observer=None):
            if prepared['request']['scope']=='TEST_UNSUPPORTED':
                return authoring.validate_reply(prepared,{'status':'unsupported','packageJson':'','examples':[],
                    'issues':[{'kind':'unsupported','message':'La operación de esta prueba no está disponible en el motor.',
                        'sources':[prepared['sources'][0]['id']]}]})
            answer=authoring_fixture.reply(prepared)
            if prepared['request']['scope']=='TEST_DICE_BLOCK':
                document=json.loads(answer['packageJson']);document['triggers']={}
                document['coverage']={'implemented':['Recurso y prueba de dos dados'],'pending':['Agotamiento automático']}
                answer['packageJson']=json.dumps(document);answer['examples']=answer['examples'][:1]
            report=authoring.validate_reply(prepared,answer)
            report['usage']={'inputTokens':123,'outputTokens':456,'latencyMs':1}
            return report
        authoring.propose=fixture_prepare
        import rule_pack_director as pack_director
        from test_rule_pack_narrative import reply as pack_reply
        def fixture_pack_director(prepared,response_observer=None):
            request=prepared['request'];action='';changes={}
            if request['operation']=='start':
                changes['objectiveUpdates']=[{'id':'marca','title':'Investigar la marca del farol','detail':'Comprobar la marca que ha señalado Arda.','known':True,'private':'PRIVATE-OBJECTIVE: la marca procede del archivo.'},
                    {'id':'secreto','title':'PRIVATE-OBJECTIVE-TITLE','detail':'Una oportunidad todavía desconocida.','known':False,'private':'No revelar.'}]
                changes['placeUpdates']=[{'id':'archivo','name':'Archivo <antiguo>','known':True,'public':'Un edificio de piedra junto a la plaza.','private':'PRIVATE-WORLD: tiene una cámara sellada.'},
                    {'id':'camara','name':'PRIVATE-WORLD-NAME','known':False,'public':'','private':'Todavía no descubierta.'}]
                changes['relationshipUpdates']=[{'id':'arda-archivo','from':'npc:arda','to':'place:archivo','known':True,'public':'Arda custodia este archivo.','private':'PRIVATE-WORLD: conoce otra entrada.'},
                    {'id':'archivo-camara','from':'place:archivo','to':'place:camara','known':False,'public':'','private':'Existe un pasadizo.'}]
                changes['npcUpdates']=[{'id':'arda','name':'Arda <archivera>','known':True,'public':'Custodia el archivo junto al farol.','private':'PRIVATE-NPC: esconde una carta.'},
                    {'id':'sombra','name':'PRIVATE-NPC-NAME','known':False,'public':'','private':'Todavía no se ha presentado.'}]
                if request['contract'] in (pack_director.PLAN_CONTRACT,pack_director.ACTORS_PLAN_CONTRACT,pack_director.TARGET_OBJECTIVES_CONTRACT):changes.pop('objectiveUpdates')
                if request['contract'] in (pack_director.ACTORS_PLAN_CONTRACT,pack_director.TARGET_OBJECTIVES_CONTRACT):changes.pop('npcUpdates')
            if request['operation']=='talk' and request['kind']=='action':
                if 'TEST_UNSUPPORTED' in request['declaration']['text']:changes['limitation']='Este paquete no define esa mecánica.'
                elif request['allowedActions']:action=request['allowedActions'][0]
                if action and any(g['id']=='marca' and g['status']=='open' for g in request['directorKnowledge'].get('objectives',[])):
                    changes['objectiveCheck']={'objective':'marca','field':'success'}
                elif action:
                    goal=next((g for g in request['directorKnowledge'].get('objectives',[]) if g['known'] and g['status']=='open'),None)
                    if goal:changes['objectiveCheck']={'objective':goal['id'],'field':'success'}
            if request['operation']=='continue':changes['narration']='El resultado confirmado revela una marca junto al farol. Arda espera tu decisión.'
            if request['contract'] in (pack_director.TARGET_CONTRACT,pack_director.PUBLIC_TARGET_CONTRACT):changes['narration']='La resolución confirmada mantiene los datos compartidos de la otra ficha. La siguiente decisión es tuya.'
            answer=pack_reply(action,**changes);answer['usage']={'inputTokens':100,'outputTokens':200,'latencyMs':1}
            return pack_director.validate_reply(prepared,answer)
        pack_director.propose=fixture_pack_director
    if os.environ.get('TEST_CAIRN_FIXTURE')=='1':
        import rulesets
        rulesets.SYSTEMS['cairn-1e']={'id':'cairn-1e','name':'Cairn 1e (test only)','status':'experimental'}
        from systems import cairn_director,cairn_adventure
        def cairn_fixture_reply(state,actor,text,kind='dialogue',operation='talk'):
            view=cairn_adventure.public_view(state);intent={'type':'none','route':''}
            if kind=='action' and operation=='talk':
                for route in ('pasarela','sendero'):
                    if route in text.casefold():intent={'type':'choose_route','route':route}
            return {'narration':'Lúa conversa sin elegir por tu personaje. DEX confirmada: '+str(actor['abilities']['DEX'])+'.',
                'memory':{'summary':'La escena conserva sus resultados. DEX actual: '+str(actor['abilities']['DEX'])+'. Objetivo completado: '+str(view['completed'])+'.',
                    'preparation':'Continuidad privada de la prueba; los resultados pertenecen al motor.'},
                'intent':intent,'limitation':''}
        cairn_director.ai_reply=cairn_fixture_reply
    # Explicit isolated fixture only; never available in the production startup path.
    if os.environ.get('TEST_ADVENTURE_FIXTURE')=='1':
        os.environ['ANTHROPIC_API_KEY']='fixture-only-never-sent'
        from test_adventure import reply,memory
        def fixture_reply(state,text,refs,**options):
            if os.environ.get('TEST_DIRECTOR_NPC_WAIT')=='1' and not options.get('starting'):
                from director_prepared_decisions import declaration_available
                choices=declaration_available(state)
                if choices and text.casefold().strip().rstrip('.')=='espero junto a la guardiana a que despierte':return reply(narration='Permaneces junto a la guardiana sin dormir ni realizar otra acción.',preparedDecision={'action':'wait-for-guard'})
                if state.get('adventureModule') and text.casefold().strip().rstrip('.')=='examino el registro del patio':return reply(narration='Puedes examinar las anotaciones del registro.',investigation={'character':state['pfEncounter']['character'],'opportunity':'registro'})
                return reply(narration='Tú decides si quieres esperar junto a la guardiana.')
            if os.environ.get('TEST_DIRECTOR_TURN')=='1' and not options.get('starting'):
                from director_turn import declaration_available
                turn=declaration_available(state)
                if turn and text.casefold().strip().rstrip('.')=='termino mi turno':return reply(narration='Cedes el turno sin realizar otra acción.',turnEnd=turn)
                return reply(narration='El final de tu turno sigue siendo una decisión tuya.')
            if os.environ.get('TEST_DIRECTOR_MELEE')=='1' and not options.get('starting'):
                from director_combat import declaration_available
                attack=declaration_available(state)
                if attack and text.casefold().strip().rstrip('.')=='ataco a la guardiana con mi espada':
                    return reply(narration='La guardiana mantiene su espada preparada.',meleeAttack={'target':attack['targets'][0]})
                return reply(narration='Puedes revisar tu turno y decidir qué haces.',memory=memory(
                    summary='La situación se conserva.',location=state['location'],goal=state['goal'],objectives=state['objectives']))
            if os.environ.get('TEST_DIRECTOR_PREPARED_DECISIONS')=='1' and not options.get('starting'):
                from director_prepared_decisions import declaration_available
                choices=declaration_available(state)
                selected={'acepto la tregua':'accept-truce','duermo8h con mi armadura ligera':'sleep-in-light-armor',
                    'me quito la cota, duermo sin ella y vuelvo a equiparla':'sleep-after-removing-armor',
                    'empiezo a investigar el registro del patio':'investigate-courtyard'}.get(text.casefold().strip().rstrip('.'))
                if choices and selected in {a['id'] for a in choices['actions']}:
                    return reply(narration='El patio sigue tranquilo.',preparedDecision={'action':selected})
                return reply(narration='Aclara qué quieres hacer antes de continuar.',memory=memory(
                    summary='La situación se conserva.',location=state['location'],goal=state['goal'],objectives=state['objectives']))
            if os.environ.get('TEST_DIRECTOR_TRAVEL')=='1' and not options.get('starting'):
                from director_travel import declaration_available
                travel=declaration_available(state)
                targets={'voy al cobertizo':'cobertizo','vuelvo al patio':'patio'}
                chosen=targets.get(text.casefold().strip().rstrip('.'))
                if travel and chosen in {e['id'] for e in travel['exits']}:
                    return reply(narration='El camino está despejado.',routeTravel={'exit':chosen})
                return reply(narration='Puedes consultar las salidas y decidir dónde ir.',memory=memory(
                    summary='La ruta conserva su situación.',location=state['location'],goal=state['goal'],objectives=state['objectives']))
            if state.get('adventureModule') and state['adventureModule']['title']!='Fixture libre':
                module=state['adventureModule']
                from adventure_modules import public_view
                public=public_view(state)
                narration=module['description'] if options.get('starting') else public['conclusion'] if public['completed'] else 'La investigación continúa.'
                return reply(narration=narration,memory=memory(summary='Progreso de investigación conservado.',
                    location=module['location'],goal=module['goal'],objectives=[v['text'] for v in public['objectives'] if not v['completed']],
                    preparation='Continuidad de prueba, sin cambios a la aventura.'))
            if options.get('starting'):
                from adventure_modules import builtin
                module=builtin('la-carta-perdida');module['title']='Fixture libre';module['location']='El molino'
                return reply(adventureModule=module)
            if 'intento abrir' in text.casefold():
                actor=options['check_actors'][0]
                return reply(narration='La puerta se resiste; prueba de Fuerza pendiente.',
                             checks=[{'character':actor,'kind':'ability','key':'str','dc':10,'reason':'CD adjudicada de prueba'}])
            return reply(narration='La puerta se abre tras el resultado confirmado.',
                         memory=memory(summary='Aria abrió la puerta tras superar la prueba.'))
        if os.environ.get('TEST_COMPACT_MEMORY')=='1':
            full_fixture_reply=fixture_reply
            def compact_fixture_reply(state,text,refs,**options):
                result=full_fixture_reply(state,text,refs,**options)
                if state.get('adventureModule') and result.get('memory'):
                    result={**result,'memory':{k:result['memory'][k] for k in ('summary','preparation')}}
                return result
            server.ai_reply=compact_fixture_reply
        else:server.ai_reply=fixture_reply
    from test_reader_support import fixture_reader
    server.READER=fixture_reader()
    if os.environ.get('TEST_PF_ENCOUNTER_VERSION'):
        import pf_encounters
        fixture_version=os.environ['TEST_PF_ENCOUNTER_VERSION'];original_definition=pf_encounters.definition
        def fixture_definition(version=fixture_version):return original_definition(version)
        pf_encounters.definition=fixture_definition
    # Predictable dice only inside this explicitly isolated test process.
    engine.secrets.randbelow=lambda sides:0 if os.environ.get('TEST_CAIRN_FIXTURE')=='1' else min(11,sides-1)
    import game_randomness
    game_randomness.draw=lambda sides:1 if os.environ.get('TEST_CAIRN_FIXTURE')=='1' else min(12,sides)
    if os.environ.get('TEST_PF_NPC_WAIT_FIXTURE')=='1':
        wait_dice=iter([20,1,12,4,1,20,1,20,12])
        game_randomness.draw=lambda sides:next(wait_dice)
        game_randomness.initiative_tie=lambda:0
    if os.environ.get('TEST_PF_CEASEFIRE_FIXTURE')=='1':
        truce_dice=iter(([20,1,12,1,*([19,1,4]*4)] if os.environ.get('TEST_PF_TRUCE_NIGHT')=='1' else [20,1,12,1])*4)
        game_randomness.draw=lambda sides:next(truce_dice)
        game_randomness.initiative_tie=lambda:0
    if os.environ.get('TEST_PF_AWAKE_EXPLORATION_FIXTURE')=='1':
        awake_dice=iter([20,1,*([19,1,4]*4),12,4,20,20,20,20])
        game_randomness.draw=lambda sides:next(awake_dice)
        game_randomness.initiative_tie=lambda:0
    if os.environ.get('TEST_PF_NIGHT_FIXTURE')=='1':
        night_dice=iter([1,20,18,3,20,20,8,8]*2)
        game_randomness.draw=lambda sides:next(night_dice)
        game_randomness.initiative_tie=lambda:0
    if os.environ.get('TEST_PF_RECOVERY_FIXTURE')=='shared':
        game_randomness.draw=lambda sides:18 if sides==20 else 4 if sides==4 else min(12,sides)
    if os.environ.get('TEST_PF_RECOVERY_FIXTURE') in ('1','death'):
        # Explicit browser-only sequence: ordinary NPC hits for3HP, then a
        # source-backed stabilization/consciousness success. No production hook.
        recovery_d20=iter([18]*8+[20]+[1]*12) if os.environ['TEST_PF_RECOVERY_FIXTURE']=='death' else None
        game_randomness.draw=lambda sides:(next(recovery_d20) if recovery_d20 is not None else 18) if sides==20 else 3 if sides==4 else min(12,sides)
    http=create_server(application,host='127.0.0.1',port=0,threads=4)
    print('http://127.0.0.1:'+str(http.effective_port),flush=True)
    http.run()


if __name__=='__main__':main()
