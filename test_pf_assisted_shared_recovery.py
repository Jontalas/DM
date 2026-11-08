import copy
import unittest
import pf_shared_recovery as shared
import test_pf_shared_recovery as original_fixture


class AssistedSharedClockTests(unittest.TestCase):
    def start(self):
        start=original_fixture.SharedRecoveryClockTests().start()
        start['patients'][0]['care']['assisted']=True
        start['patients'][1].update(hp=1,stable=False,care=None)
        return start

    def record(self,start,result):
        pc,npc=start['patients']
        record={'definition':{'recoveryScope':shared.ASSISTED_SCOPE},'phase':'defeated','character':pc['id'],'npc':npc['id'],
            'outcome':{'round':start['round'],'hp':pc['hp'],'constitution':pc['constitution'],'stable':pc['stable'],
                'npcHp':npc['hp'],'npcConstitution':npc['constitution'],'npcStable':npc['stable']},
            'recoveryStart':copy.deepcopy(start),'recoveryOutcome':shared._receipt(start,result,'Inicio verificado',scope=shared.ASSISTED_SCOPE)}
        if result['status']=='rest-boundary':record['recoveryLimit']='shared-rest-boundary'
        return record

    def test_assisted_pc_can_wake_without_healing_npc_actions_or_input_mutation(self):
        start=self.start();before=copy.deepcopy(start);roles=[]
        result=shared.simulate(start,lambda role:roles.append(role) or 20,scope=shared.ASSISTED_SCOPE)
        self.assertEqual(roles,[0]);self.assertEqual(result['status'],'conscious');self.assertEqual(result['seconds'],3600)
        self.assertEqual([p['hp'] for p in result['patients']],[-1,1]);self.assertTrue(result['patients'][0]['recoveryState']['conscious'])
        self.assertTrue(result['patients'][0]['recoveryCare']['assisted']);self.assertEqual(start,before)
        record=self.record(start,result);self.assertEqual(record['recoveryOutcome']['format'],'cronicas-pf-recovery-outcome-3');self.assertTrue(record['recoveryOutcome']['assisted'])
        self.assertEqual(shared.validate_record(record),result)

    def test_six_failed_assisted_checks_stop_before_unknown_rest_without_hp_loss(self):
        start=self.start();result=shared.simulate(start,lambda role:1,scope=shared.ASSISTED_SCOPE)
        self.assertEqual(result['status'],'rest-boundary');self.assertEqual(result['seconds'],21600);self.assertEqual(result['hours'],6)
        self.assertEqual(result['patients'][0]['hp'],-1);self.assertFalse(result['patients'][0]['recoveryState']['conscious'])
        self.assertEqual(result['rolls'],[[0,1]]*6);shared.validate_record(self.record(start,result))

    def test_assisted_player_scope_cannot_downgrade_receipt_or_modify_assistance(self):
        start=self.start();result=shared.simulate(start,lambda role:20,scope=shared.ASSISTED_SCOPE);record=self.record(start,result)
        for case in ('format','assisted','old-scope','extra-die'):
            bad=copy.deepcopy(record)
            if case=='format':bad['recoveryOutcome']['format']='cronicas-pf-recovery-outcome-2'
            elif case=='assisted':bad['recoveryOutcome']['assisted']=False
            elif case=='old-scope':bad['definition']['recoveryScope']=shared.SCOPE
            else:bad['recoveryOutcome']['rolls'].append([0,20])
            with self.subTest(case=case),self.assertRaises(ValueError):shared.validate_record(bad)

    def test_old_scope_still_rejects_assisted_pc_and_same_instant_npc_event_is_not_lost(self):
        start=self.start()
        with self.assertRaises(shared.CoverageLimit):shared.simulate(start,lambda role:self.fail('Old scope rolled'))
        start=original_fixture.SharedRecoveryClockTests().start(npc_help=True,simultaneous=True);start['patients'][0]['care']['assisted']=True
        dice=iter([20,1]);result=shared.simulate(start,lambda role:next(dice),scope=shared.ASSISTED_SCOPE)
        self.assertEqual(result['rolls'],[[0,20],[1,1]]);self.assertEqual(result['status'],'conscious');self.assertFalse(result['patients'][1]['recoveryState']['conscious'])
        self.assertEqual([p['hp'] for p in result['patients']],[-1,-3])
