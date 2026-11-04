"""Narrative persistence, boundaries and provider contract; no real inference."""
import copy
import io
import json
import unittest
from unittest.mock import patch
import adventure
import claude_dm
from engine import initial_state,apply_action
from test_character_builder import choices

HOST={'id':'host','name':'Ana','host':True}


def memory(**changes):
    return {'summary':'Aria llega al molino; la puerta sigue cerrada.','location':'El molino',
            'goal':'Investigar las luces','objectives':['Hablar con la molinera'],
            'preparation':'La molinera oculta una llave bajo la escalera.',**changes}


def reply(**changes):
    return {'narration':'Una luz brilla bajo la puerta del molino.','proposals':[],
            'memory':memory(),**changes}


class AdventureTests(unittest.TestCase):
    def state(self):
        state=initial_state({})
        apply_action(state,{'type':'create_character','choices':choices()},HOST)
        return state

    def test_start_requires_host_ready_character_no_combat_and_short_premise(self):
        state=self.state();self.assertEqual(adventure.validate_start(state,{'premise':'Un misterio'},HOST),'Un misterio')
        for invalid in ['',True,{},'x'*2001]:
            with self.assertRaises(ValueError):adventure.validate_start(state,{'premise':invalid},HOST)
        with self.assertRaises(PermissionError):adventure.validate_start(state,{},dict(HOST,host=False))
        for mutate in [lambda s:s.update(characters=[]),lambda s:s['characters'][0].update(enemy=True),
                       lambda s:s['characters'][0]['creation'].update(manualOverride=True),
                       lambda s:s['characters'][0].update(hp=0),lambda s:s['board'].update(active=True),
                       lambda s:s.update(adventure={'revision':1})]:
            modified=copy.deepcopy(state);mutate(modified)
            with self.assertRaises(ValueError):adventure.validate_start(modified,{},HOST)

    def test_memory_changes_only_narrative_fields_and_keeps_manual_preparation(self):
        state=self.state();state['directorNotes']='Preparación del anfitrión';before=copy.deepcopy(state)
        adventure.apply_memory(state,memory(),starting=True)
        changed={k for k in state if state[k]!=before.get(k)}
        self.assertEqual(changed,{'adventure','directorMemory','location','goal','objectives'})
        adventure.apply_memory(state,memory(summary='La molinera saluda a Aria.'))
        self.assertEqual(state['adventure']['revision'],2)
        self.assertEqual(state['characters'],before['characters'])
        self.assertEqual(state['directorNotes'],before['directorNotes'])

    def test_malformed_or_mechanical_fields_rejected_without_mutation(self):
        for invalid in [None,{},memory(hp=100),memory(summary=''),memory(preparation='x'*8001),
                        memory(objectives=['A']*2),memory(objectives=[1]),memory(objectives=['A']*13)]:
            state=self.state();before=copy.deepcopy(state)
            with self.assertRaises(ValueError):adventure.apply_memory(state,invalid,starting=True)
            self.assertEqual(state,before)
        with self.assertRaises(ValueError):adventure.apply_memory(self.state(),memory())

    def test_combat_cannot_be_relocated_by_narrative_memory(self):
        state=self.state();adventure.apply_memory(state,memory(),starting=True)
        state['board']['active']=True;before=copy.deepcopy(state)
        with self.assertRaises(ValueError):adventure.apply_memory(state,memory(location='Otra ciudad'))
        self.assertEqual(state,before)

    def test_provider_receives_private_memory_only_in_narration_and_validates_output(self):
        state=self.state();adventure.apply_memory(state,memory(),starting=True)
        context=claude_dm.build_context(state,'Saludo',[])
        self.assertNotIn('directorMemory',context['state'])
        self.assertEqual(context['directorKnowledge']['memory'],memory()['preparation'])
        rules=claude_dm.build_context(state,'Consulta',[],rules=True)
        self.assertNotIn(memory()['preparation'],json.dumps(rules))
        for output,rules,valid in [(reply(),False,True),(reply(memory=memory(hp=10)),False,False),(reply(),True,False)]:
            response={'stop_reason':'end_turn','content':[{'type':'text','text':json.dumps(output)}]}
            with patch.dict('os.environ',{'ANTHROPIC_API_KEY':'test-only'}),patch('urllib.request.urlopen',return_value=io.BytesIO(json.dumps(response).encode())):
                if valid:self.assertEqual(claude_dm.ai_reply(state,'Saludo',[],rules=rules),output)
                else:
                    with self.assertRaises(ValueError):claude_dm.ai_reply(state,'Consulta',[],rules=rules)

    def test_continuation_requires_new_results_and_ownership(self):
        state=self.state();adventure.apply_memory(state,memory(),starting=True)
        with self.assertRaises(ValueError):adventure.continuation_request(state,HOST)
        cid=state['characters'][0]['id']
        state['messages'].append({'kind':'rules','text':'Resultado','check':{'character':cid}})
        self.assertIn('ya resueltas',adventure.continuation_request(state,HOST))
        state['messages'].append({'kind':'director','text':'Pausa fuera de personaje','ooc':True})
        self.assertIn('ya resueltas',adventure.continuation_request(state,HOST))
        with self.assertRaises(PermissionError):adventure.continuation_request(state,{'id':'other','host':False})
        state['messages'].append({'kind':'director','text':'Narrado'})
        with self.assertRaises(ValueError):adventure.continuation_request(state,HOST)

    def test_provider_reports_safe_failure_stage_and_uses_generation_headroom(self):
        import adventure_modules
        state=self.state()
        response={'stop_reason':'max_tokens','content':[{'type':'text','text':'PRIVATE-PARTIAL-PAYLOAD'}]}
        with patch.dict('os.environ',{'ANTHROPIC_API_KEY':'test-only'}),patch('urllib.request.urlopen',return_value=io.BytesIO(json.dumps(response).encode())) as provider:
            with self.assertRaisesRegex(ValueError,'director:output_limit') as error:
                claude_dm.ai_reply(state,'Crear',[],starting=True)
            self.assertNotIn('PRIVATE-PARTIAL-PAYLOAD',str(error.exception))
            self.assertEqual(json.loads(provider.call_args.args[0].data)['max_tokens'],4500)
        module=adventure_modules.builtin('la-carta-perdida');module['scope']='unsupported';module['preparation']='PRIVATE-MODULE-PREPARATION'
        result=reply(adventureModule=module)
        response={'stop_reason':'end_turn','content':[{'type':'text','text':json.dumps(result)}]}
        with patch.dict('os.environ',{'ANTHROPIC_API_KEY':'test-only'}),patch('urllib.request.urlopen',return_value=io.BytesIO(json.dumps(response).encode())):
            with self.assertRaisesRegex(ValueError,'director:module') as error:
                claude_dm.ai_reply(state,'Crear',[],starting=True)
            self.assertNotIn('PRIVATE-MODULE-PREPARATION',str(error.exception))

    def test_opening_schema_cannot_request_player_actions_and_requires_module(self):
        state=self.state();schema=claude_dm.response_schema(state,starting=True)
        self.assertNotIn('investigation',schema['properties']);self.assertNotIn('checks',schema['properties'])
        self.assertIn('adventureModule',schema['required']);self.assertIn('memory',schema['required'])
        rules=claude_dm.response_schema(state,rules=True)
        self.assertEqual(set(rules['properties']),{'narration','proposals'})
        self.assertNotIn('adventureModule',claude_dm.SCHEMA['required'])
