import copy
import unittest
from unittest.mock import patch

import pf_recovery
import pf_rest


class NaturalNightHealingTests(unittest.TestCase):
    def patient(self,hp=3,level=1,maximum=10):
        return {'id':'patient','hp':hp,'maxHp':maximum,'level':level,'abilities':[10,10,12,10,10,10],'conditions':''}

    def test_one_hp_per_level_capped_at_maximum_without_dice_or_mutation(self):
        for level in (1,7,20,100):
            for hp in (0,3,9,10):
                patient=self.patient(hp,level);before=copy.deepcopy(patient)
                with patch('game_randomness.draw',side_effect=AssertionError('Rest rolled dice')):
                    result=pf_rest.night_healing(patient,elapsed_seconds=28800)
                self.assertEqual(result['hpAfter'],min(10,hp+level));self.assertEqual(result['amount'],min(level,10-hp))
                self.assertEqual(patient,before)

    def test_short_rest_or_significant_interruption_gives_no_hp(self):
        for seconds,interruption,reason in ((0,False,'insufficient-rest'),(28799,False,'insufficient-rest'),(28800,True,'interrupted')):
            result=pf_rest.night_healing(self.patient(),elapsed_seconds=seconds,significant_interruption=interruption)
            self.assertEqual(result['amount'],0);self.assertEqual(result['hpAfter'],3);self.assertEqual(result['reason'],reason)

    def test_assisted_unconscious_patient_can_heal_and_zero_hp_restores_consciousness(self):
        for hp,after,conscious in ((-3,-2,False),(-1,0,True)):
            patient=self.patient(hp);patient['stable']=False
            pf_recovery.record_stabilization(patient,assisted=True,round_number=1)
            result=pf_rest.night_healing(patient,elapsed_seconds=28800)
            self.assertEqual(result['hpAfter'],after);self.assertEqual(result['consciousAfter'],conscious)
        patient=self.patient(-3);pf_recovery.record_stabilization(patient,assisted=True,round_number=1);pf_recovery.apply_hour(patient,20)
        self.assertTrue(pf_rest.night_healing(patient,elapsed_seconds=28800)['consciousAfter'])

    def test_unassisted_negative_hp_needs_daily_rule_even_when_conscious(self):
        for conscious in (False,True):
            patient=self.patient(-3);pf_recovery.record_stabilization(patient,assisted=False,round_number=1)
            if conscious:pf_recovery.apply_hour(patient,20)
            before=copy.deepcopy(patient)
            with self.assertRaises(ValueError):pf_rest.night_healing(patient,elapsed_seconds=28800)
            self.assertEqual(patient,before)

    def test_dead_dying_unknown_help_and_conditions_are_not_silently_cured(self):
        for changes in ({'hp':-12},{'hp':-3,'stable':False},{'hp':-3,'stable':True},{'conditions':'Fatigado'}):
            patient=self.patient()|changes;before=copy.deepcopy(patient)
            with self.assertRaises(ValueError):pf_rest.night_healing(patient,elapsed_seconds=28800)
            self.assertEqual(patient,before)

    def test_invalid_or_multiple_nights_are_not_inferred(self):
        for seconds in (True,-1,28801,None):
            with self.assertRaises(ValueError):pf_rest.night_healing(self.patient(),elapsed_seconds=seconds)
        for changes in ({'level':True},{'maxHp':True},{'hp':True},{'level':0},{'hp':11}):
            with self.assertRaises(ValueError):pf_rest.night_healing(self.patient()|changes,elapsed_seconds=28800)
