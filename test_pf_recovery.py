import copy
import unittest

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
