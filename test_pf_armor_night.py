import copy
import unittest
from unittest.mock import patch
import engine
import pf_night_rest as rest
import pf_scene_transition
import test_pf_night_rest
from test_character_builder import choices


class PreparedArmorNightTests(unittest.TestCase):
    act=test_pf_night_rest.PreparedNightRestTests.act
    agree=test_pf_night_rest.PreparedNightRestTests.agree
    wounded_victory=test_pf_night_rest.PreparedNightRestTests.wounded_victory

    def setUp(self):self.prepare('scale')

    def prepare(self,armor):
        self.me={'id':'host','name':'Ana','host':True};self.state=engine.initial_state({})
        selected=choices();selected['armor']=armor
        engine.apply_action(self.state,{'type':'create_character','choices':selected},self.me)
        self.actor=self.state['characters'][0]['id']
        self.act('enter_pf_encounter',encounter='patio-del-peaje',encounterVersion='1.7.0',character=self.actor)

    def test_scale_sleep_is_explicit_and_includes_normal_unassisted_doff_and_don_time(self):
        self.wounded_victory();before=copy.deepcopy(self.state)
        with self.assertRaises(ValueError):self.act('rest_pf_night')
        self.assertEqual(self.state,before)
        with patch('game_randomness.draw',side_effect=AssertionError('Prepared sleep rolled dice')):
            self.act('rest_pf_night',armorPlan='remove-and-reequip')
        receipt=self.state['pfNightRest'];result=receipt['result']
        self.assertEqual(receipt['format'],rest.ARMOR_FORMAT)
        self.assertEqual([p['seconds'] for p in result['phases']],[60,28800,240])
        self.assertEqual(result['seconds'],29100);self.assertEqual(result['healing']['elapsedSeconds'],28800)
        self.assertFalse(result['phases'][1]['armorWorn']);self.assertFalse(result['phases'][2]['hasty'])
        self.assertFalse(result['phases'][0]['assisted']);self.assertFalse(result['phases'][2]['assisted'])
        expected=copy.deepcopy(before['characters']);expected[0]['hp']=14
        self.assertEqual(self.state['characters'],expected)
        self.assertEqual(self.state['board'],before['board']);self.assertEqual(self.state['pfEncounter'],before['pfEncounter'])
        self.assertIn('8 horas y 5 minutos',self.state['worldTime']);rest.validate_restored(self.state)
        self.act('continue_pf_encounter');rest.validate_restored(self.state);pf_scene_transition.validate_restored(self.state)
        self.assertEqual(self.state['characters'][0]['ac'],before['characters'][0]['ac'])

    def test_light_armor_can_stay_on_or_be_removed_using_verified_one_minute_times(self):
        for armor in ('leather','studded','chainshirt'):
            for plan,seconds in (('keep',28800),('remove-and-reequip',28920)):
                self.prepare(armor);self.agree();before=copy.deepcopy(self.state['characters'])
                self.act('rest_pf_night',armorPlan=plan)
                result=self.state['pfNightRest']['result']
                self.assertEqual(result['seconds'],seconds);self.assertEqual(result['healing']['amount'],0)
                self.assertEqual(self.state['characters'],before);rest.validate_restored(self.state)

    def test_import_rejects_hasty_helped_missing_or_forged_preparation_and_old_format(self):
        self.agree();self.act('rest_pf_night',armorPlan='remove-and-reequip');baseline=copy.deepcopy(self.state)
        for change in ('haste','help','duration','sleep-armor','plan','format','phase-removed'):
            altered=copy.deepcopy(baseline);record=altered['pfNightRest']
            if change=='haste':record['result']['phases'][2]['hasty']=True
            elif change=='help':record['result']['phases'][0]['assisted']=True
            elif change=='duration':record['result']['seconds']=28800
            elif change=='sleep-armor':record['result']['phases'][1]['armorWorn']=True
            elif change=='plan':record['start']['armorPlan']='keep'
            elif change=='format':record['format']=rest.FORMAT
            else:record['result']['phases'].pop()
            with self.subTest(change=change),self.assertRaises(ValueError):rest.validate_restored(altered)
        self.assertEqual(self.state,baseline)

    def test_preparation_does_not_bypass_owner_medical_or_pending_guards(self):
        self.agree();baseline=copy.deepcopy(self.state)
        for case in ('owner','patient','condition','pending','hours','helper','hasty'):
            self.state=copy.deepcopy(baseline);body={'type':'rest_pf_night','armorPlan':'remove-and-reequip'};me=self.me
            if case=='owner':me={**me,'id':'other'}
            elif case=='patient':self.state['characters'][1]['hp']=-1
            elif case=='condition':self.state['characters'][0]['conditions']='Fatigado'
            elif case=='pending':self.state['pending']=[{'reason':'Sin resolver'}]
            elif case=='hours':body['hours']=9
            elif case=='helper':body['assisted']=True
            else:body['hasty']=True
            before=copy.deepcopy(self.state)
            with self.subTest(case=case),self.assertRaises(PermissionError if case=='owner' else ValueError):rest.rest(self.state,body,me)
            self.assertEqual(self.state,before)

    def test_provider_gets_consequences_not_step_by_step_preparation(self):
        import claude_dm
        self.agree();self.act('rest_pf_night',armorPlan='remove-and-reequip')
        context=claude_dm.build_context(self.state,'Consulta los hechos',[])
        self.assertNotIn('phases',context['state']['nightRestResult'])
        self.assertEqual(context['state']['nightRestResult']['seconds'],29100)
        self.assertEqual(context['state']['nightRestResult']['armorPlan'],'remove-and-reequip')

    def test_valid_receipt_from_different_armor_cannot_be_rebound_to_this_character(self):
        import hashlib
        self.agree();self.act('rest_pf_night',armorPlan='remove-and-reequip');scale=copy.deepcopy(self.state)
        self.prepare('leather');self.agree();self.act('rest_pf_night',armorPlan='remove-and-reequip')
        receipt=copy.deepcopy(self.state['pfNightRest'])
        receipt['character']=scale['characters'][0]['id'];receipt['npc']=scale['characters'][1]['id']
        scale['pfNightRest']=receipt
        scale['messages'][-1]['nightRestSha256']=hashlib.sha256(rest.canonical(receipt).encode()).hexdigest()
        with self.assertRaises(ValueError):rest.validate_restored(scale)
