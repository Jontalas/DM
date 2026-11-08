import copy
import unittest
import character_builder
import pf_first_aid as aid
import pf_recovery
from test_character_builder import choices


class FirstAidPrimitiveTests(unittest.TestCase):
    def setUp(self):
        self.helper,_=character_builder.build(choices());self.helper.update(id='helper',x=0,y=0,conditions='')
        self.patient={**copy.deepcopy(self.helper),'id':'patient','x':1,'hp':-2,'stable':False}
        self.clock={'round_number':3,'order':['helper','patient'],'epoch':1}

    def test_success_spends_standard_and_records_exact_help_without_healing_or_aliasing(self):
        before=copy.deepcopy((self.helper,self.patient));spent={'move':True}
        result=aid.resolve(self.helper,self.patient,spent,die=20,**self.clock)
        self.assertEqual((self.helper,self.patient),before);self.assertEqual(spent,{'move':True})
        self.assertTrue(result['patient']['stable']);self.assertEqual(result['patient']['hp'],-2)
        self.assertEqual(result['spent'],{'move':True,'standard':True});self.assertEqual(result['helper'],self.helper)
        self.assertEqual(result['patient']['recoveryCare'],{'format':'cronicas-pf-care-3','assisted':True,'round':3,'initiative':'helper','order':['helper','patient'],'epoch':1})
        pf_recovery.validate_restored({'characters':[result['patient']],'board':{'combatSerial':1}})
        result['patient']['abilities'][2]=1;self.assertEqual(self.patient['abilities'][2],14)

    def test_disabled_helper_pays_one_hp_after_success_or_failure_while_patient_never_loses_hp(self):
        self.helper['hp']=0
        for die,success in ((1,False),(20,True)):
            result=aid.resolve(self.helper,self.patient,{},die=die,**self.clock)
            self.assertEqual(result['helper']['hp'],-1);self.assertFalse(result['helper']['stable']);self.assertNotIn('recoveryCare',result['helper'])
            self.assertEqual(result['patient']['hp'],-2);self.assertEqual(result['patient']['stable'],success)
            self.assertEqual(self.helper['hp'],0)
        self.helper['hp']=-1;pf_recovery.record_stabilization(self.helper,assisted=False,round_number=1);pf_recovery.apply_hour(self.helper,20)
        result=aid.resolve(self.helper,self.patient,{},die=20,**self.clock)
        self.assertEqual(result['helper']['hp'],-2);self.assertFalse(result['helper']['stable']);self.assertNotIn('recoveryState',result['helper'])

    def test_unprepared_helper_spent_action_distance_and_unknown_clock_reject_without_mutation(self):
        baseline=copy.deepcopy((self.helper,self.patient,self.clock))
        for case in ('unprepared','spent','disabled-moved','distance','unconscious','stable','clock','condition'):
            self.helper,self.patient,self.clock=copy.deepcopy(baseline);spent={}
            if case=='unprepared':self.helper['skillTotals']=[]
            elif case=='spent':spent['standard']=True
            elif case=='disabled-moved':self.helper['hp']=0;spent['move']=True
            elif case=='distance':self.patient['x']=2
            elif case=='unconscious':self.helper.update(hp=-1,stable=True)
            elif case=='stable':self.patient['stable']=True
            elif case=='clock':self.clock['order']=['helper','helper']
            else:self.patient['conditions']='Sangrado sin resolver'
            before=copy.deepcopy((self.helper,self.patient,spent,self.clock))
            with self.subTest(case=case),self.assertRaises(ValueError):aid.validate(self.helper,self.patient,spent,**self.clock)
            self.assertEqual((self.helper,self.patient,spent,self.clock),before)

    def test_legacy_clock_is_not_promoted_and_skill_natural_twenty_is_not_automatic_success(self):
        self.helper['skillTotals']=[{'name':'Curar','total':-6}]
        result=aid.resolve(self.helper,self.patient,{},die=20,**{**self.clock,'epoch':None})
        self.assertFalse(result['check']['success']);self.assertEqual(result['patient'],self.patient)
        self.helper['skillTotals']=[{'name':'Curar','total':0}]
        result=aid.resolve(self.helper,self.patient,{},die=20,**{**self.clock,'epoch':None})
        self.assertEqual(result['patient']['recoveryCare']['format'],'cronicas-pf-care-2');self.assertNotIn('epoch',result['patient']['recoveryCare'])
