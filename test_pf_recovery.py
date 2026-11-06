import copy
import unittest
from unittest.mock import patch

import pf_recovery


class HourlyRecoveryTests(unittest.TestCase):
    def patient(self,con=12,hp=-3):
        return {'abilities':[10,10,con,10,10,10],'hp':hp,'stable':True,'conditions':''}

    def test_known_assistance_is_recorded_and_unknown_old_states_stay_unknown(self):
        for assisted in (False,True):
            patient=self.patient();patient['stable']=False
            pf_recovery.record_stabilization(patient,assisted=assisted,round_number=3)
            self.assertEqual(patient['recoveryCare']['assisted'],assisted)
            pf_recovery.validate_restored({'characters':[patient]})
        old=self.patient();pf_recovery.validate_restored({'characters':[old]})
        self.assertNotIn('recoveryCare',old)

    def test_forged_care_or_incompatible_patient_cannot_be_imported(self):
        patient=self.patient();pf_recovery.record_stabilization(patient,assisted=True,round_number=1)
        for changes in ({'assisted':1},{'round':True},{'format':'unknown'},{'extra':True}):
            changed=copy.deepcopy(patient);changed['recoveryCare'].update(changes)
            with self.assertRaises(ValueError):pf_recovery.validate_restored({'characters':[changed]})
        for changes in ({'hp':1},{'stable':False},{'hp':-12}):
            with self.assertRaises(ValueError):pf_recovery.validate_restored({'characters':[patient|changes]})

    def test_all_dice_use_constitution_penalty_and_only_natural_twenty_is_automatic(self):
        for con in (2,3,10,12,14,30,60):
            for hp in range(-con+1,0):
                for raw in range(1,21):
                    for assisted in (False,True):
                        patient=self.patient(con,hp);before=copy.deepcopy(patient)
                        result=pf_recovery.consciousness_check(patient,raw,assisted=assisted)
                        expected=raw==20 or raw+(con-10)//2+hp>=10
                        self.assertEqual(result['success'],expected)
                        self.assertEqual(result['hpAfter'],hp-int(not assisted and not expected))
                        self.assertEqual(result['conscious'],expected)
                        self.assertEqual(result['dead'],result['hpAfter']<=-con)
                        self.assertEqual(result['elapsedSeconds'],3600)
                        self.assertEqual(patient,before)

    def test_assistance_failure_preserves_hp_and_unaided_failure_can_kill(self):
        patient=self.patient(12,-11)
        aided=pf_recovery.consciousness_check(patient,1,assisted=True)
        self.assertEqual(aided['hpAfter'],-11);self.assertFalse(aided['dead'])
        unaided=pf_recovery.consciousness_check(patient,1,assisted=False)
        self.assertEqual(unaided['hpAfter'],-12);self.assertTrue(unaided['dead'])

    def test_success_returns_consciousness_without_healing_and_natural_one_can_succeed(self):
        result=pf_recovery.consciousness_check(self.patient(12,-11),20,assisted=False)
        self.assertTrue(result['conscious']);self.assertEqual(result['hpAfter'],-11)
        result=pf_recovery.consciousness_check(self.patient(60,-1),1,assisted=True)
        self.assertTrue(result['success']);self.assertFalse(result['naturalSuccess'])

    def test_unknown_care_invalid_dice_and_non_eligible_patients_reject_without_mutation(self):
        for raw,care in ((True,True),(0,True),(21,False),(10,None),(10,1)):
            with self.assertRaises(ValueError):pf_recovery.consciousness_check(self.patient(),raw,assisted=care)
        for changes in ({'hp':0},{'hp':-12},{'hp':True},{'stable':False},
                        {'conscious':True},{'conditions':'sangrado'},{'abilities':[10,10,True,10,10,10]}):
            patient=self.patient()|changes;before=copy.deepcopy(patient)
            with self.assertRaises(ValueError):pf_recovery.consciousness_check(patient,20,assisted=False)
            self.assertEqual(patient,before)

    def test_hour_preserves_episode_and_records_consciousness_separately_without_healing(self):
        patient=self.patient();pf_recovery.record_stabilization(patient,assisted=False,round_number=2)
        result=pf_recovery.apply_hour(patient,1)
        self.assertEqual(patient['hp'],-4);self.assertFalse(result['conscious'])
        self.assertEqual(patient['recoveryState']['hours'],1)
        result=pf_recovery.apply_hour(patient,20)
        self.assertEqual(patient['hp'],-4);self.assertTrue(pf_recovery.is_conscious(patient))
        self.assertEqual(patient['recoveryState']['hours'],2)
        pf_recovery.validate_restored({'characters':[copy.deepcopy(patient)]})
        before=copy.deepcopy(patient)
        with self.assertRaises(ValueError):pf_recovery.apply_hour(patient,20)
        self.assertEqual(patient,before)
        for changes in ({'conscious':False},{'hours':True},{'format':'unknown'}):
            forged=copy.deepcopy(patient);forged['recoveryState'].update(changes)
            with self.assertRaises(ValueError):pf_recovery.validate_restored({'characters':[forged]})

    def test_hour_requires_known_care_and_cleans_the_episode_on_actual_death(self):
        with self.assertRaises(ValueError):pf_recovery.apply_hour(self.patient(),20)
        patient=self.patient(12,-11);pf_recovery.record_stabilization(patient,assisted=False,round_number=1)
        result=pf_recovery.apply_hour(patient,1)
        self.assertTrue(result['dead']);self.assertEqual(patient['hp'],-12)
        self.assertNotIn('recoveryCare',patient);self.assertNotIn('recoveryState',patient)
        pf_recovery.validate_restored({'characters':[patient]})

    def test_recovered_negative_hp_character_can_move_or_attack_but_not_both(self):
        import engine
        import combat
        me={'id':'host','name':'Ana','host':True};state=engine.initial_state({})
        for name,enemy in (('Aria',False),('Adversario',True)):
            engine.apply_action(state,{'type':'character','character':{'name':name,'enemy':enemy,
                'maxHp':20,'abilities':[14,14,12,10,10,10],'attack':5,'damage':'1d6',
                'meleeProfile':{'flatAc':10,'criticalMin':20,'multiplier':2}}},me)
        with patch('game_randomness.draw',side_effect=[20,1]):engine.apply_action(state,{'type':'combat'},me)
        actor,target=state['characters'];state['board'].update(turn=0,order=[{'id':c['id'],'roll':10,'modifier':0} for c in (actor,target)])
        actor['hp']=-1;pf_recovery.record_stabilization(actor,assisted=False,round_number=1)
        pf_recovery.apply_hour(actor,20);self.assertEqual(combat.health_status(actor),'incapacitado')
        before=copy.deepcopy(state)
        engine.apply_action(state,{'type':'move','character':actor['id'],'path':[[0,1]],'acknowledge':True},me)
        self.assertEqual(actor['hp'],-1);self.assertTrue(actor['recoveryState']['conscious'])
        with self.assertRaises(ValueError):engine.apply_action(state,{'type':'attack','character':actor['id'],'target':target['id']},me)
        actor,target=before['characters']
        engine.apply_action(before,{'type':'attack','character':actor['id'],'target':target['id'],
            'physical':{'attack':[20],'confirmation':[20],'damage':[1,1]}},me)
        self.assertEqual(actor['hp'],-2);self.assertFalse(actor['stable'])
        self.assertNotIn('recoveryState',actor);self.assertNotIn('recoveryCare',actor)
        self.assertFalse(combat.standing(actor));self.assertEqual(combat.health_status(actor),'moribundo')
