import copy
import unittest
from unittest.mock import patch
import engine
import rulesets
import server
from test_support import TestStore


class RulesetIdentityTests(unittest.TestCase):
    def test_only_implemented_systems_are_selectable(self):
        self.assertEqual([v['id'] for v in rulesets.catalog()],['pathfinder-1e'])
        self.assertEqual(rulesets.new_campaign({})['ruleset'],'pathfinder-1e')
        for invalid in ['cairn-1e','pathfinder-2e',None,{}]:
            with patch('engine.initial_state') as initial:
                with self.assertRaises(ValueError):rulesets.new_campaign({'ruleset':invalid})
                initial.assert_not_called()

    def test_legacy_identity_is_explicit_without_recalculating_or_writing_on_read(self):
        store=TestStore();legacy=engine.initial_state({});legacy['notes']='Existing campaign'
        token=store.create('Legacy',legacy,'Ana');me=store.identity(token)
        before=copy.deepcopy(store.campaigns[me['campaign']])
        with patch.object(server,'STORE',store):row,state=server.load(me['campaign'])
        self.assertEqual(state['ruleset'],'pathfinder-1e');self.assertEqual(state['notes'],'Existing campaign')
        self.assertEqual(store.campaigns[me['campaign']],before)

    def test_catalog_descriptors_cannot_be_mutated_by_callers(self):
        value=rulesets.require();value['coverage'].append('Invented coverage')
        self.assertNotIn('Invented coverage',rulesets.require()['coverage'])
        state={'ruleset':'cairn-1e','characters':[]};before=copy.deepcopy(state)
        with self.assertRaises(ValueError):rulesets.identify(state)
        self.assertEqual(state,before)
