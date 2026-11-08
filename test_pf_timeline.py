import copy
import unittest
import pf_timeline as timeline


class PathfinderTimelineTests(unittest.TestCase):
    def event(self,patient,round_number,index,**extra):
        return {'character':patient,'epoch':1,'round':round_number,'initiative':['pc','npc'][index],'orderIndex':index,**extra}

    def batch(self,events):return timeline.first_batch(events,epoch=1,order=['pc','npc'])

    def test_same_round_different_initiative_is_not_simultaneous(self):
        later=self.event('npc',601,1);earlier=self.event('pc',601,0)
        self.assertEqual(self.batch([later,earlier]),[earlier]);self.assertEqual(self.batch([later,self.event('pc',602,0)]),[later])

    def test_all_exact_ties_survive_without_effect_type_priority_or_shared_payload(self):
        events=[self.event('pc',601,0,kind='check',payload={'raw':[20]}),self.event('npc',601,0,kind='healing'),self.event('npc',602,1)]
        before=copy.deepcopy(events);batch=self.batch(events);self.assertEqual(batch,events[:2]);self.assertEqual(self.batch(list(reversed(events))),list(reversed(events[:2])))
        batch[0]['payload']['raw'].append(1);self.assertEqual(events,before)

    def test_overlapping_effects_are_kept_and_rejected_without_choosing_order(self):
        events=[self.event('pc',4801,0,kind='check'),self.event('pc',4801,0,kind='healing')]
        self.assertEqual(self.batch(events),events)
        with self.assertRaises(timeline.SimultaneousEffects):timeline.require_non_overlapping(self.batch(events))
        timeline.require_non_overlapping([events[0],self.event('npc',4801,0)])

    def test_mixed_epoch_order_and_unknown_instants_fail_before_selecting_a_plausible_event(self):
        valid=self.event('pc',601,0)
        for changed in ({'epoch':2},{'orderIndex':0},{'round':True},{'initiative':'unknown'},{'orderIndex':False}):
            with self.subTest(changed=changed),self.assertRaises(ValueError):self.batch([valid,{**self.event('npc',602,1),**changed}])
        with self.assertRaises(ValueError):timeline.first_batch([valid],epoch=1,order=['pc','pc'])

    def test_elapsed_seconds_requires_equal_counts_and_never_invents_fractional_time(self):
        self.assertEqual(timeline.elapsed_seconds((2,1),(602,1)),3600);self.assertEqual(timeline.elapsed_seconds((2,0),(2,0)),0)
        for start,end in (((2,0),(2,1)),((602,1),(2,1)),((False,0),(2,0))):
            with self.subTest(start=start,end=end),self.assertRaises(ValueError):timeline.elapsed_seconds(start,end)

    def test_no_due_events_does_not_require_an_invented_clock(self):
        self.assertEqual(timeline.first_batch([],epoch=None,order=None),[])
