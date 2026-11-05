import base64
import copy
import io
import json
import os
import unittest
from unittest.mock import Mock,patch
import rule_pack_campaign as campaign
import rule_pack_director as director
import rule_preparation_attempt as attempts
from firebase_store import Conflict
from rule_pack_runtime import RulePackError
from test_rule_pack_runtime import document
from test_support import TestStore


def reply(action='',**changes):
    return {'narration':'Arda espera junto al farol. ¿Qué haces?', 'limitation':'',
        'summary':'Arda ofrece información junto al farol.','preparation':'PRIVATE-DIRECTOR: Arda oculta una carta.',
        'proposal':{'action':action,'inputsJson':'{}','reason':'Investigar el farol según tu declaración.' if action else ''},**changes}


class RulePackNarrativeTests(unittest.TestCase):
    def setUp(self):
        self.me={'id':'ana','name':'Ana','host':True,'campaign':'generic-story'}
        self.state=campaign.execute_action(campaign.initial_state({'goal':'Investigar un farol perdido'}),
            {'type':'install_rule_pack','package':document('live-lantern-example'),'policy':'provided-rules'},self.me)
        self.state=campaign.execute_action(self.state,{'type':'create_pack_sheet','name':'Aria'},self.me)
        self.character=self.state['characters'][0]['id']

    def apply(self,state,kind,answer=None,**data):
        return campaign.execute_action(state,{'type':kind,**data},self.me,narrative_call=Mock(return_value=answer or reply()))

    def start(self):return self.apply(self.state,'start_pack_adventure',character=self.character)

    def pending(self):return self.apply(self.start(),'talk_pack_adventure',reply('intentar'),character=self.character,text='Investigo el farol.',mode='action')

    def test_declaration_request_roll_and_continuation_preserve_mechanical_authority(self):
        initial=copy.deepcopy(self.state['characters'])
        with patch('rule_pack_runtime.secrets.randbelow',side_effect=AssertionError('Narration rolled dice')):
            pending=self.pending()
            self.assertEqual(pending['characters'],initial)
            self.assertEqual(pending['messages'][-2]['text'],'Investigo el farol.')
            request=pending['narrative']['pending']
            resolved=self.apply(pending,'resolve_pack_request',request=request['id'],physical={'dice':[3,4]})
            self.assertEqual(resolved['characters'][0]['sheet']['fields']['energy'],2)
            self.assertIsNone(resolved['narrative']['pending'])
            self.assertEqual(resolved['narrative']['continuation']['message'],len(resolved['messages'])-1)
            complete=self.apply(resolved,'continue_pack_adventure',reply(narration='La luz muestra una marca, tras el éxito confirmado.'))
            self.assertEqual(complete['characters'],resolved['characters'])
            self.assertIsNone(complete['narrative']['continuation'])
            campaign.validate_restored(complete)
            with self.assertRaises(RulePackError):self.apply(complete,'continue_pack_adventure')

    def test_pending_has_owner_package_and_sheet_binding_even_for_host(self):
        pending=self.pending();request=pending['narrative']['pending'];before=copy.deepcopy(pending)
        for kind in ('resolve_pack_request','cancel_pack_request'):
            with self.assertRaises(PermissionError):campaign.execute_action(pending,{'type':kind,'request':request['id']},self.me|{'id':'other'})
        for field,value in (('packageSha256','0'*64),('sheetRevision',55),('rolls',[{'id':'dice','count':2,'sides':20,'keep':2}])):
            bad=copy.deepcopy(pending);bad['narrative']['pending'][field]=value
            with self.assertRaises(RulePackError):campaign.validate_restored(bad)
            with patch('rule_pack_runtime.secrets.randbelow',side_effect=AssertionError('Stale request rolled')):
                with self.assertRaises(RulePackError):self.apply(bad,'resolve_pack_request',request=request['id'])
            withdrawn=self.apply(bad,'cancel_pack_request',request=request['id'])
            self.assertIsNone(withdrawn['narrative']['pending'])
        with self.assertRaises(RulePackError):self.apply(pending,'resolve_pack_request',request='old')
        with self.assertRaises(RulePackError):self.apply(pending,'run_pack_action',character=self.character,action='intentar')
        self.assertEqual(pending,before)
        canceled=self.apply(pending,'cancel_pack_request',request=request['id'])
        self.assertIsNone(canceled['narrative']['pending']);self.assertEqual(canceled['characters'],before['characters'])

    def test_dialogue_ooc_and_limitations_cannot_apply_or_propose_mechanics(self):
        state=self.start()
        provider=Mock(side_effect=AssertionError('OOC called provider'))
        ooc=campaign.execute_action(state,{'type':'talk_pack_adventure','character':self.character,'text':'Pausa para hablar.','mode':'ooc'},self.me,narrative_call=provider)
        provider.assert_not_called();self.assertEqual(ooc['narrative'],state['narrative'])
        for mode in ('dialogue','action'):
            answer=reply('intentar',limitation='Mecánica no cubierta') if mode=='action' else reply('intentar')
            with self.assertRaises(RulePackError):self.apply(state,'talk_pack_adventure',answer,character=self.character,text='¿Qué ves?',mode=mode)
        limited=self.apply(state,'talk_pack_adventure',reply(limitation='El paquete no define combate.'),character=self.character,text='Ataco con una espada.',mode='action')
        self.assertIsNone(limited['narrative']['pending']);self.assertEqual(limited['characters'],state['characters'])

    def test_unavailable_actions_bad_inputs_and_illegal_requirements_are_rejected(self):
        state=self.start()
        for action in ('unknown','generate'):
            with self.assertRaises(RulePackError):self.apply(state,'talk_pack_adventure',reply(action),character=self.character,text='Investigo.',mode='action')
        bad=reply('intentar');bad['proposal']['inputsJson']='{"forged":1}'
        with patch('rule_pack_runtime.secrets.randbelow',side_effect=AssertionError('Invalid request rolled')):
            with self.assertRaises(RulePackError):self.apply(state,'talk_pack_adventure',bad,character=self.character,text='Investigo.',mode='action')
        # A complete, replayable exhausted sheet cannot acquire an illegal request.
        for _ in range(3):self.state=campaign.execute_action(self.state,{'type':'run_pack_action','character':self.character,'action':'intentar','physical':{'dice':[1,1]}},self.me)
        exhausted=self.start()
        with self.assertRaises(RulePackError):self.apply(exhausted,'talk_pack_adventure',reply('intentar'),character=self.character,text='Investigo.',mode='action')

    def test_private_memory_is_filtered_and_context_never_loads_rule_fragments(self):
        state=self.start();state['authoringWorkspaceRef']={'format':'cronicas-rule-workspace-ref-1','sha256':'a'*64}
        view=campaign.public_view(state,self.me|{'host':False})
        self.assertNotIn('PRIVATE-DIRECTOR',json.dumps(view));self.assertNotIn('narrative',view)
        pack=campaign.runtime(state,self.me['campaign'])
        prepared=director.prepare(state,'talk',state['characters'][0],'Investigo.','action',pack)
        self.assertIn('PRIVATE-DIRECTOR',json.dumps(prepared))
        self.assertNotIn('authoringWorkspaceRef',json.dumps(prepared));self.assertNotIn('fragments',prepared['request'])
        self.assertEqual(prepared['request']['rules']['sha256'],pack.digest)
        self.assertIn('intentar',prepared['request']['allowedActions'])

    def test_distinct_confirmed_turns_cannot_collide_even_if_the_context_repeats(self):
        state=self.start();pack=campaign.runtime(state,self.me['campaign']);actor=state['characters'][0]
        first=director.prepare(state,'talk',actor,'¿Qué ves?','dialogue',pack)
        repeated=copy.deepcopy(state);repeated['narrative']['revision']+=1
        second=director.prepare(repeated,'talk',actor,'¿Qué ves?','dialogue',pack)
        self.assertNotEqual(first['sha256'],second['sha256'])
        self.assertEqual(second['request']['turn'],first['request']['turn']+1)

    def test_copy_replays_pending_and_confirmed_mechanics_without_rng(self):
        pending=self.pending()
        with patch('rule_pack_runtime.secrets.randbelow',side_effect=AssertionError('Story copy rolled')):
            restored=campaign.import_campaign(pending,self.me|{'id':'eva'})
            self.assertEqual(restored['characters'][0]['owner'],'eva')
            resolved=campaign.execute_action(restored,{'type':'resolve_pack_request','request':restored['narrative']['pending']['id'],'physical':{'dice':[6,6]}},self.me|{'id':'eva'})
            campaign.validate_restored(resolved)
            for mutation in ('continuation','trace','memory'):
                bad=copy.deepcopy(resolved)
                if mutation=='continuation':bad['narrative']['continuation']['message']=0
                elif mutation=='trace':bad['messages'][-1]['trace']['rolls']['dice']['values']=[1,1]
                else:bad['narrative']['revision']=True
                with self.assertRaises(RulePackError):campaign.validate_restored(bad)

    def test_space_is_reserved_before_provider_and_inputs_are_strict(self):
        state=self.start();state['messages'].append({'kind':'system','text':'x'*660000,'actor':'ana','time':1})
        provider=Mock(side_effect=AssertionError('Full state called provider'))
        with self.assertRaises(RulePackError):campaign.execute_action(state,{'type':'talk_pack_adventure','character':self.character,'text':'Investigo.','mode':'action'},self.me,narrative_call=provider)
        provider.assert_not_called()
        prepared=director.prepare(self.state,'start',self.state['characters'][0],'','action',campaign.runtime(self.state,self.me['campaign']))
        for field,value in (('proposal',{'action':'','inputsJson':{},'reason':''}),('usage',{'inputTokens':True,'outputTokens':0,'latencyMs':0}),('sheet',{})):
            with self.assertRaises(RulePackError):director.validate_reply(prepared,reply(**{field:value}))

    def test_generic_capture_recovers_cold_without_another_provider_call(self):
        pack=campaign.runtime(self.state,self.me['campaign']);prepared=director.prepare(self.state,'start',self.state['characters'][0],'','action',pack)
        output=json.dumps({'stop_reason':'end_turn','content':[{'type':'text','text':json.dumps(reply())}],'usage':{'input_tokens':100,'output_tokens':200}}).encode()
        store=TestStore()
        with patch.dict(os.environ,{'ANTHROPIC_API_KEY':'fixture-never-sent'}),patch.object(director.urllib.request,'urlopen',return_value=io.BytesIO(output)) as provider:
            first=attempts.run(store,'room','ana',prepared,converter=director.propose,restore=director.restore)
            self.assertEqual(provider.call_count,1)
        cold=TestStore();cold.preparations=copy.deepcopy(store.preparations)
        saved=next(iter(cold.preparations.values()));self.assertEqual(saved['promptSha256'],prepared['promptSha256'])
        with patch.dict(os.environ,{'ANTHROPIC_API_KEY':''}),patch.object(director,'propose',side_effect=AssertionError('Cold recovery called provider')):
            second=attempts.run(cold,'room','ana',prepared,converter=director.propose,restore=director.restore)
        self.assertEqual(first,second);self.assertEqual(second['usage']['outputTokens'],200)
