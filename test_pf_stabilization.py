import copy
import unittest
import pf_stabilization as stabilization
import pf_recovery


class StabilizationPrimitiveTests(unittest.TestCase):
    def setUp(self):
        self.patient={'id':'patient','hp':-13,'abilities':[10,10,14,10,10,10],'stable':False,'conditions':''}
        self.clock={'round_number':2,'order':['helper','patient'],'epoch':1}

    def test_natural_twenty_stabilizes_even_below_dc_without_healing_or_mutation(self):
        before=copy.deepcopy(self.patient)
        result=stabilization.resolve(self.patient,die=20,**self.clock)
        self.assertEqual(result['total'],9);self.assertTrue(result['success']);self.assertEqual(result['hpAfter'],-13)
        self.assertEqual(self.patient,before);self.assertTrue(result['patient']['stable']);self.assertFalse(result['patient']['recoveryCare']['assisted'])
        self.assertEqual(result['patient']['recoveryCare']['initiative'],'patient')
        pf_recovery.validate_restored({'characters':[result['patient']],'board':{'combatSerial':1}})

    def test_failed_check_can_kill_but_natural_one_is_not_an_automatic_failure(self):
        result=stabilization.resolve(self.patient,die=1,**self.clock)
        self.assertEqual(result['hpAfter'],-14);self.assertEqual(result['status'],'muerto');self.assertNotIn('recoveryCare',result['patient'])
        self.patient.update(hp=-1,abilities=[10,10,60,10,10,10])
        result=stabilization.resolve(self.patient,die=1,**self.clock)
        self.assertTrue(result['success']);self.assertEqual(result['patient']['hp'],-1)

    def test_stable_conditions_and_invalid_clock_reject_without_touching_patient(self):
        baseline=copy.deepcopy(self.patient)
        for case in ('stable','condition','clock'):
            self.patient=copy.deepcopy(baseline);clock=copy.deepcopy(self.clock)
            if case=='stable':self.patient['stable']=True
            elif case=='condition':self.patient['conditions']='Daño continuado sin resolver'
            else:clock['order']=['helper']
            before=copy.deepcopy(self.patient)
            with self.subTest(case=case),self.assertRaises(ValueError):stabilization.validate(self.patient,**clock)
            self.assertEqual(self.patient,before)

    def test_legacy_initiative_proof_is_not_given_an_invented_epoch(self):
        result=stabilization.resolve(self.patient,die=20,**{**self.clock,'epoch':None})
        self.assertEqual(result['patient']['recoveryCare']['format'],'cronicas-pf-care-2');self.assertNotIn('epoch',result['patient']['recoveryCare'])
