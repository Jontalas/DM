"""Replay a captured real conversion of original CC0 rules, without a provider.

The source and candidate are fixtures. These tests verify the source's bounded
arithmetic, not arbitrary rulebooks or semantic fidelity of future conversions.
"""
import unittest
from unittest.mock import patch
import rule_pack_authoring as authoring
from rule_pack_runtime import RulePack,RulePackError
from test_rule_pack_runtime import document


class CapturedOriginalRulePackageTests(unittest.TestCase):
    def test_identity_license_and_source_match_the_supplied_original_fragment(self):
        prepared=authoring.prepare_input(document('live-lantern-source-request'))
        data=document('live-lantern-example')
        self.assertEqual({key:data[key] for key in prepared['request']['identity']},prepared['request']['identity'])
        self.assertEqual(data['license'],prepared['request']['license']);self.assertEqual(data['sources'],prepared['sources'])
        self.assertNotIn('identity',data)

    def test_all_36_dice_pairs_and_three_resource_levels_match_the_source(self):
        pack=RulePack(document('live-lantern-example'))
        self.assertEqual(set(pack.document()['actions']),{'intentar'})
        for first in range(1,7):
            for second in range(1,7):
                sheet,_=pack.create_character('ana')
                self.assertEqual(sheet['fields'],{'energy':3,'total':0,'success':False,'exhausted':False})
                with patch('rule_pack_runtime.secrets.randbelow',side_effect=AssertionError('Captured conversion verification rolled')):
                    for energy in (2,1,0):
                        sheet,trace=pack.execute(sheet,'intentar',{},'ana',physical={'dice':[first,second]})
                        self.assertEqual(sheet['fields'],{'energy':energy,'total':first+second,'success':first+second>=7,'exhausted':energy==0})
                        self.assertEqual(bool(trace['triggers']),energy==0)
                    with self.assertRaises(RulePackError):pack.execute(sheet,'intentar',{},'ana')

    def test_success_is_replaced_after_each_roll_and_cost_always_applies(self):
        pack=RulePack(document('live-lantern-example'));sheet,_=pack.create_character('ana')
        for dice,expected in (([6,6],True),([1,1],False),([3,4],True)):
            sheet,_=pack.execute(sheet,'intentar',{},'ana',physical={'dice':dice})
            self.assertEqual(sheet['fields']['success'],expected)
        self.assertEqual(sheet['fields']['energy'],0);self.assertTrue(sheet['fields']['exhausted'])
