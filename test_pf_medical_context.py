import copy
import json
import unittest
import claude_dm
import engine
import legacy_director_attempt as legacy
import pf_recovery
import pf_rest
import test_pf_medical_evolution as clinical_fixture


class MedicalContextTests(unittest.TestCase):
    def setUp(self):
        self.patient=clinical_fixture.MedicalEvolutionTests().patient(hp=-59,con=60)
        for _ in range(10):pf_rest.apply_night_healing(self.patient,elapsed_seconds=28800)
        self.state=engine.initial_state({});self.state['characters']=[self.patient];self.state['board']['combatSerial']=1

    def test_provider_gets_awareness_summary_while_capture_and_campaign_keep_full_proof(self):
        before=copy.deepcopy(self.state);prepared=legacy.prepare(self.state,'Consulto el estado.',[])
        sent=prepared['request']['context']['state']['characters'][0]['recoveryState']
        self.assertEqual(sent,{'format':'cronicas-pf-medical-context-1','hours':1,'conscious':False})
        full=prepared['captureRequest']['context']['state']['characters'][0]['recoveryState']
        self.assertEqual(full,self.patient['recoveryState']);self.assertEqual(legacy.capture_input(prepared),prepared['captureRequest'])
        self.assertGreater(len(json.dumps(full))-len(json.dumps(sent)),5000);self.assertEqual(self.state,before)

    def test_forged_projection_or_private_proof_is_rejected_before_reservation(self):
        prepared=legacy.prepare(self.state,'Consulto el estado.',[])
        projection=copy.deepcopy(prepared);projection['request']['context']['state']['characters'][0]['recoveryState']['conscious']=True
        private=copy.deepcopy(prepared);private['captureRequest']['context']['state']['characters'][0]['recoveryState']['change']['result']['amount']=99
        for changed in (projection,private):
            with self.assertRaises(ValueError):legacy.capture_input(changed)

    def test_context_summary_is_not_an_importable_medical_proof(self):
        projected=claude_dm.build_context(self.state,'Consulto el estado.',[])['state']
        with self.assertRaises(ValueError):pf_recovery.validate_restored(projected)
        pf_recovery.validate_restored(self.state)
