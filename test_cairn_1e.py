import copy
import unittest
from systems import cairn_1e as cairn
import rulesets


def rolls():
    return {'STR':[2,4,6],'DEX':[3,3,3],'WIL':[4,4,5],'HP':[4],'gold':[1,2,3],'age':[1,20]}


class CairnCoreTests(unittest.TestCase):
    def test_initial_arithmetic_preserves_raw_rolls_and_is_explicitly_incomplete(self):
        inputs=rolls();core=cairn.core_from_rolls(inputs)
        self.assertEqual(core['abilities'],{'STR':12,'DEX':9,'WIL':13})
        self.assertEqual((core['hitProtection'],core['gold'],core['age']),(4,6,31))
        self.assertFalse(core['creation']['complete'])
        inputs['STR'][0]=6;self.assertEqual(core['creation']['rolls']['STR'],[2,4,6])
        self.assertNotIn('level',core);self.assertNotIn('class',core)
        self.assertEqual([v['id'] for v in rulesets.catalog()],['pathfinder-1e'])

    def test_player_swap_matches_srd_example_and_cannot_repeat_or_change_input(self):
        core=cairn.core_from_rolls(rolls());before=copy.deepcopy(core)
        changed=cairn.swap_initial(core,['STR','DEX'])
        self.assertEqual(changed['abilities'],{'STR':9,'DEX':12,'WIL':13})
        self.assertEqual(core,before)
        with self.assertRaises(ValueError):cairn.swap_initial(changed,['DEX','WIL'])
        core['abilities']['STR']=18
        with self.assertRaises(ValueError):cairn.swap_initial(core,['STR','DEX'])

    def test_every_save_die_at_boundary_and_extreme_scores(self):
        for score in range(0,25):
            core={'ruleset':cairn.ID,'abilities':{'STR':score}}
            for raw in range(1,21):
                result=cairn.save(core,'STR',raw)
                expected=True if raw==1 else False if raw==20 else raw<=score
                self.assertEqual(result['success'],expected,(score,raw))
                self.assertFalse(result['effectApplied'])
        self.assertFalse(cairn.save({'ruleset':cairn.ID,'abilities':{'WIL':30}},'WIL',20)['success'])

    def test_invalid_dice_and_cross_system_data_are_rejected(self):
        for value in [True,0,7,'3',3.5]:
            invalid=rolls();invalid['STR'][0]=value
            with self.assertRaises(ValueError):cairn.core_from_rolls(invalid)
        invalid=rolls();invalid['age']=[20]
        with self.assertRaises(ValueError):cairn.core_from_rolls(invalid)
        with self.assertRaises(ValueError):cairn.save({'ruleset':'pathfinder-1e','abilities':{'STR':12}},'STR',10)
        with self.assertRaises(ValueError):cairn.save({'ruleset':cairn.ID,'abilities':{'STR':True}},'STR',10)
        for value in [None,[],{'ruleset':cairn.ID,'abilities':None}]:
            with self.assertRaises(ValueError):cairn.save(value,'STR',10)
        for pair in [[],['STR','STR'],['str','DEX'],[{},'DEX']]:
            with self.assertRaises(ValueError):cairn.swap_initial(cairn.core_from_rolls(rolls()),pair)
