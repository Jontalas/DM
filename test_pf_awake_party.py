import copy
import unittest
from unittest.mock import patch
import engine
import pf_awake_party
import pf_encounters
from test_character_builder import choices


class AwakePartyProofTests(unittest.TestCase):
    def setUp(self):
        self.me={'id':'player','name':'Ana','host':True};self.state=engine.initial_state({})
        self.act('create_character',choices=choices());self.actor=self.state['characters'][0]['id']
        self.act('enter_pf_encounter',encounter='patio-del-peaje',encounterVersion=getattr(self,'encounter_version','1.12.0'),character=self.actor)
        with patch('game_randomness.draw',side_effect=[20,1]),patch('game_randomness.initiative_tie',return_value=0):self.act('choose_pf_encounter',choice='combat')
        for _ in range(4):
            with patch('game_randomness.draw',side_effect=[19,1,4]):self.act('turn')
        self.assertEqual(self.state['characters'][0]['hp'],0)
        npc=self.state['characters'][1]['id']
        with patch('game_randomness.draw',side_effect=[12,4,20,20,20,20]):self.act('attack',character=self.actor,target=npc)
        self.assertEqual([c['hp'] for c in self.state['characters']],[-1,-2])

    def act(self,kind,**body):engine.apply_action(self.state,{'type':kind,**body},self.me)

    def test_current_shared_patients_match_replay_without_rng_or_mutation(self):
        before=copy.deepcopy(self.state)
        with patch('game_randomness.draw',side_effect=AssertionError('Revalidation rolled')):
            pf_encounters.validate_restored(self.state)
            self.assertTrue(pf_awake_party.verified(self.state))
        self.assertEqual(self.state,before)
        # This proof alone cannot expand the published zero-only scene.
        import pf_light_exploration
        self.assertFalse(pf_light_exploration.eligible(self.state,self.state['characters'][0]))

    def test_past_consciousness_does_not_certify_changed_current_patients(self):
        baseline=copy.deepcopy(self.state)
        for case in ('hp','care','conscious','constitution','condition','override','new-combat','receipt','missing-proof'):
            self.state=copy.deepcopy(baseline);actor,npc=self.state['characters']
            if case=='hp':npc['hp']+=1
            elif case=='care':npc['recoveryCare']['assisted']=not npc['recoveryCare']['assisted']
            elif case=='conscious':npc['recoveryState']['conscious']=False
            elif case=='constitution':actor['abilities'][2]+=2
            elif case=='condition':actor['conditions']='Fatigado'
            elif case=='override':actor['creation']['manualOverride']=True
            elif case=='new-combat':self.state['board']['combatSerial']=2
            elif case=='receipt':self.state['pfEncounter']['recoveryOutcome']['rolls'].append([0,20])
            else:actor.pop('recoveryState')
            before=copy.deepcopy(self.state)
            with self.subTest(case=case),patch('game_randomness.draw',side_effect=AssertionError('Invalid proof rolled')):
                self.assertFalse(pf_awake_party.verified(self.state));self.assertEqual(self.state,before)
