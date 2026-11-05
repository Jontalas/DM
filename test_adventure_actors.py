import copy
import unittest
from unittest.mock import patch
import adventure_actors
from rule_pack_runtime import RulePack,RulePackError
from test_target_context import abstract_document
from test_rule_pack_world import npc


class AdventureActorsTests(unittest.TestCase):
    def setUp(self):
        self.pack=RulePack(abstract_document())
        self.preparation={'format':adventure_actors.FORMAT,
            'package':{'id':self.pack.id,'version':self.pack.version,'sha256':self.pack.digest},
            'npcs':[npc(),npc('sombra',known=False,public='')],
            'actors':[{'id':'a'*24,'npc':'arda','profile':'support','stages':[{'inputs':{},'physical':{}}],
                'publicFields':['energy']}]}

    def compile(self,preparation=None,**options):
        return adventure_actors.compile_preparation(self.preparation if preparation is None else preparation,self.pack,'provided-profile',**options)

    def test_complete_profile_compiles_without_randomness_or_input_mutation(self):
        before=copy.deepcopy(self.preparation)
        with patch('rule_pack_runtime.secrets.randbelow',side_effect=AssertionError('Preparation generated dice')):
            first=self.compile();second=self.compile()
        self.assertEqual(first,second);self.assertEqual(before,self.preparation)
        self.assertEqual(first['actors'][0]['sheet']['owner'],'director:'+'a'*24)
        self.assertNotIn('introducedAt',first['actors'][0])
        first['npcs'][0]['name']='Changed';self.assertNotEqual(first,self.compile())

    def test_rejects_wrong_package_policy_raw_statistics_and_unknown_npc(self):
        variants=[]
        wrong=copy.deepcopy(self.preparation);wrong['package']['sha256']='0'*64;variants.append(wrong)
        raw=copy.deepcopy(self.preparation);raw['actors'][0]['fields']={'energy':999};variants.append(raw)
        unknown=copy.deepcopy(self.preparation);unknown['actors'][0]['npc']='missing';variants.append(unknown)
        for value in variants:
            with self.assertRaises(RulePackError):self.compile(value)
        with self.assertRaises(RulePackError):adventure_actors.compile_preparation(self.preparation,self.pack,'unconfirmed')

    def test_rejects_duplicate_identity_npc_and_player_collision(self):
        for replacement in [{'id':'a'*24,'npc':'sombra'},{'id':'b'*24,'npc':'arda'}]:
            value=copy.deepcopy(self.preparation);value['actors'].append(value['actors'][0]|replacement)
            with self.assertRaises(RulePackError):self.compile(value)
        with self.assertRaises(RulePackError):self.compile(player_ids=['a'*24])

    def test_incomplete_creation_never_rolls_as_fallback(self):
        value=copy.deepcopy(self.preparation);value['actors'][0]['profile']='default'
        with patch('rule_pack_runtime.secrets.randbelow',side_effect=AssertionError('Fallback rolled')):
            with self.assertRaises(RulePackError):self.compile(value)
        # The alternative profile explicitly uses the package's random aptitude
        # stage. Missing confirmed dice must fail, even if the inputs are legal.
        data=abstract_document();data['creationProfiles']['random-support']={'label':'Random support',
            'sources':['staged-source'],'steps':['aptitude','training']}
        pack=RulePack(data);value['package']={'id':pack.id,'version':pack.version,'sha256':pack.digest}
        value['actors'][0].update(profile='random-support',stages=[{'inputs':{},'physical':{}},
            {'inputs':{'role':'cronista','focus':0},'physical':{}}])
        with patch('rule_pack_runtime.secrets.randbelow',side_effect=AssertionError('Unconfirmed preparation rolled')):
            with self.assertRaisesRegex(RulePackError,'dados confirmados'):
                adventure_actors.compile_preparation(value,pack,'provided-profile')

    def test_confirmed_dice_and_all_stages_replay(self):
        data=abstract_document();data['creationProfiles']['random-support']={'label':'Random support',
            'sources':['staged-source'],'steps':['aptitude','training']}
        pack=RulePack(data);value=copy.deepcopy(self.preparation)
        value['package']={'id':pack.id,'version':pack.version,'sha256':pack.digest}
        value['actors'][0].update(profile='random-support',stages=[{'inputs':{},'physical':{'aptitude':[4]}},
            {'inputs':{'role':'cronista','focus':0},'physical':{}}])
        result=adventure_actors.compile_preparation(value,pack,'provided-profile')
        self.assertEqual(result['actors'][0]['creation']['steps'][0]['trace']['rolls']['aptitude']['values'],[4])
        self.assertTrue(pack.ready(result['actors'][0]['sheet']))
