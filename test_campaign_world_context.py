import copy
import io
import json
import unittest
from unittest.mock import patch
import campaign_world as world
import claude_dm
import director_prompt
import legacy_director_attempt as legacy
import test_compact_memory as authored
from test_rule_pack_world import npc,place,relationship


class CampaignWorldContextTests(unittest.TestCase):
    def setUp(self):
        fixture=authored.CompactAuthoredMemoryTests();fixture.setUp();self.state=fixture.state
        self.state['campaignWorld']=world.apply(world.empty(),{'npcs':[npc(),npc('oculta',name='SECRET-NAME',known=False,public='')],'places':[place()],'relationships':[]})
        self.state['messages'].append({'speaker':'Aria','owner':'host','kind':'dialogue','text':'Pregunto por Arda.'})
        self.reply={'narration':'Arda te escucha.','proposals':[],
            'memory':{'summary':'La conversación sigue abierta.','preparation':'PRIVATE-PREPARATION'},
            'worldUpdates':{'npcs':[npc(public='Arda escucha junto al archivo.')],'places':[],'relationships':[relationship()]}}

    def raw(self,value):return json.dumps({'stop_reason':'end_turn','content':[{'type':'text','text':json.dumps(value)}]}).encode()

    def test_private_world_is_only_in_director_knowledge_never_rules_or_public_state(self):
        before=copy.deepcopy(self.state);context=claude_dm.build_context(self.state,'Saludo',[])
        self.assertNotIn('campaignWorld',context['state']);self.assertNotIn('PRIVATE',str(context['state']))
        self.assertIn('SECRET-NAME',str(context['directorKnowledge']['campaignWorld']))
        rules=claude_dm.build_context(self.state,'Regla',[],rules=True)
        self.assertNotIn('campaignWorld',str(rules));self.assertEqual(self.state,before)

    def test_new_schema_is_gated_and_legacy_start_contract_is_preserved(self):
        self.assertIn('worldUpdates',claude_dm.response_schema(self.state)['properties'])
        self.assertIn('worldUpdates',claude_dm.response_schema(self.state,starting=True)['required'])
        self.assertNotIn('worldUpdates',claude_dm.response_schema(self.state,rules=True)['properties'])
        old=copy.deepcopy(self.state);old.pop('campaignWorld')
        self.assertNotIn('worldUpdates',claude_dm.response_schema(old,starting=True)['properties'])
        self.assertNotIn(director_prompt.WORLD,director_prompt.system_prompt())

    def test_reply_and_durable_capture_replay_without_provider_or_state_mutation(self):
        before=copy.deepcopy(self.state);parsed=claude_dm.parse_response(self.state,self.raw(self.reply))
        self.assertEqual(parsed['worldUpdates'],self.reply['worldUpdates']);self.assertEqual(self.state,before)
        prepared=legacy.prepare(self.state,'Saludo',[])
        with patch.object(claude_dm,'ai_reply',side_effect=AssertionError('Replay called provider')):
            restored=legacy.restore(prepared,{'kind':'report','value':self.reply,'latencyMs':0},legacy.SCHEME)
        self.assertEqual(restored['worldUpdates'],self.reply['worldUpdates']);self.assertEqual(self.state,before)

    def test_updates_cannot_advance_checks_actions_combat_or_unenabled_campaigns(self):
        baseline=copy.deepcopy(self.state)
        for case in ('old','rules','combat','pending','ooc','investigation','mechanics'):
            self.state=copy.deepcopy(baseline);reply=copy.deepcopy(self.reply)
            if case=='old':self.state.pop('campaignWorld')
            elif case=='rules':reply.pop('memory')
            elif case=='combat':self.state['board']['active']=True
            elif case=='pending':self.state['pending']=[{'reason':'Pendiente'}]
            elif case=='ooc':self.state['messages'][-1]['kind']='ooc'
            elif case=='investigation':reply['investigation']={'requested':True,'character':self.state['characters'][0]['id'],'opportunity':'registro'}
            elif case=='mechanics':reply['worldUpdates']['npcs'][0]['hp']=10
            with self.subTest(case=case),self.assertRaisesRegex(ValueError,'director:world-memory'):
                claude_dm.parse_response(self.state,self.raw(reply),rules=case=='rules')

    def test_explicit_no_investigation_does_not_block_independent_notes(self):
        value={**self.reply,'investigation':{'requested':False,'character':'','opportunity':''}}
        parsed=claude_dm.parse_response(self.state,self.raw(value))
        self.assertNotIn('investigation',parsed);self.assertEqual(parsed['worldUpdates'],self.reply['worldUpdates'])

    def test_actual_provider_request_and_capture_keep_private_world_separate(self):
        sent=[]
        def response(request,**options):
            sent.append(json.loads(request.data));return io.BytesIO(self.raw(self.reply))
        with patch.dict('os.environ',{'ANTHROPIC_API_KEY':'fixture-never-sent'}),patch('urllib.request.urlopen',side_effect=response):
            self.assertEqual(claude_dm.ai_reply(self.state,'Saludo',[])['worldUpdates'],self.reply['worldUpdates'])
        context=json.loads(sent[0]['messages'][0]['content'])
        self.assertNotIn('campaignWorld',context['state']);self.assertIn('SECRET-NAME',str(context['directorKnowledge']))
        self.assertIn(director_prompt.WORLD,sent[0]['system']);self.assertIn('worldUpdates',sent[0]['output_config']['format']['schema']['properties'])
        before=legacy.prepare(self.state,'Saludo',[]);changed=copy.deepcopy(self.state);changed['campaignWorld']['npcs'][0]['private']='Otro motivo privado.'
        after=legacy.prepare(changed,'Saludo',[])
        self.assertNotEqual(before['sha256'],after['sha256']);self.assertFalse(legacy.compatible_input(before['captureRequest'],after['captureRequest']))
