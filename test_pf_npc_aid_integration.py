import copy
import hashlib
import unittest
from unittest.mock import patch
import engine
import pf_encounters
import pf_npc_aid
import pf_recovery
import pf_light_exploration
import test_character_builder as builder
from rule_pack_authoring import canonical


class NPCFirstAidIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.me={'id':'player','name':'Ana','host':True};self.state=engine.initial_state({})
        selected=builder.choices()
        if getattr(self,'armor',None):selected['armor']=self.armor
        self.act('create_character',choices=selected);self.actor=self.state['characters'][0]['id']
        self.act('enter_pf_encounter',encounter='patio-del-peaje',encounterVersion=getattr(self,'encounter_version','1.14.0'),character=self.actor)
        self.npc=self.state['characters'][1]['id']
        with patch('game_randomness.draw',side_effect=[20,1]),patch('game_randomness.initiative_tie',return_value=0):self.act('choose_pf_encounter',choice='combat')

    def act(self,kind,**body):engine.apply_action(self.state,{'type':kind,**body},self.me)

    def zero(self):
        for _ in range(4):
            with patch('game_randomness.draw',side_effect=[19,1,4]):self.act('turn')
        self.assertEqual(self.state['characters'][0]['hp'],0)

    def test_disabled_attack_fall_gets_npc_next_standard_and_assisted_awareness_without_healing(self):
        self.zero();old_board=self.state['board']
        with patch('game_randomness.draw',side_effect=[12,1,20,20]) as dice:self.act('attack',character=self.actor,target=self.npc)
        self.assertEqual(dice.call_count,4);self.assertFalse(old_board['active']);self.assertFalse(self.state['board']['active'])
        self.assertEqual([c['hp'] for c in self.state['characters']],[-1,1]);self.assertTrue(pf_recovery.is_conscious(self.state['characters'][0]))
        record=self.state['pfEncounter'];self.assertEqual(record['npcAidEpisode']['rolls'],[['first-aid',20]])
        self.assertEqual(record['npcAidEpisode']['end']['attempts'],1);self.assertTrue(record['recoveryOutcome']['assisted'])
        self.assertEqual(record['recoveryOutcome']['format'],'cronicas-pf-recovery-outcome-3');self.assertEqual(record['recoveryOutcome']['hours'],1)
        pf_encounters.validate_restored(self.state);pf_recovery.validate_restored(self.state)
        self.assertTrue(pf_light_exploration.eligible(self.state,self.state['characters'][0]));self.act('continue_pf_encounter')
        pf_encounters.validate_restored(self.state)

    def test_npc_attack_spent_standard_cannot_also_aid_before_players_check(self):
        for _ in range(5):
            with patch('game_randomness.draw',side_effect=[19,1,3]):self.act('turn')
        self.assertEqual(self.state['characters'][0]['hp'],1);old_board=self.state['board']
        with patch('game_randomness.draw',side_effect=[19,1,3,1,20,20]):self.act('turn')
        record=self.state['pfEncounter'];self.assertFalse(old_board['active'])
        self.assertEqual(record['npcAidEpisode']['rolls'],[['stabilization',1],['first-aid',20]])
        self.assertEqual([c['hp'] for c in self.state['characters']],[-3,6]);pf_encounters.validate_restored(self.state)

    def test_natural_stabilization_before_helper_turn_never_certifies_assistance(self):
        for _ in range(5):
            with patch('game_randomness.draw',side_effect=[19,1,3]):self.act('turn')
        with patch('game_randomness.draw',side_effect=[19,1,3,20,20]):self.act('turn')
        record=self.state['pfEncounter'];self.assertEqual(record['npcAidEpisode']['rolls'],[['stabilization',20]])
        self.assertEqual(record['npcAidEpisode']['end']['attempts'],0);self.assertFalse(record['recoveryOutcome']['assisted'])
        self.assertEqual([c['hp'] for c in self.state['characters']],[-2,6]);pf_encounters.validate_restored(self.state)

    def test_first_aid_does_not_remove_scale_armor_or_skip_its_recovery_limit(self):
        self.armor='scale';self.setUp();self.zero();before=copy.deepcopy(self.state['characters'][0])
        with patch('game_randomness.draw',side_effect=[12,1,20]) as dice:self.act('attack',character=self.actor,target=self.npc)
        self.assertEqual(dice.call_count,3);record=self.state['pfEncounter'];self.assertEqual(record['recoveryLimit'],'armor-rest')
        self.assertNotIn('recoveryOutcome',record);self.assertTrue(self.state['characters'][0]['recoveryCare']['assisted'])
        self.assertEqual(self.state['characters'][0]['equipment'],before['equipment']);self.assertEqual(self.state['characters'][0]['creation'],before['creation'])
        self.assertFalse(pf_recovery.is_conscious(self.state['characters'][0]));pf_encounters.validate_restored(self.state)

    def test_six_failed_assisted_checks_keep_limit_and_copy_proof_without_more_dice(self):
        self.zero()
        with patch('game_randomness.draw',side_effect=[12,1,20,*([1]*6)]):self.act('attack',character=self.actor,target=self.npc)
        record=self.state['pfEncounter'];self.assertEqual(record['recoveryLimit'],'shared-rest-boundary');self.assertEqual(record['recoveryOutcome']['hours'],6)
        self.assertEqual(self.state['characters'][0]['hp'],-1);self.assertFalse(pf_recovery.is_conscious(self.state['characters'][0]))
        self.assertFalse(pf_light_exploration.eligible(self.state,self.state['characters'][0]))
        with patch('game_randomness.draw',side_effect=AssertionError('Imported care rolled')):pf_encounters.validate_restored(copy.deepcopy(self.state))

    def test_forged_or_orphan_aid_never_certifies_assisted_recovery(self):
        self.zero()
        with patch('game_randomness.draw',side_effect=[12,1,20,20]):self.act('attack',character=self.actor,target=self.npc)
        baseline=copy.deepcopy(self.state)
        for case in ('orphan','missing','missing-both','die','helper-skill','end','care'):
            state=copy.deepcopy(baseline);record=state['pfEncounter']
            if case=='orphan':record.pop('npcAidEpisode')
            elif case=='missing':state['messages']=[m for m in state['messages'] if 'npcAidSha256' not in m]
            elif case=='missing-both':
                record.pop('npcAidEpisode');state['messages']=[m for m in state['messages'] if 'npcAidSha256' not in m]
            elif case=='die':record['npcAidEpisode']['rolls'][0][1]=1
            elif case=='helper-skill':record['npcAidEpisode']['start']['helper']['heal']=10
            elif case=='end':record['npcAidEpisode']['end']['hp']=0
            else:record['recoveryStart']['patients'][0]['care']['assisted']=False
            if case in ('die','helper-skill','end'):
                # A recomputed checksum cannot make incorrect mechanics legal.
                marker=hashlib.sha256(canonical(record['npcAidEpisode']).encode()).hexdigest()
                for message in state['messages']:
                    if 'npcAidSha256' in message:message['npcAidSha256']=marker
            with self.subTest(case=case),self.assertRaises(ValueError):pf_encounters.validate_restored(state)

    def test_previous_definition_never_gains_npc_aid_or_assisted_player_scope(self):
        self.encounter_version='1.13.0';self.setUp();self.zero()
        with patch('game_randomness.draw',side_effect=[12,1,20,20]):self.act('attack',character=self.actor,target=self.npc)
        record=self.state['pfEncounter'];self.assertNotIn('npcAidEpisode',record)
        self.assertFalse(record['recoveryOutcome']['assisted']);self.assertEqual(record['recoveryOutcome']['format'],'cronicas-pf-recovery-outcome-2')
        self.assertFalse(any(row['name']=='Curar' for row in self.state['characters'][1]['skillTotals']))
        pf_encounters.validate_restored(self.state)

    def test_variant_adds_only_untrained_heal_and_older_templates_stay_exact(self):
        import npc_catalog
        old,proof=npc_catalog.prepare('pf1-common-speaking-goblin-guard-1','pathfinder-1e')
        new,new_proof=npc_catalog.prepare(pf_npc_aid.TEMPLATE,'pathfinder-1e')
        expected=copy.deepcopy(old);expected['skillTotals'].append({'name':'Curar','total':-1})
        self.assertEqual(new,expected);self.assertEqual(new_proof['profile']['construction']['firstAid'],{'wisdom':9,'ranks':0,'classBonus':0,'kitBonus':0,'total':-1})
        original=npc_catalog._catalog()['templates']['pf1-goblin-warrior-1']
        self.assertEqual(hashlib.sha256(canonical(original).encode()).hexdigest(),'04f7b0f12f49dc360411d4aae8e54a3c19a82bce6e465b5d267ffdf9368fda12')
