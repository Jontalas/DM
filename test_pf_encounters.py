import copy
import unittest
from unittest.mock import patch
import engine
import pf_encounters
from test_character_builder import choices


class PreparedPathfinderEncounterTests(unittest.TestCase):
    def setUp(self):
        self.me={'id':'player','name':'Aria','host':True}
        self.state=engine.initial_state({})
        engine.apply_action(self.state,{'type':'create_character','choices':choices()},self.me)
        self.actor=self.state['characters'][0]['id']

    def enter(self,state=None):
        target=self.state if state is None else state
        engine.apply_action(target,{'type':'enter_pf_encounter','encounter':pf_encounters.ID,'character':self.actor},self.me)
        return target

    def test_entry_prepares_catalog_npc_without_stats_or_dice_from_the_player(self):
        before=copy.deepcopy(self.state['characters'][0])
        with patch('game_randomness.draw',side_effect=AssertionError('Entry rolled dice')):self.enter()
        self.assertEqual(self.state['characters'][0],before)
        npc=self.state['characters'][1]
        self.assertEqual((npc['hp'],npc['maxHp'],npc['ac'],npc['attack'],npc['damage']),(7,7,16,2,'1d4'))
        self.assertEqual((npc['owner'],npc['x'],npc['y']),('director',1,0))
        self.assertFalse(self.state['board']['active']);self.assertEqual(self.state['pfEncounter']['phase'],'offered')
        pf_encounters.validate_restored(self.state)

    def test_parley_is_an_explicit_player_choice_and_voluntary_authored_npc_response(self):
        self.enter();before=copy.deepcopy(self.state['characters'])
        with patch('game_randomness.draw',side_effect=AssertionError('Voluntary agreement rolled')):
            engine.apply_action(self.state,{'type':'choose_pf_encounter','choice':'parley'},self.me)
        self.assertEqual(self.state['characters'],before)
        self.assertEqual(self.state['pfEncounter']['phase'],'agreement');self.assertFalse(self.state['board']['active'])
        self.assertIn('decisión tuya',self.state['messages'][-1]['text']);pf_encounters.validate_restored(self.state)

    def test_combat_uses_existing_initiative_and_automation_and_does_not_choose_player_actions(self):
        self.enter();before=self.state['characters'][0]['hp']
        with patch('game_randomness.draw',side_effect=[20,1]):
            engine.apply_action(self.state,{'type':'choose_pf_encounter','choice':'combat'},self.me)
        self.assertTrue(self.state['board']['active']);self.assertTrue(self.state['board']['autoEnemies'])
        self.assertEqual(self.state['board']['order'][0]['id'],self.actor)
        self.assertEqual(self.state['characters'][0]['hp'],before)
        self.assertEqual(self.state['pfEncounter']['phase'],'combat');pf_encounters.validate_restored(self.state)

    def test_other_player_even_host_cannot_choose_for_owner_and_repeated_entry_rejects(self):
        self.enter();before=copy.deepcopy(self.state)
        with self.assertRaises(PermissionError):engine.apply_action(self.state,{'type':'choose_pf_encounter','choice':'combat'},self.me|{'id':'other','host':True})
        with self.assertRaises(ValueError):self.enter()
        self.assertEqual(self.state,before)

    def test_preflight_and_copy_reject_changed_participants_scene_or_provenance(self):
        for change in ('terrain','wound','position','override'):
            state=copy.deepcopy(self.state)
            if change=='terrain':state['board']['terrain']={'1,0':'wall'}
            elif change=='wound':state['characters'][0]['hp']-=1
            elif change=='position':state['characters'][0]['x']=5
            else:state['characters'][0]['creation']['manualOverride']=True
            before=copy.deepcopy(state)
            with self.assertRaises(ValueError):self.enter(state)
            self.assertEqual(state,before)
        self.enter()
        for field,value in (('sha256','0'*64),('npc','unknown'),('phase','won')):
            state=copy.deepcopy(self.state);state['pfEncounter'][field]=value
            with self.assertRaises(ValueError):pf_encounters.validate_restored(state)

    def dying_opponent(self):
        self.enter()
        with patch('game_randomness.draw',side_effect=[20,1]):engine.apply_action(self.state,{'type':'choose_pf_encounter','choice':'combat'},self.me)
        self.state['characters'][1]['hp']=-3;self.state['characters'][1]['stable']=False

    def test_first_aid_uses_prepared_skill_standard_action_and_never_heals_hp(self):
        self.dying_opponent();baseline=copy.deepcopy(self.state)
        for die in range(1,21):
            state=copy.deepcopy(baseline)
            with patch('game_randomness.draw',side_effect=AssertionError('Physical aid rolled')):
                engine.apply_action(state,{'type':'pf_first_aid','physical':die},self.me)
            success=die+1>=15
            self.assertEqual(state['characters'][1]['hp'],-3)
            self.assertEqual(state['characters'][1]['stable'],success)
            self.assertTrue(state['board']['spent'][self.actor]['standard'])
            self.assertEqual(state['pfEncounter']['phase'],'resolved' if success else 'combat')
            self.assertEqual(state['characters'][0]['hp'],16)
            pf_encounters.validate_restored(state)

    def test_aid_requirements_reject_before_dice_and_failed_attempt_can_be_retried_next_turn(self):
        self.dying_opponent()
        for bad in (True,0,21,None):
            before=copy.deepcopy(self.state)
            with patch('game_randomness.draw',side_effect=AssertionError('Invalid aid rolled')):
                with self.assertRaises(ValueError):engine.apply_action(self.state,{'type':'pf_first_aid','physical':bad},self.me)
            self.assertEqual(self.state,before)
        engine.apply_action(self.state,{'type':'pf_first_aid','physical':1},self.me)
        with self.assertRaises(ValueError):engine.apply_action(self.state,{'type':'pf_first_aid','physical':20},self.me)
        with patch('game_randomness.draw',return_value=1):engine.apply_action(self.state,{'type':'turn'},self.me)
        self.assertEqual(self.state['characters'][1]['hp'],-4)
        engine.apply_action(self.state,{'type':'pf_first_aid','physical':20},self.me)
        self.assertTrue(self.state['characters'][1]['stable']);self.assertEqual(self.state['characters'][1]['hp'],-4)

    def test_disabled_helper_pays_the_existing_standard_action_hp_cost(self):
        self.dying_opponent();self.state['characters'][0]['hp']=0
        with patch('game_randomness.draw',return_value=20):engine.apply_action(self.state,{'type':'pf_first_aid','physical':20},self.me)
        self.assertEqual(self.state['characters'][0]['hp'],-1)
        self.assertTrue(self.state['characters'][0]['stable'])
        self.assertTrue(self.state['characters'][1]['stable'])
        self.assertEqual(self.state['pfEncounter']['phase'],'defeated')

    def test_owner_can_use_virtual_aid_but_physical_results_follow_pf_host_permission(self):
        self.dying_opponent();player=self.me|{'host':False}
        with self.assertRaises(PermissionError):engine.apply_action(self.state,{'type':'pf_first_aid','physical':20},player)
        with patch('game_randomness.draw',return_value=20):engine.apply_action(self.state,{'type':'pf_first_aid'},player)
        self.assertEqual(self.state['pfEncounter']['outcome']['status'],'stable')

    def test_wait_automates_stabilization_until_stable_or_actual_death(self):
        self.dying_opponent();baseline=copy.deepcopy(self.state)
        for die,expected,calls,hp in ((20,'stable',1,-3),(1,'dead',9,-12)):
            state=copy.deepcopy(baseline)
            with patch('game_randomness.draw',return_value=die) as rng:engine.apply_action(state,{'type':'pf_wait_stabilization'},self.me)
            self.assertEqual(rng.call_count,calls)
            self.assertEqual(state['pfEncounter']['outcome']['status'],expected)
            self.assertEqual(state['characters'][1]['hp'],hp);self.assertFalse(state['board']['active'])
            self.assertEqual(state['characters'][0]['hp'],16);pf_encounters.validate_restored(state)

    def test_zero_hp_is_not_death_or_unconscious_victory_and_bad_outcomes_reject(self):
        self.dying_opponent();self.state['characters'][1]['hp']=0
        pf_encounters.sync_outcome(self.state)
        self.assertTrue(self.state['board']['active']);self.assertEqual(self.state['pfEncounter']['phase'],'combat')
        self.state['characters'][1]['hp']=-3
        engine.apply_action(self.state,{'type':'pf_first_aid','physical':20},self.me)
        for field,value in (('hp',0),('status','dead'),('stable',False),('constitution',1),('round',True)):
            state=copy.deepcopy(self.state);state['pfEncounter']['outcome'][field]=value
            with self.assertRaises(ValueError):pf_encounters.validate_restored(state)

    def test_unconscious_player_gets_no_chosen_actions_only_real_stabilization_and_defeat(self):
        self.dying_opponent();self.state['characters'][1]['hp']=7;self.state['characters'][0]['hp']=-1
        baseline=copy.deepcopy(self.state)
        for die,status,calls,hp in ((20,'unconscious',1,-1),(1,'dead',13,-14)):
            state=copy.deepcopy(baseline)
            with patch('game_randomness.draw',return_value=die) as rng:self.assertTrue(pf_encounters.resolve_defeat(state))
            self.assertEqual(rng.call_count,calls);self.assertEqual(state['characters'][0]['hp'],hp)
            self.assertEqual(state['characters'][1]['hp'],7);self.assertFalse(state['board']['active'])
            self.assertEqual(state['pfEncounter']['phase'],'defeated');self.assertEqual(state['pfEncounter']['outcome']['status'],status)
            pf_encounters.validate_restored(state)

    def test_both_fallen_resolve_both_health_states_without_healing_or_lost_dying_npc(self):
        self.dying_opponent();self.state['characters'][0]['hp']=-1
        with patch('game_randomness.draw',return_value=20) as rng:pf_encounters.resolve_defeat(self.state)
        self.assertEqual(rng.call_count,2)
        self.assertEqual([c['hp'] for c in self.state['characters']],[-1,-3])
        self.assertTrue(all(c['stable'] for c in self.state['characters']));pf_encounters.validate_restored(self.state)
        self.assertTrue(all(c['recoveryCare']['assisted'] is False for c in self.state['characters']))
        self.state['pfEncounter']['outcome']['npcStable']=False
        with self.assertRaises(ValueError):pf_encounters.validate_restored(self.state)

    def test_npc_attack_ends_defeat_without_advancing_after_the_recorded_outcome(self):
        self.enter()
        with patch('game_randomness.draw',side_effect=[20,1]):
            engine.apply_action(self.state,{'type':'choose_pf_encounter','choice':'combat'},self.me)
        self.state['characters'][0]['hp']=1
        with patch('game_randomness.draw',side_effect=lambda sides:20 if sides==20 else sides):
            engine.apply_action(self.state,{'type':'turn'},self.me)
        record=self.state['pfEncounter']
        self.assertEqual(record['phase'],'defeated');self.assertFalse(self.state['board']['active'])
        self.assertEqual(record['outcome']['round'],self.state['board']['round'])
        self.assertNotIn('autoPaused',self.state['board'])
        self.assertNotIn('termina su turno',self.state['messages'][-1]['text'])
        pf_encounters.validate_restored(self.state)

    def test_new_injury_clears_previous_episode_care_and_first_aid_records_actual_help(self):
        self.dying_opponent()
        engine.apply_action(self.state,{'type':'pf_first_aid','physical':20},self.me)
        patient=self.state['characters'][1]
        self.assertTrue(patient['recoveryCare']['assisted'])
        engine.apply_action(self.state,{'type':'manual','character':patient['id'],'hpDelta':-1,
            'reason':'Nueva herida del fixture','resolution':'Nuevo episodio','reference':'Prueba'},self.me)
        self.assertNotIn('recoveryCare',patient);self.assertFalse(patient['stable'])

    def test_awakened_negative_hp_helper_loses_one_hp_not_a_reset_to_minus_one(self):
        import pf_recovery
        self.dying_opponent();actor=self.state['characters'][0];actor['hp']=-1
        pf_recovery.record_stabilization(actor,assisted=False,round_number=1);pf_recovery.apply_hour(actor,20)
        with patch('game_randomness.draw',return_value=20):engine.apply_action(self.state,{'type':'pf_first_aid','physical':20},self.me)
        actor,patient=self.state['characters']
        self.assertEqual(actor['hp'],-2);self.assertEqual(patient['hp'],-3)
        self.assertNotIn('recoveryState',actor);self.assertFalse(actor['recoveryCare']['assisted'])
        self.assertTrue(patient['recoveryCare']['assisted'])
        self.assertEqual(self.state['pfEncounter']['phase'],'defeated')
        pf_recovery.validate_restored(self.state);pf_encounters.validate_restored(self.state)

    def recovery_scene(self):
        engine.apply_action(self.state,{'type':'enter_pf_encounter','encounter':pf_encounters.ID,
            'encounterVersion':'1.1.0','character':self.actor},self.me)
        with patch('game_randomness.draw',side_effect=[20,1]):
            engine.apply_action(self.state,{'type':'choose_pf_encounter','choice':'combat'},self.me)
        self.state['characters'][0]['hp']=-1

    def test_new_scene_resolves_hours_without_player_administration_and_keeps_real_wounds(self):
        import pf_recovery
        self.recovery_scene()
        with patch('game_randomness.draw',side_effect=[20,1,20]) as rng:self.assertTrue(pf_encounters.resolve_defeat(self.state))
        self.assertEqual(rng.call_count,3);actor,npc=self.state['characters']
        self.assertEqual((actor['hp'],npc['hp']),(-2,7));self.assertTrue(pf_recovery.is_conscious(actor))
        record=self.state['pfEncounter'];self.assertEqual(record['outcome']['hp'],-1)
        self.assertEqual(record['recoveryOutcome']['dice'],[1,20]);self.assertEqual(record['recoveryOutcome']['seconds'],7200)
        self.assertIn('2 hora',self.state['worldTime']);self.assertFalse(self.state['board']['active'])
        pf_encounters.validate_restored(self.state);pf_recovery.validate_restored(self.state)
        with patch('game_randomness.draw',side_effect=AssertionError('Recovery repeated')):
            self.assertFalse(pf_encounters.resolve_recovery(self.state))
        for field,value in (('hours',True),('seconds',3600),('hp',0),('status','dead'),('assisted',True),('dice',[1,20,20])):
            forged=copy.deepcopy(self.state);forged['pfEncounter']['recoveryOutcome'][field]=value
            with self.assertRaises(ValueError):pf_encounters.validate_restored(forged)

    def test_unaided_recovery_can_kill_and_does_not_invent_a_rescue(self):
        self.recovery_scene()
        with patch('game_randomness.draw',side_effect=[20]+[1]*13) as rng:pf_encounters.resolve_defeat(self.state)
        self.assertEqual(rng.call_count,14)
        self.assertEqual(self.state['characters'][0]['hp'],-14)
        receipt=self.state['pfEncounter']['recoveryOutcome'];self.assertEqual(receipt['status'],'dead')
        self.assertEqual(receipt['hours'],13);self.assertEqual(receipt['seconds'],46800)
        audits=[m for m in self.state['messages'] if m.get('recoveryChecks')]
        self.assertEqual(len(audits),1);self.assertEqual(len(audits[0]['recoveryChecks']),13)
        self.assertNotIn('recoveryState',self.state['characters'][0]);pf_encounters.validate_restored(self.state)

    def test_multiple_fallen_and_legacy_scene_do_not_skip_unimplemented_hourly_events(self):
        self.recovery_scene();self.state['characters'][1]['hp']=-3
        with patch('game_randomness.draw',return_value=20) as rng:pf_encounters.resolve_defeat(self.state)
        self.assertEqual(rng.call_count,2);self.assertNotIn('recoveryOutcome',self.state['pfEncounter'])
        pf_encounters.validate_restored(self.state)
        self.setUp();self.dying_opponent();self.state['characters'][0]['hp']=-1;self.state['characters'][1]['hp']=7
        with patch('game_randomness.draw',return_value=20) as rng:pf_encounters.resolve_defeat(self.state)
        self.assertEqual(rng.call_count,1);self.assertNotIn('recoveryOutcome',self.state['pfEncounter'])
        self.assertEqual(self.state['pfEncounter']['definition']['version'],'1.0.0');pf_encounters.validate_restored(self.state)
