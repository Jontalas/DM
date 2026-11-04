import copy
import json
import unittest
from unittest.mock import Mock
from systems import cairn_1e as rules,cairn_creator as creator,cairn_engine as engine,cairn_adventure as adventure
from test_cairn_creator import draft_with_bonus

HOST={'id':'player','host':True}


def scene(dex=None,plate=False):
    draft=draft_with_bonus(6)
    if dex is not None:draft['core']['DEX']=dex
    choices={'weapons':{'weapons':'Dagger'}}
    if plate:
        draft['gear']['armor']=20;choices['disposition']={'armor:0':'equipped'}
    character=creator.finalize(draft,choices,'player');character['id']='pc'
    state=engine.initial_state({});state['characters']=[character]
    return adventure.apply(state,{'type':'start_cairn_adventure','character':'pc'},HOST)


class CairnAdventureTests(unittest.TestCase):
    def test_zero_protection_from_full_load_does_not_prevent_actions_or_get_healed_while_full(self):
        draft=draft_with_bonus(6);draft['gear']['armor']=20;draft['gear']['helmets--shields']=20
        actor=creator.finalize(draft,{'weapons':{'weapons':'Dagger'},'disposition':{'torch':'stored'}},'player');actor['id']='pc'
        self.assertEqual(actor['inventorySlots'],10);self.assertEqual(actor['hitProtection'],0)
        state=engine.initial_state({});state['characters']=[actor]
        state=adventure.apply(state,{'type':'start_cairn_adventure','character':'pc'},HOST)
        state=adventure.apply(state,{'type':'choose_route','route':'pasarela'},HOST)
        state=adventure.apply(state,{'type':'resolve_save','request':state['adventure']['pending']['id'],'physical':20},HOST,lambda sides:1)
        state=adventure.apply(state,{'type':'rest_and_recover'},HOST)
        self.assertEqual(state['characters'][0]['hitProtection'],0)
        self.assertTrue(adventure.status(state['characters'][0])['canAct'])
        engine.validate_restored(state)

    def test_safe_plan_succeeds_without_save_or_dice_and_preserves_character(self):
        state=scene();before=copy.deepcopy(state['characters'])
        draw=Mock(side_effect=AssertionError('Safe route rolled'))
        changed=adventure.apply(state,{'type':'choose_route','route':'sendero'},HOST,draw)
        self.assertTrue(changed['adventure']['completed']);self.assertEqual(before,changed['characters'])
        draw.assert_not_called();self.assertFalse(state['adventure']['completed'])
        engine.validate_restored(json.loads(json.dumps(changed)))

    def test_failed_save_applies_announced_dex_injury_without_hp_damage_or_critical_save(self):
        state=scene(plate=True)
        pending=adventure.apply(state,{'type':'choose_route','route':'pasarela'},HOST)
        self.assertIn('1d4',pending['messages'][-1]['text'])
        request=pending['adventure']['pending']['id'];draw=Mock(side_effect=[20,4])
        changed=adventure.apply(pending,{'type':'resolve_save','request':request},HOST,draw)
        self.assertEqual([c.args for c in draw.call_args_list],[(20,),(4,)])
        actor=changed['characters'][0]
        self.assertEqual(actor['abilities']['DEX'],0);self.assertEqual(actor['hitProtection'],1)
        self.assertEqual(actor['armor'],3);self.assertFalse(adventure.status(actor)['canAct'])
        self.assertFalse(changed['adventure']['completed']);self.assertIsNone(changed['adventure']['pending'])
        self.assertNotIn('criticalDamage',actor);self.assertNotIn('scars',actor)
        engine.validate_restored(json.loads(json.dumps(changed)))
        with self.assertRaises(ValueError):adventure.apply(changed,{'type':'choose_route','route':'sendero'},HOST)

    def test_healer_week_rest_recovers_then_player_may_choose_safe_alternative(self):
        state=scene();state=adventure.apply(state,{'type':'choose_route','route':'pasarela'},HOST)
        state=adventure.apply(state,{'type':'resolve_save','request':state['adventure']['pending']['id'],'physical':20},HOST,lambda sides:4)
        healed=adventure.apply(state,{'type':'rest_and_recover'},HOST)
        self.assertEqual(healed['characters'][0]['abilities'],healed['characters'][0]['maxAbilities'])
        self.assertEqual(healed['adventure']['elapsedDays'],7)
        self.assertEqual(healed['characters'][0]['gold'],state['characters'][0]['gold'])
        with self.assertRaises(ValueError):adventure.apply(healed,{'type':'rest_and_recover'},HOST)
        done=adventure.apply(healed,{'type':'choose_route','route':'sendero'},HOST)
        restored=engine.import_campaign(json.loads(json.dumps(done)),{'id':'new-host','host':True})
        self.assertEqual(restored['adventure'],done['adventure']);self.assertEqual(restored['characters'][0]['owner'],'new-host')
        self.assertEqual(restored['characters'][0]['abilities'],done['characters'][0]['abilities'])
        engine.validate_restored(restored)

    def test_natural_one_succeeds_without_damage_roll_and_natural_twenty_always_fails(self):
        for raw,dex,damage,success in [(1,[1,1,1],0,True),(20,[6,6,6],1,False)]:
            state=scene(dex);state=adventure.apply(state,{'type':'choose_route','route':'pasarela'},HOST)
            draw=Mock(return_value=damage)
            changed=adventure.apply(state,{'type':'resolve_save','request':state['adventure']['pending']['id'],'physical':raw},HOST,draw)
            self.assertEqual(changed['adventure']['completed'],success)
            self.assertEqual(draw.call_count,0 if success else 1)
            self.assertEqual(changed['characters'][0]['abilities']['DEX'],sum(dex)-damage)

    def test_ownership_pending_integrity_and_invalid_physical_values_precede_rng(self):
        state=scene();state=adventure.apply(state,{'type':'choose_route','route':'pasarela'},HOST)
        before=copy.deepcopy(state);draw=Mock(side_effect=AssertionError('Invalid action consumed dice'))
        request=state['adventure']['pending']['id']
        with self.assertRaises(PermissionError):adventure.apply(state,{'type':'resolve_save','request':request},{'id':'other','host':True},draw)
        for body in [{'type':'resolve_save','request':'wrong'},
                {'type':'resolve_save','request':request,'physical':True},
                {'type':'resolve_save','request':request,'physical':21},
                {'type':'resolve_save','request':request,'dc':1}]:
            with self.assertRaises(ValueError):adventure.apply(state,body,HOST,draw)
        self.assertEqual(state,before);draw.assert_not_called()

    def test_restored_consequences_are_replayed_and_tampering_is_rejected(self):
        state=scene();state=adventure.apply(state,{'type':'choose_route','route':'pasarela'},HOST)
        state=adventure.apply(state,{'type':'resolve_save','request':state['adventure']['pending']['id'],'physical':20},HOST,lambda sides:1)
        for change in ('raw','damage','dex','days','completed','untracked'):
            invalid=copy.deepcopy(state)
            if change=='raw':invalid['adventure']['events'][0]['raw']=1
            elif change=='damage':invalid['adventure']['events'][0]['damage']=5
            elif change=='dex':invalid['characters'][0]['abilities']['DEX']=3
            elif change=='days':invalid['adventure']['elapsedDays']=7
            elif change=='completed':invalid['adventure']['completed']=True
            else:invalid['adventure']=None
            with self.assertRaises(ValueError):engine.validate_restored(invalid)
