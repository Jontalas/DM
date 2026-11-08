import copy
import unittest
import pf_npc_aid as aid


class NPCFirstAidEpisodeTests(unittest.TestCase):
    def start(self,*,initiative='npc',spent=True,hp=-1):
        return {'epoch':1,'round':1,'initiative':initiative,'order':['pc','npc'],
            'patient':{'id':'pc','hp':hp,'constitution':14,'x':0,'y':0},
            'helper':{'id':'npc','hp':6,'heal':-1,'x':1,'y':0},
            'spent':{'pc':{'standard':True},'npc':{'standard':spent}}}

    def test_npc_cannot_aid_twice_in_attack_turn_pc_checks_first_then_npc_aids(self):
        start=self.start();before=copy.deepcopy(start);dice=iter([1,20]);kinds=[]
        result=aid.simulate(start,lambda kind:kinds.append(kind) or next(dice))
        self.assertEqual(kinds,['stabilization','first-aid']);self.assertEqual(result['patient']['hp'],-2)
        self.assertTrue(result['assisted']);self.assertEqual(result['round'],2);self.assertEqual(result['initiative'],'npc')
        self.assertEqual(result['patient']['recoveryCare'],{'format':'cronicas-pf-care-3','assisted':True,'round':2,'initiative':'npc','order':['pc','npc'],'epoch':1})
        self.assertTrue(result['spent']['npc']['standard']);self.assertEqual(start,before)

    def test_free_current_npc_standard_can_aid_without_skipping_or_repeating_any_pc_turn(self):
        start=self.start(spent=False);kinds=[];result=aid.simulate(start,lambda kind:kinds.append(kind) or 20)
        self.assertEqual(kinds,['first-aid']);self.assertEqual(result['patient']['hp'],-1);self.assertEqual(result['round'],1);self.assertEqual(result['begunTurns'],[])
        start=self.start(initiative='pc');result=aid.simulate(start,lambda kind:20)
        self.assertEqual(result['rolls'],[['first-aid',20]]);self.assertEqual(result['begunTurns'],['npc'])

    def test_natural_stabilization_before_npc_turn_records_no_assistance_or_extra_roll(self):
        kinds=[];result=aid.simulate(self.start(),lambda kind:kinds.append(kind) or 20)
        self.assertEqual(kinds,['stabilization']);self.assertFalse(result['assisted']);self.assertEqual(result['patient']['hp'],-1)
        self.assertEqual(result['patient']['recoveryCare']['initiative'],'pc');self.assertEqual(result['initiative'],'pc')

    def test_failed_aid_does_not_wound_patient_and_death_stops_before_another_npc_action(self):
        start=self.start(spent=False,hp=-13);kinds=[]
        result=aid.simulate(start,lambda kind:kinds.append(kind) or 1)
        self.assertEqual(kinds,['first-aid','stabilization']);self.assertEqual(result['patient']['hp'],-14);self.assertNotIn('recoveryCare',result['patient'])
        self.assertFalse(result['audit'][0]['check']['success']);self.assertEqual(result['audit'][1]['hpBefore'],-13)

    def test_unsupported_start_rejects_before_dice_and_input_never_changes(self):
        baseline=self.start()
        for case in ('helper-zero','distance','late','epoch','budget','dead'):
            start=copy.deepcopy(baseline)
            if case=='helper-zero':start['helper']['hp']=0
            elif case=='distance':start['helper']['x']=2
            elif case=='late':start['round']=551
            elif case=='epoch':start['epoch']=2
            elif case=='budget':start['spent']['npc']['unknown']=True
            else:start['patient']['hp']=-14
            before=copy.deepcopy(start)
            with self.subTest(case=case),self.assertRaises(ValueError):aid.simulate(start,lambda kind:self.fail('Invalid aid rolled'))
            self.assertEqual(start,before)
