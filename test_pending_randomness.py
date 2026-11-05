import copy
import unittest
import pending_randomness
import rule_pack_campaign as campaign
from rule_pack_runtime import RulePackError
import test_target_objective_plan as fixture


class PendingRandomnessDescriptorTests(unittest.TestCase):
    def setUp(self):
        example=fixture.TargetObjectivePlanTests();example.setUp();self.me=example.me
        self.state=example.pending();self.pack=campaign.runtime(self.state,self.me['campaign'])
        self.state['narrative']['pending'].pop('randomnessScope',None)
        self.action={'type':'resolve_pack_request','request':self.state['narrative']['pending']['id'],'id':'first','version':10}

    def enable(self):self.state['narrative']['pending']['randomnessScope']=pending_randomness.SCOPE
    def describe(self,state=None,action=None,me=None):
        return pending_randomness.describe(self.state if state is None else state,self.action if action is None else action,self.me if me is None else me,self.pack)

    def test_old_pending_keeps_legacy_reservation(self):
        self.assertIsNone(self.describe())

    def test_ooc_http_version_and_action_id_do_not_change_pending_reservation(self):
        self.enable();expected=self.describe();changed=copy.deepcopy(self.state)
        changed['messages'].append({'kind':'pack-talk','text':'Un mensaje fuera de personaje.'})
        self.assertEqual(self.describe(changed,self.action|{'version':11,'id':'second'}),expected)
        self.assertEqual(set(expected),{'key','fingerprint','version'});self.assertEqual(len(expected['fingerprint']),64)

    def test_mechanical_or_world_changes_cannot_reuse_same_fingerprint(self):
        self.enable();expected=self.describe()
        for transform in [lambda s:s['characters'][0]['sheet']['fields'].update(energy=1),
            lambda s:s['actors'][0]['sheet']['fields'].update(scene='otra'),
            lambda s:s['narrative']['npcs'][0].update(known=False),
            lambda s:s['narrative']['pending'].update(sheetRevision=99),
            lambda s:s['narrative']['objectiveTargets']['routes'][0].update(npc='sombra')]:
            changed=copy.deepcopy(self.state);transform(changed);actual=self.describe(changed)
            self.assertEqual(actual['key'],expected['key']);self.assertNotEqual(actual['fingerprint'],expected['fingerprint'])

    def test_other_owner_request_and_scope_are_rejected(self):
        self.enable()
        with self.assertRaises(PermissionError):self.describe(me=self.me|{'id':'other'})
        with self.assertRaises(RulePackError):self.describe(action=self.action|{'request':'another'})
        self.state['narrative']['pending']['randomnessScope']='invented'
        with self.assertRaises(RulePackError):self.describe()

    def test_physical_choices_change_fingerprint_and_raw_sheets_are_not_returned(self):
        self.enable();expected=self.describe();actual=self.describe(action=self.action|{'physical':{'pool':[3,4]}})
        self.assertEqual(expected['key'],actual['key']);self.assertNotEqual(expected['fingerprint'],actual['fingerprint'])
        self.assertNotIn('fields',str(actual));self.assertNotIn('arda',str(actual))
        with self.assertRaises(RulePackError):self.describe(action=self.action|{'physical':[]})
