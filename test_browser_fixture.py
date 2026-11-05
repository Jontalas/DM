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
        def fixture_prepare(prepared):
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
        from test_adventure import reply,memory
        def fixture_reply(state,text,refs,**options):
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
        server.ai_reply=fixture_reply
    from test_reader_support import fixture_reader
    server.READER=fixture_reader()
    # Predictable dice only inside this explicitly isolated test process.
    engine.secrets.randbelow=lambda sides:0 if os.environ.get('TEST_CAIRN_FIXTURE')=='1' else min(11,sides-1)
    http=create_server(application,host='127.0.0.1',port=0,threads=4)
    print('http://127.0.0.1:'+str(http.effective_port),flush=True)
    http.run()


if __name__=='__main__':main()
