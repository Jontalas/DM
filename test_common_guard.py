import copy
import math
import unittest
from unittest.mock import patch
import engine
import npc_catalog
import pf_ceasefire
import pf_encounters
import pf_night_rest
import pf_scene_transition
from test_character_builder import choices


class CommonGuardTests(unittest.TestCase):
    me={'id':'host','name':'Ana','host':True}

    def setUp(self):
        self.state=engine.initial_state({});self.act('create_character',choices=choices())
        self.actor=self.state['characters'][0]['id']
        self.act('enter_pf_encounter',encounter='patio-del-peaje',encounterVersion='1.10.0',character=self.actor)
        self.npc=self.state['characters'][1]['id']

    def act(self,kind,**body):engine.apply_action(self.state,{'type':kind,**body},self.me)

    def wound_guard(self):
        with patch('game_randomness.draw',side_effect=[20,1]),patch('game_randomness.initiative_tie',return_value=0):self.act('choose_pf_encounter',choice='combat')
        with patch('game_randomness.draw',side_effect=[12,1]):self.act('attack',character=self.actor,target=self.npc)
        self.assertEqual(self.state['characters'][1]['hp'],1)

    def test_original_template_hash_and_seven_hp_remain_frozen(self):
        data,proof=npc_catalog.prepare('pf1-goblin-warrior-1','pathfinder-1e')
        self.assertEqual(proof['templateSha256'],'04f7b0f12f49dc360411d4aae8e54a3c19a82bce6e465b5d267ffdf9368fda12')
        self.assertEqual((data['maxHp'],data['ac'],data['abilities'][3]),(7,16,10))
        self.assertNotIn('languages',proof['profile'])
        for version in ('1.0.0','1.7.0','1.8.0','1.9.0'):
            self.assertEqual(pf_encounters.definition(version)['npc']['template'],'pf1-goblin-warrior-1')

    def test_new_guard_totals_follow_npc_array_race_class_ranks_and_normal_hit_die(self):
        data,proof=npc_catalog.prepare('pf1-common-speaking-goblin-guard-1','pathfinder-1e')
        source=proof['profile']['construction'];mods=[(a-10)//2 for a in data['abilities']]
        self.assertEqual(sorted(source['baseAbilities']),[8,9,10,11,12,13])
        self.assertEqual(data['abilities'],[b+r for b,r in zip(source['baseAbilities'],source['racialAdjustments'])])
        self.assertEqual(data['hp'],math.floor((source['hitDie']+1)/2+mods[2]+source['favoredHp']))
        self.assertEqual(data['hp'],6);self.assertEqual(data['saves'],[2+mods[2],mods[1],mods[4]])
        self.assertEqual(data['ac'],10+mods[1]+1+source['armorAc']+source['shieldAc'])
        self.assertEqual(data['meleeProfile']['flatAc'],data['ac']-mods[1]);self.assertEqual(data['attack'],1+mods[0]+1)
        self.assertEqual(sum(source['skillRanks'].values()),2+mods[3])
        self.assertEqual({r['name']:r['total'] for r in data['skillTotals']},{'Percepción':1+mods[4],
            'Montar':1+3+mods[1]+4,'Nadar':1+3+mods[0],'Sigilo':mods[1]+4+4})
        self.assertEqual(proof['profile']['languages'],['Goblin','Común']);self.assertEqual(mods[3],1)

    def test_default_character_can_accept_common_offer_without_changing_languages_or_wounds(self):
        self.assertEqual(self.state['characters'][0]['creation']['choices']['languages'],[])
        self.wound_guard();before=copy.deepcopy(self.state['characters'])
        self.assertIsNone(pf_ceasefire.limitation(self.state));self.act('accept_pf_ceasefire')
        self.assertEqual(self.state['characters'],before)
        receipt=self.state['pfEncounter']['ceasefire']
        self.assertEqual(receipt['format'],pf_ceasefire.SHARED_FORMAT);self.assertEqual(receipt['sharedLanguage'],'Común')
        pf_encounters.validate_restored(self.state)
        for language in ('Goblin','Élfico',None):
            altered=copy.deepcopy(self.state);altered['pfEncounter']['ceasefire']['sharedLanguage']=language
            with self.assertRaises(ValueError):pf_encounters.validate_restored(altered)

    def test_organic_zero_common_truce_night_and_route_keep_guard_one_hp_and_original_profile(self):
        self.wound_guard()
        for _ in range(4):
            with patch('game_randomness.draw',side_effect=[19,1,4]):self.act('turn')
        self.assertEqual(self.state['characters'][0]['hp'],0)
        self.act('accept_pf_ceasefire');self.act('rest_pf_night')
        self.assertEqual([c['hp'] for c in self.state['characters']],[1,1])
        pf_encounters.validate_restored(self.state);pf_night_rest.validate_restored(self.state)
        self.act('continue_pf_encounter');pf_scene_transition.validate_restored(self.state)
        pf_night_rest.validate_restored(self.state);self.assertEqual(self.state['characters'][1]['maxHp'],6)

    def test_new_guard_can_resolve_combat_without_reinterpreting_old_outcomes(self):
        with patch('game_randomness.draw',side_effect=[20,1]),patch('game_randomness.initiative_tie',return_value=0):self.act('choose_pf_encounter',choice='combat')
        with patch('game_randomness.draw',side_effect=[20,20,8,8]):self.act('attack',character=self.actor,target=self.npc)
        self.assertEqual(self.state['pfEncounter']['phase'],'resolved');self.assertEqual(self.state['pfEncounter']['outcome']['constitution'],10)
        pf_encounters.validate_restored(self.state);self.act('rest_pf_night');pf_night_rest.validate_restored(self.state)
