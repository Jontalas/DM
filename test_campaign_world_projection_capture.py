import copy
import io
import json
import unittest
from unittest.mock import patch
import claude_dm
import campaign_world_context as selection
import legacy_director_attempt as legacy
import test_compact_memory as authored
from test_campaign_world_context_selection import full_world


class WorldProjectionCaptureTests(unittest.TestCase):
    def setUp(self):
        fixture=authored.CompactAuthoredMemoryTests();fixture.setUp();self.state=fixture.state
        self.state['campaignWorld']=full_world();self.text='Pregunto a Persona 3.'
        self.state['messages'].append({'speaker':'Aria','owner':'host','kind':'dialogue','text':self.text})
        _,self.selected=selection.select(self.state['campaignWorld'],self.text,self.state['location'])
        person=copy.deepcopy(self.state['campaignWorld']['npcs'][3]);person['public']='Persona 3 recuerda el saludo.'
        self.reply={'narration':'La conversación continúa sin cambiar heridas ni pistas.','proposals':[],
            'memory':{'summary':'Continúa el saludo.','preparation':'La pista no cambia.'},
            'worldUpdates':{'npcs':[person],'places':[],'relationships':[]}}

    def report(self,value):return {'kind':'report','value':value,'latencyMs':0}
    def raw(self,value):return json.dumps({'stop_reason':'end_turn','content':[{'type':'text','text':json.dumps(value)}]}).encode()

    def test_request_projects_but_capture_and_legacy_key_preserve_complete_world(self):
        prepared=legacy.prepare(self.state,self.text,[])
        self.assertEqual(prepared['request']['context']['directorKnowledge']['campaignWorld']['format'],selection.FORMAT)
        self.assertEqual(prepared['captureRequest']['context']['directorKnowledge']['campaignWorld'],self.state['campaignWorld'])
        self.assertEqual(legacy.capture_input(prepared),prepared['captureRequest'])
        old=copy.deepcopy(prepared['captureRequest']);old['context'].pop('worldMemorySelection')
        self.assertEqual(legacy.request_sha(old),prepared['sha256']);self.assertTrue(legacy.compatible_input(old,prepared['captureRequest']))
        old_prepared={**prepared,'request':old,'captureRequest':copy.deepcopy(old)}
        self.assertEqual(legacy.capture_input(old_prepared),old)
        changed=copy.deepcopy(prepared['captureRequest']);omitted=next(item for item in changed['context']['directorKnowledge']['campaignWorld']['npcs'] if item['id'] not in self.selected['npcs']);omitted['private']='Changed omitted private fact.'
        self.assertFalse(legacy.compatible_input(old,changed))
        tampered=copy.deepcopy(prepared);tampered['request']['context']['directorKnowledge']['campaignWorld']['npcs'][0]['private']='MUTATED'
        with self.assertRaises(ValueError):legacy.capture_input(tampered)

    def test_current_projection_and_cold_complete_input_replay_without_provider(self):
        prepared=legacy.prepare(self.state,self.text,[])
        with patch.object(claude_dm,'ai_reply',side_effect=AssertionError('Projection replay called provider')):
            for candidate in (prepared,{**prepared,'request':copy.deepcopy(prepared['captureRequest'])}):
                result=legacy.restore(candidate,self.report(self.reply),legacy.SCHEME)
                self.assertEqual(result['worldUpdates'],self.reply['worldUpdates'])

    def test_old_full_input_keeps_its_original_permission_to_update_omitted_note(self):
        prepared=legacy.prepare(self.state,self.text,[]);old=copy.deepcopy(prepared['captureRequest']);old['context'].pop('worldMemorySelection')
        omitted=next(item for item in self.state['campaignWorld']['npcs'] if item['id'] not in self.selected['npcs'])
        reply={**self.reply,'worldUpdates':{'npcs':[omitted],'places':[],'relationships':[]}}
        with self.assertRaisesRegex(ValueError,'director:world-memory'):legacy.restore(prepared,self.report(reply),legacy.SCHEME)
        result=legacy.restore({**prepared,'request':old},self.report(reply),legacy.SCHEME)
        self.assertEqual(result['worldUpdates'],reply['worldUpdates'])

    def test_actual_sdk_uses_projection_and_checks_the_notes_it_really_loaded(self):
        sent=[]
        def response(request,**options):sent.append(json.loads(request.data));return io.BytesIO(self.raw(self.reply))
        with patch.dict('os.environ',{'ANTHROPIC_API_KEY':'fixture-never-sent'}),patch('urllib.request.urlopen',side_effect=response):
            self.assertEqual(claude_dm.ai_reply(self.state,self.text,[])['worldUpdates'],self.reply['worldUpdates'])
        context=json.loads(sent[0]['messages'][0]['content']);self.assertEqual(context['worldMemorySelection'],self.selected)
        self.assertEqual(context['directorKnowledge']['campaignWorld']['format'],selection.FORMAT)
        self.assertNotIn('campaignWorld',context['state']);self.assertIn('PRIVATE 3',str(context['directorKnowledge']))
        omitted=next(item for item in self.state['campaignWorld']['npcs'] if item['id'] not in self.selected['npcs'])
        self.assertNotIn(omitted['private'],str(context));self.assertIn(omitted['name'],str(context['directorKnowledge']['campaignWorld']['identities']))
