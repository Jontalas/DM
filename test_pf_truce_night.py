import copy
import unittest
from unittest.mock import patch
import engine
import pf_night_rest as rest
import pf_encounters
import pf_scene_transition
import test_pf_ceasefire


class TruceNightTests(unittest.TestCase):
    me={'id':'host','name':'Ana','host':True}
    act=test_pf_ceasefire.PreparedCeasefireTests.act
    wound_guard=test_pf_ceasefire.PreparedCeasefireTests.wound_guard

    def prepare(self,armor='chainshirt'):
        from test_character_builder import choices
        selected=choices();selected['abilities'][3:5]=[12,10]
        selected['languages']=['Goblin'];selected['skills'].append('swim');selected['armor']=armor
        self.state=engine.initial_state({});self.act('create_character',choices=selected)
        self.actor=self.state['characters'][0]['id']
        self.act('enter_pf_encounter',encounter=pf_encounters.ID,encounterVersion='1.9.0',character=self.actor)
        self.npc=self.state['characters'][1]['id']

    def test_zero_hp_can_sleep_after_organic_truce_without_healing_wounded_guard(self):
        self.prepare();self.wound_guard()
        for _ in range(4):
            with patch('game_randomness.draw',side_effect=[19,1,4]):self.act('turn')
        self.assertEqual(self.state['characters'][0]['hp'],0)
        self.act('accept_pf_ceasefire');before=copy.deepcopy(self.state)
        self.assertIsNone(rest.public_view(self.state)['reason'])
        with patch('game_randomness.draw',side_effect=AssertionError('Truce night rolled')):self.act('rest_pf_night')
        result=self.state['pfNightRest']['result']
        self.assertEqual(result['healing']['hpAfter'],1);self.assertEqual(result['npcHpAfter'],2)
        self.assertEqual(result['seconds'],28800);self.assertEqual(result['npcActivity'],'awake-watch')
        expected=copy.deepcopy(before['characters']);expected[0]['hp']=1
        self.assertEqual(self.state['characters'],expected)
        self.assertEqual(self.state['pfNightRest']['format'],rest.TRUCE_FORMAT)
        rest.validate_restored(self.state);pf_encounters.validate_restored(self.state)
        self.act('continue_pf_encounter');rest.validate_restored(self.state);pf_scene_transition.validate_restored(self.state)
        self.assertEqual(self.state['characters'][0]['hp'],1)

    def test_new_night_binds_the_truce_and_does_not_expand_old_scenarios(self):
        self.prepare();self.wound_guard();self.act('accept_pf_ceasefire');self.act('rest_pf_night')
        baseline=copy.deepcopy(self.state)
        for case in ('truce-origin','missing-truce','format','guard-healing'):
            altered=copy.deepcopy(baseline)
            if case=='truce-origin':altered['pfNightRest']['start']['ceasefireSha256']='0'*64
            elif case=='missing-truce':del altered['pfEncounter']['ceasefire']
            elif case=='format':altered['pfNightRest']['format']=rest.ARMOR_FORMAT
            else:altered['pfNightRest']['result']['npcHpAfter']=7
            with self.subTest(case=case),self.assertRaises(ValueError):rest.validate_restored(altered)
        self.prepare();self.wound_guard();self.act('accept_pf_ceasefire')
        self.state['pfEncounter']['definition']=pf_encounters.definition('1.8.0')
        self.assertIsNotNone(rest.limitation(self.state))

    def test_zero_hp_does_not_authorize_armor_preparation_or_negative_patients(self):
        for armor in ('chainshirt','scale'):
            self.prepare(armor);self.wound_guard();self.act('accept_pf_ceasefire')
            self.state['characters'][0]['hp']=0
            before=copy.deepcopy(self.state)
            with self.assertRaises(ValueError):self.act('rest_pf_night',armorPlan='remove-and-reequip')
            self.assertEqual(self.state,before)
            self.state['characters'][1]['hp']=-1
            self.assertIsNotNone(rest.public_view(self.state)['reason'])

    def test_positive_truce_keeps_normal_scale_preparation_and_guard_wounds(self):
        self.prepare('scale');self.wound_guard();self.act('accept_pf_ceasefire')
        before=copy.deepcopy(self.state['characters'])
        self.act('rest_pf_night',armorPlan='remove-and-reequip')
        result=self.state['pfNightRest']['result']
        self.assertEqual(result['seconds'],29100);self.assertEqual(result['npcHpAfter'],2)
        self.assertEqual(self.state['characters'],before);rest.validate_restored(self.state)

    def test_initial_peace_has_no_truce_hash_and_still_caps_healing(self):
        self.prepare();self.act('choose_pf_encounter',choice='parley');self.act('rest_pf_night')
        self.assertIsNone(self.state['pfNightRest']['start']['ceasefireSha256'])
        self.assertEqual(self.state['pfNightRest']['result']['healing']['amount'],0)
        rest.validate_restored(self.state)
