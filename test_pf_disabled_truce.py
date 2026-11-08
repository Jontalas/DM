"""Authored mercy offer, not a new Pathfinder surrender or Diplomacy rule."""
import copy
import hashlib
import unittest
from unittest.mock import patch
import engine
import pf_ceasefire
import pf_encounters
import pf_light_exploration
import director_prepared_facts
from rule_pack_authoring import canonical
from test_character_builder import choices


class DisabledTruceTests(unittest.TestCase):
    def setUp(self):
        self.me={'id':'player','name':'Ana','host':True};self.state=engine.initial_state({})
        self.act('create_character',choices=choices());self.actor=self.state['characters'][0]['id']
        self.act('enter_pf_encounter',encounter='patio-del-peaje',encounterVersion='1.15.0',character=self.actor)
        with patch('game_randomness.draw',side_effect=[20,1]),patch('game_randomness.initiative_tie',return_value=0):self.act('choose_pf_encounter',choice='combat')
        for _ in range(4):
            with patch('game_randomness.draw',side_effect=[19,1,4]):self.act('turn')
        self.assertEqual([c['hp'] for c in self.state['characters']],[0,6])

    def act(self,kind,**body):engine.apply_action(self.state,{'type':kind,**body},self.me)

    def test_free_choice_preserves_every_patient_clock_position_and_action_then_explores(self):
        self.assertIsNone(pf_ceasefire.limitation(self.state));self.assertTrue(pf_ceasefire.disabled_player_offer(self.state))
        before=copy.deepcopy(self.state)
        with patch('game_randomness.draw',side_effect=AssertionError('Brief speech rolled')):
            self.act('accept_pf_ceasefire')
        for key in ('characters','worldTime','pending','consequences'):self.assertEqual(self.state[key],before[key])
        self.assertEqual(self.state['board']['spent'],before['board']['spent']);self.assertFalse(self.state['board']['active'])
        self.assertEqual(self.state['pfEncounter']['ceasefire']['format'],pf_ceasefire.DISABLED_FORMAT)
        self.assertNotIn('guardiana herida',self.state['messages'][-1]['text'])
        pf_encounters.validate_restored(self.state)
        self.assertTrue(pf_light_exploration.eligible(self.state,self.state['characters'][0]))
        self.assertEqual(director_prepared_facts.public_facts(self.state)['publicDocumentsAccess'],'already-permitted')
        self.act('continue_pf_encounter');pf_encounters.validate_restored(self.state)
        import adventure_modules
        self.assertIsNotNone(adventure_modules.investigation(self.state,{'character':self.actor,'opportunity':'registro'},self.me))
        self.assertEqual([c['hp'] for c in self.state['characters']],[0,6])

    def test_waiting_does_not_accept_or_spend_hp_and_owner_keeps_choice(self):
        with patch('game_randomness.draw',side_effect=AssertionError('Zero HP waiting rolled')):self.act('turn')
        self.assertEqual(self.state['pfEncounter']['phase'],'combat');self.assertTrue(self.state['board']['active'])
        self.assertEqual([c['hp'] for c in self.state['characters']],[0,6]);self.assertIsNone(pf_ceasefire.limitation(self.state))
        before=copy.deepcopy(self.state)
        with self.assertRaises(PermissionError):pf_ceasefire.accept(self.state,{'type':'accept_pf_ceasefire'},{**self.me,'id':'other'})
        self.assertEqual(self.state,before)

    def test_healthy_player_cannot_demand_mercy_and_old_definition_is_not_widened(self):
        baseline=copy.deepcopy(self.state)
        for case in ('positive-player','negative-player','old','condition','out-of-turn','pending'):
            self.state=copy.deepcopy(baseline)
            if case=='positive-player':self.state['characters'][0]['hp']=1
            elif case=='negative-player':self.state['characters'][0]['hp']=-1
            elif case=='old':
                d=pf_encounters.definition('1.14.0');self.state['pfEncounter'].update(definition=d,sha256=hashlib.sha256(canonical(d).encode()).hexdigest())
            elif case=='condition':self.state['characters'][0]['conditions']='Fatigado'
            elif case=='out-of-turn':self.state['board']['turn']=1
            else:self.state['pending']=[{'reason':'Pendiente'}]
            before=copy.deepcopy(self.state)
            with self.subTest(case=case):
                self.assertIsNotNone(pf_ceasefire.limitation(self.state))
                with self.assertRaises(ValueError):self.act('accept_pf_ceasefire')
                self.assertEqual(self.state,before)

    def test_receipt_cannot_be_relabelled_or_certify_healthy_player_and_guard(self):
        self.act('accept_pf_ceasefire');baseline=copy.deepcopy(self.state)
        for case in ('format','positive-player','negative-player','bool-player','npc-overmax','marker','remove'):
            altered=copy.deepcopy(baseline);receipt=altered['pfEncounter']['ceasefire']
            if case=='format':receipt['format']=pf_ceasefire.SHARED_FORMAT
            elif case=='positive-player':receipt['actorHp']=1
            elif case=='negative-player':receipt['actorHp']=-1
            elif case=='bool-player':receipt['actorHp']=False
            elif case=='npc-overmax':receipt['npcHp']=7
            elif case=='remove':del altered['pfEncounter']['ceasefire']
            else:altered['messages'][-1]['ceasefireSha256']='0'*64
            if case not in ('remove','marker'):altered['messages'][-1]['ceasefireSha256']=hashlib.sha256(canonical(receipt).encode()).hexdigest()
            with self.subTest(case=case),self.assertRaises(ValueError):pf_encounters.validate_restored(altered)

    def test_new_scene_retains_first_aid_and_exact_negative_awareness_proofs(self):
        import test_pf_npc_aid_integration as medical
        fixture=medical.NPCFirstAidIntegrationTests()
        fixture.encounter_version='1.15.0';fixture.setUp()
        fixture.test_disabled_attack_fall_gets_npc_next_standard_and_assisted_awareness_without_healing()

    def test_new_receipt_still_allows_wounded_guard_offer_to_positive_player(self):
        self.state['characters'][0]['hp']=1;self.state['characters'][1]['hp']=1
        self.assertIsNone(pf_ceasefire.limitation(self.state));self.act('accept_pf_ceasefire')
        self.assertEqual(self.state['pfEncounter']['ceasefire']['format'],pf_ceasefire.DISABLED_FORMAT)
        self.assertIn('guardiana herida',self.state['messages'][-1]['text']);pf_encounters.validate_restored(self.state)
