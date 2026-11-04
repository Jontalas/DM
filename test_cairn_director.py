import copy
import io
import json
import os
import unittest
from unittest.mock import patch
from systems import cairn_director as director,cairn_narrative as narrative,cairn_adventure as adventure,cairn_engine as engine
from test_cairn_adventure import scene

ME={'id':'player','name':'Ana','host':True}


def reply(**changes):
    return {'narration':'Lúa explica las dos rutas y espera tu decisión.','limitation':'',
        'memory':{'summary':'El personaje pregunta por el archivo. El cruce no está confirmado.','preparation':'Lúa conoce las rutas. Espera la decisión del personaje.'},
        'intent':{'type':'none','route':''},**changes}


class CairnDirectorTests(unittest.TestCase):
    def test_context_has_only_needed_actor_data_and_keeps_director_material_separate(self):
        state=scene();actor=state['characters'][0]
        actor['creation']['privateNote']='HIDDEN-CREATION'
        state['creationDrafts']['someone']={'note':'HIDDEN-OTHER-DRAFT'}
        state['importedDrafts']['archived']={'note':'HIDDEN-ARCHIVE'}
        state['narrative']['preparation']='PRIVATE-DIRECTOR-MEMORY'
        state['messages'].append({'kind':'private','speaker':'Someone','character':'someone','text':'HIDDEN-NOTE'})
        context=director.context(state,actor,'¿Qué caminos hay?','dialogue','talk')
        serialized=json.dumps(context)
        for private in ('HIDDEN-CREATION','HIDDEN-OTHER-DRAFT','HIDDEN-ARCHIVE','HIDDEN-NOTE'):self.assertNotIn(private,serialized)
        self.assertEqual(context['directorKnowledge']['memory'],'PRIVATE-DIRECTOR-MEMORY')
        self.assertNotIn('PRIVATE-DIRECTOR-MEMORY',json.dumps(context['scene']))
        self.assertNotIn('creation',context['character']);self.assertIsNotNone(context['declaration'])

    def test_provider_payload_is_native_bounded_and_usage_is_transport_metadata(self):
        state=scene();actor=state['characters'][0]
        output={'stop_reason':'end_turn','content':[{'type':'text','text':json.dumps(reply(),ensure_ascii=False)}],
            'usage':{'input_tokens':123,'output_tokens':64}}
        with patch.dict(os.environ,{'ANTHROPIC_API_KEY':'fake-cairn-test-key'}),patch.object(director.urllib.request,'urlopen',return_value=io.BytesIO(json.dumps(output).encode('utf-8'))) as call:
            result=director.ai_reply(state,actor,'¿Qué caminos hay?')
        payload=json.loads(call.call_args.args[0].data)
        self.assertEqual(payload['max_tokens'],1400)
        self.assertNotIn('checks',payload['output_config']['format']['schema']['properties'])
        self.assertEqual(payload['output_config']['format']['schema']['properties']['intent']['properties']['type']['enum'],['none'])
        self.assertEqual(result['_usage']['inputTokens'],123);self.assertEqual(result['_usage']['outputTokens'],64)
        self.assertNotIn('fake-cairn-test-key',json.dumps(payload));self.assertNotIn('Pathfinder 1e',json.dumps(payload['messages']))

    def test_dialogue_and_continuation_cannot_propose_player_actions_or_modify_stats(self):
        state=scene();actor=state['characters'][0]
        for invalid in [reply(intent={'type':'choose_route','route':'pasarela'}),reply(abilities={'DEX':18}),
                reply(memory={'summary':'Texto','preparation':'Privado','hp':100})]:
            with self.assertRaises(ValueError):director.validate_reply(invalid,state,actor,'talk','dialogue')
        with self.assertRaises(ValueError):director.validate_reply(reply(intent={'type':'choose_route','route':'sendero'}),state,actor,'continue','continue')

    def test_declared_action_can_queue_supported_route_without_finishing_or_rolling(self):
        state=scene();before=copy.deepcopy(state)
        response=reply(intent={'type':'choose_route','route':'pasarela'})
        with patch.object(director,'ai_reply',return_value=response) as provider,patch.object(adventure.secrets,'randbelow',side_effect=AssertionError('Narration rolled')):
            changed=narrative.apply(state,{'type':'talk','character':'pc','kind':'action','text':'Cruzo por la pasarela húmeda.'},ME)
        self.assertEqual(provider.call_count,1);self.assertIsNotNone(changed['adventure']['pending'])
        self.assertFalse(changed['adventure']['completed']);self.assertEqual(changed['characters'],before['characters'])
        self.assertEqual(state,before)
        kinds=[m['kind'] for m in changed['messages'][-3:]];self.assertEqual(kinds,['action','director','rules'])
        self.assertEqual(changed['narrative']['revision'],1);engine.validate_restored(changed)

    def test_continue_uses_real_consequence_and_cannot_repeat_without_new_events(self):
        state=adventure.apply(scene(),{'type':'choose_route','route':'sendero'},ME)
        with patch.object(director,'ai_reply',return_value=reply()) as provider:
            changed=narrative.apply(state,{'type':'continue_cairn_adventure'},ME)
            with self.assertRaises(ValueError):narrative.apply(changed,{'type':'continue_cairn_adventure'},ME)
        self.assertEqual(provider.call_count,1);self.assertEqual(changed['narrative']['eventsSeen'],1)
        self.assertEqual(changed['characters'],state['characters']);self.assertEqual(changed['adventure'],state['adventure'])
        self.assertEqual(provider.call_args.args[4],'continue');engine.validate_restored(changed)

    def test_permissions_pending_ooc_and_provider_failure_prevent_unwanted_inference_or_partial_state(self):
        state=scene();before=copy.deepcopy(state)
        with patch.object(director,'ai_reply',side_effect=AssertionError('Precondition called AI')) as provider:
            with self.assertRaises(PermissionError):narrative.apply(state,{'type':'talk','character':'pc','text':'Hola'},{'id':'other','name':'Other','host':True})
            with self.assertRaises(ValueError):narrative.apply(state,{'type':'talk','character':'pc','kind':'private','text':'PRIVATE'},ME)
            ooc=narrative.apply(state,{'type':'talk','kind':'ooc','text':'Texto Ã± literal'},ME)
            provider.assert_not_called()
        self.assertEqual(ooc['messages'][-1]['text'],'Texto Ã± literal');self.assertEqual(ooc['narrative'],state['narrative'])
        with patch.object(director,'ai_reply',side_effect=ValueError('Provider failed')):
            with self.assertRaises(ValueError):narrative.apply(state,{'type':'talk','character':'pc','text':'Hola'},ME)
        self.assertEqual(state,before)

    def test_private_memory_is_not_public_and_response_usage_only_counts_committed_measurements(self):
        state=scene();response=reply(_usage={'inputTokens':12,'outputTokens':4,'latencyMs':20})
        with patch.object(director,'ai_reply',return_value=response):changed=narrative.apply(state,{'type':'talk','character':'pc','text':'Hola'},ME)
        self.assertEqual(changed['narrative']['usage'],{'responses':1,'measuredResponses':1,'inputTokens':12,'outputTokens':4,'latencyMs':20})
        view=engine.public_view(changed,ME)
        self.assertNotIn('narrative',view);self.assertEqual(view['narrativeView']['revision'],1)
        self.assertNotIn(response['memory']['preparation'],json.dumps(view))
        restored=engine.import_campaign(changed,{'id':'new-host','host':True})
        self.assertEqual(restored['narrative'],changed['narrative'])
