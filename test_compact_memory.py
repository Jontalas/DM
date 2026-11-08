import copy
import io
import json
import unittest
from unittest.mock import patch
import adventure
import adventure_modules as modules
import claude_dm
import engine
import legacy_director_attempt as legacy
from test_adventure import memory
from test_character_builder import choices


class CompactAuthoredMemoryTests(unittest.TestCase):
    me={'id':'host','name':'Ana','host':True}

    def setUp(self):
        self.state=engine.initial_state({});engine.apply_action(self.state,{'type':'create_character','choices':choices()},self.me)
        modules.install(self.state,modules.builtin('la-carta-perdida'))
        adventure.apply_memory(self.state,memory(),starting=True)
        self.compact={'summary':'Aria pregunta por la carta; todavía no ha buscado.','preparation':'La escena conserva sus pistas pendientes.'}

    def test_authored_schema_requests_two_fields_and_free_schema_still_requests_five(self):
        before=copy.deepcopy(self.state)
        for starting in (False,True):
            schema=claude_dm.response_schema(self.state,starting=starting)
            self.assertEqual(set(schema['properties']['memory']['properties']),{'summary','preparation'})
            self.assertEqual(schema['properties']['memory']['required'],['summary','preparation'])
        free=engine.initial_state({});adventure.apply_memory(free,memory(),starting=True)
        self.assertEqual(set(claude_dm.response_schema(free)['properties']['memory']['properties']),set(adventure.MEMORY_SCHEMA['required']))
        self.assertEqual(self.state,before)

    def test_compact_memory_uses_authoritative_scene_facts_without_changing_mechanics(self):
        before=copy.deepcopy(self.state);value=copy.deepcopy(self.compact)
        expanded=adventure.memory_for_state(self.state,value)
        self.assertEqual(expanded['location'],self.state['adventureModule']['location'])
        self.assertEqual(expanded['goal'],self.state['adventureModule']['goal'])
        self.assertEqual(expanded['objectives'],self.state['objectives']);self.assertEqual(value,self.compact)
        adventure.apply_memory(self.state,value)
        for key in ('characters','board','worldTime','location','goal','objectives','moduleProgress'):self.assertEqual(self.state[key],before[key])
        self.assertEqual(self.state['adventure']['summary'],self.compact['summary'])
        self.assertEqual(self.state['directorMemory'],self.compact['preparation'])

    def test_invalid_compact_or_unknown_fields_are_atomic_and_free_world_cannot_use_it(self):
        for value in ({'summary':'','preparation':'x'},{'summary':'x','preparation':99},
            {**self.compact,'hp':99},{**self.compact,'location':'Otro lugar'}):
            before=copy.deepcopy(self.state)
            with self.assertRaises(ValueError):adventure.apply_memory(self.state,value)
            self.assertEqual(self.state,before)
        with self.assertRaises(ValueError):adventure.apply_memory(engine.initial_state({}),self.compact,starting=True)

    def test_raw_compact_capture_restores_locally_and_full_historical_memory_is_not_rewritten(self):
        prepared=legacy.prepare(self.state,'Pregunto por la carta',[])
        value={'narration':'La carta todavía no está a la vista.','proposals':[],'memory':self.compact}
        with patch.object(claude_dm,'ai_reply',side_effect=AssertionError('Memory restore called provider')):
            restored=legacy.restore(prepared,{'kind':'report','value':value,'latencyMs':0},legacy.SCHEME)
        self.assertEqual(restored['memory'],adventure.memory_for_state(self.state,self.compact))
        historical={**value,'memory':memory(location='Nombre narrativo histórico')}
        self.assertEqual(legacy.restore(prepared,{'kind':'report','value':historical,'latencyMs':0},legacy.SCHEME),historical)
        raw=json.dumps({'stop_reason':'end_turn','content':[{'type':'text','text':json.dumps(value)}]})
        self.assertEqual(claude_dm.parse_response(self.state,raw)['memory'],restored['memory'])

    def test_actual_provider_adapter_requests_only_compact_fields_and_expands_the_reply(self):
        value={'narration':'El registro sigue en el banco.','proposals':[],'memory':self.compact}
        raw=json.dumps({'stop_reason':'end_turn','content':[{'type':'text','text':json.dumps(value)}]}).encode()
        with patch.dict('os.environ',{'ANTHROPIC_API_KEY':'fixture-never-sent'}),patch('urllib.request.urlopen',return_value=io.BytesIO(raw)) as provider:
            result=claude_dm.ai_reply(self.state,'Pregunto por la carta',[])
        body=json.loads(provider.call_args.args[0].data)
        self.assertEqual(set(body['output_config']['format']['schema']['properties']['memory']['properties']),{'summary','preparation'})
        self.assertEqual(result['memory'],adventure.memory_for_state(self.state,self.compact))
