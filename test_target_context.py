import copy
import unittest
from unittest.mock import Mock,patch
import target_context
import rule_pack_campaign as campaign
from rule_pack_runtime import RulePack,RulePackError
from test_target_sheets import target_document
from test_rule_pack_narrative import reply
from test_rule_pack_world import npc


def abstract_document():
    data=target_document();data['id']='original-abstract-context-example';data['version']='1.3.0'
    data['name']='Encuentro abstracto propio';data['edition']='Ejemplo propio 4'
    data['requires'].append('abstract-scene-targets')
    data['fields']['scene']={'type':'text','label':'Escena propia','sources':['staged-source'],'initial':'farol','maxLength':64}
    data['fields']['visible']={'type':'boolean','label':'Percepción compartida propia','sources':['staged-source'],'initial':True}
    data['actions']['contest']['targetContext']={'kind':'abstract-scene','sceneField':'scene','visibleField':'visible','turns':'not-required'}
    data['sources'][0]['locator']+=' Variante propia: participantes empiezan en la escena farol; percepción compartida explícita; la prueba abstracta no requiere turnos ni alcance espacial.'
    return data


class AbstractTargetContextTests(unittest.TestCase):
    def setUp(self):
        self.me={'id':'ana','name':'Ana','host':True,'campaign':'abstract-context'}
        state=campaign.execute_action(campaign.initial_state({}),{'type':'install_rule_pack','package':abstract_document(),'policy':'provided-rules'},self.me)
        state=campaign.execute_action(state,{'type':'create_pack_sheet','name':'Aria','physical':{'aptitude':[1]}},self.me);self.cid=state['characters'][0]['id']
        state=campaign.execute_action(state,{'type':'advance_pack_creation','character':self.cid,'step':'training','inputs':{'role':'cronista','focus':1}},self.me)
        state=campaign.execute_action(state,{'type':'start_pack_adventure','character':self.cid},self.me,
            narrative_call=Mock(return_value=reply(npcUpdates=[npc(),npc('sombra',known=False,public='')])))
        for identifier,reference in [('a'*24,'arda'),('b'*24,'sombra')]:
            state=campaign.execute_action(state,{'type':'create_pack_actor','actor':identifier,'npc':reference,'profile':'support',
                'stages':[{'inputs':{},'physical':{}}],'publicFields':[],'policy':'provided-profile'},self.me)
        self.state=state;self.pack=campaign.runtime(state,self.me['campaign'])

    def test_candidates_are_known_present_perceived_and_owned_without_dice(self):
        original=copy.deepcopy(self.state)
        with patch('rule_pack_runtime.secrets.randbelow',side_effect=AssertionError('Candidate selection rolled')):
            options=target_context.options(self.state,self.me,self.pack)
            binding,preview=target_context.select(self.state,self.cid,'a'*24,'contest',{},self.me,self.pack)
        self.assertEqual(options['byCharacter'],{self.cid:{'scene:visible':['a'*24]}})
        self.assertEqual(binding['target'],'a'*24);self.assertEqual(preview['rolls'][0]['count'],2)
        self.assertEqual(self.state,original);self.assertNotIn('fields',str(options))
        self.assertEqual(target_context.options(self.state,self.me|{'id':'eva'},self.pack)['byCharacter'],{})

    def test_other_scene_unknown_or_unperceived_targets_fail_before_dice(self):
        for change in [{'scene':'otro-lugar'},{'visible':False},{'scene':''}]:
            state=copy.deepcopy(self.state);state['actors'][0]['sheet']['fields'].update(change)
            self.assertEqual(target_context.options(state,self.me,self.pack)['byCharacter'],{})
            with patch('rule_pack_runtime.secrets.randbelow',side_effect=AssertionError('Unavailable target rolled')):
                with self.assertRaises(RulePackError):target_context.select(state,self.cid,'a'*24,'contest',{},self.me,self.pack)
        with self.assertRaises(RulePackError):target_context.select(self.state,self.cid,'b'*24,'contest',{},self.me,self.pack)
        with self.assertRaises(RulePackError):target_context.select(self.state,self.cid,'a'*24,'explore',{},self.me,self.pack)

    def test_context_does_not_approximate_spatial_range_or_turns(self):
        for change in [{'kind':'spatial-range'},{'turns':'initiative'},{'sceneField':'energy'},{'visibleField':'scene'}]:
            data=abstract_document();data['actions']['contest']['targetContext'].update(change)
            with self.assertRaises(RulePackError):RulePack(data)
        data=abstract_document();data['requires'].remove('abstract-scene-targets')
        with self.assertRaises(RulePackError):RulePack(data)
