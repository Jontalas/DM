import copy
import json
import unittest
from unittest.mock import patch
import pf_medical_evolution as evolution
import pf_recovery
import pf_rest


class MedicalEvolutionTests(unittest.TestCase):
    def patient(self,hp=-5,con=12,conscious=False):
        character={'id':'patient','hp':hp,'maxHp':10,'level':1,'abilities':[10,10,con,10,10,10],'conditions':''}
        pf_recovery.record_stabilization(character,assisted=True,round_number=1,initiative='patient',order=['patient'],epoch=1)
        pf_recovery.apply_hour(character,20 if conscious else 1)
        return character

    def validate(self,patient):pf_recovery.validate_restored({'characters':[patient],'board':{'combatSerial':1}})

    def test_natural_healing_keeps_assistance_and_awareness_without_inventing_check_hours(self):
        for conscious in (False,True):
            patient=self.patient(conscious=conscious);care=copy.deepcopy(patient['recoveryCare'])
            with patch('game_randomness.draw',side_effect=AssertionError('Healing rolled dice')):result=pf_rest.apply_night_healing(patient,elapsed_seconds=28800)
            self.assertEqual(patient['hp'],-4);self.assertEqual(patient['recoveryState']['format'],evolution.FORMAT)
            self.assertEqual(patient['recoveryState']['hours'],1);self.assertEqual(patient['recoveryCare'],care)
            self.assertEqual(pf_recovery.is_conscious(patient),conscious);self.assertEqual(patient['recoveryState']['change']['result'],result)
            self.validate(patient);self.validate(json.loads(json.dumps(patient)))

    def test_repeated_healing_replays_bounded_history_and_zero_clears_the_episode(self):
        patient=self.patient(hp=-59,con=60)
        for expected in range(-58,1):
            pf_rest.apply_night_healing(patient,elapsed_seconds=28800);self.assertEqual(patient['hp'],expected);self.validate(patient)
        self.assertTrue(pf_recovery.is_conscious(patient));self.assertNotIn('recoveryState',patient);self.assertNotIn('recoveryCare',patient)

    def test_manual_correction_after_healing_preserves_history_but_not_current_assistance(self):
        patient=self.patient(conscious=True);pf_rest.apply_night_healing(patient,elapsed_seconds=28800)
        pf_recovery.manual_hp_change(patient,1,reason='Corrección excepcional explícita')
        self.assertEqual(patient['hp'],-3);self.assertNotIn('recoveryCare',patient);self.assertTrue(pf_recovery.is_conscious(patient));self.validate(patient)
        proof=patient['recoveryState'];self.assertEqual(proof['change']['kind'],'manual-hp-correction')
        self.assertEqual(proof['previous']['recovery']['change']['kind'],'natural-night-rest')
        with self.assertRaises(ValueError):pf_rest.apply_night_healing(patient,elapsed_seconds=28800)

    def test_later_hourly_check_uses_current_hp_and_preserves_original_care(self):
        patient=self.patient();pf_rest.apply_night_healing(patient,elapsed_seconds=28800)
        result=pf_recovery.apply_hour(patient,20);self.assertEqual(result['hpBefore'],-4);self.assertTrue(result['conscious']);self.assertEqual(patient['recoveryState']['hours'],2);self.validate(patient)

    def test_short_or_interrupted_rest_does_not_mutate_or_create_a_proof(self):
        for options in ({'elapsed_seconds':28799},{'elapsed_seconds':28800,'significant_interruption':True}):
            patient=self.patient();before=copy.deepcopy(patient);self.assertEqual(pf_rest.apply_night_healing(patient,**options)['amount'],0);self.assertEqual(patient,before)

    def test_unverified_previous_check_cannot_be_replaced_with_a_healing_proof(self):
        patient=self.patient();patient.pop('recoveryState');before=copy.deepcopy(patient)
        with self.assertRaises(ValueError):pf_rest.apply_night_healing(patient,elapsed_seconds=28800)
        self.assertEqual(patient,before)

    def test_forged_history_hours_healing_assistance_and_future_epoch_are_rejected(self):
        patient=self.patient();pf_rest.apply_night_healing(patient,elapsed_seconds=28800)
        for case in ('amount','hours','conscious','previous-hp','future','kind','cycle'):
            altered=copy.deepcopy(patient);proof=altered['recoveryState']
            if case=='amount':proof['change']['result']['amount']=2
            elif case=='hours':proof['hours']=8
            elif case=='conscious':proof['conscious']=True
            elif case=='previous-hp':proof['previous']['hp']=altered['hp']
            elif case=='future':proof['previous']['care']['epoch']=2;altered['recoveryCare']['epoch']=2
            elif case=='kind':proof['change']['kind']='unverified'
            elif case=='cycle':proof['previous']['recovery']=proof
            with self.subTest(case=case),self.assertRaises(ValueError):self.validate(altered)

    def test_historical_profile_is_not_recomputed_as_the_current_level(self):
        patient=self.patient();pf_rest.apply_night_healing(patient,elapsed_seconds=28800);patient['level']=2
        self.validate(patient);self.assertEqual(patient['recoveryState']['change']['result']['level'],1)
