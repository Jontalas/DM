import copy
import json
import unittest
from unittest.mock import Mock,patch
from systems import cairn_1e as rules,cairn_creator as creator
from test_support import make_store


def draft_with_bonus(raw=1,owner='player'):
    count=0
    def draw(sides):
        nonlocal count
        count+=1
        return raw if count==35 else 1
    return creator.begin(owner,'female-names',draw)


class CairnCreatorTests(unittest.TestCase):
    def test_action_boundary_keeps_ownership_server_side_and_prevents_new_rolls_on_resume(self):
        state={'ruleset':rules.ID,'creationDrafts':{}};draw=Mock(return_value=1)
        created=creator.draft_action(state,{'type':'begin_character','nameTable':'male-names'},'p1',draw)
        count=draw.call_count;self.assertGreater(count,0)
        with self.assertRaises(ValueError):creator.draft_action(created,{'type':'begin_character','nameTable':'male-names'},'p1',draw)
        with self.assertRaises(ValueError):creator.draft_action(created,{'type':'choose_bonus','table':'tools','owner':'p1'},'p2',draw)
        with self.assertRaises(ValueError):creator.draft_action(created,{'type':'choose_bonus','table':'tools'},'p2',draw)
        with self.assertRaises(PermissionError):creator.preview_for_actor(created,{},'p2')
        self.assertEqual(draw.call_count,count);self.assertEqual(state,{'ruleset':rules.ID,'creationDrafts':{}})
        chosen=creator.draft_action(created,{'type':'choose_bonus','table':'tools'},'p1',draw)
        self.assertEqual(draw.call_count,count+1)
        with patch('secrets.randbelow',side_effect=AssertionError('Resume rerolled')):
            preview=creator.preview_for_actor(json.loads(json.dumps(chosen)),{'weapons':{'weapons':'Dagger'}},'p1')
        self.assertEqual(preview['owner'],'p1')

    def test_bonus_choice_happens_before_its_roll_and_is_never_repeated(self):
        draft=draft_with_bonus();self.assertIsNone(draft['bonus'])
        draw=Mock(return_value=2)
        with self.assertRaises(PermissionError):creator.choose_bonus(draft,'tools','other',draw)
        with self.assertRaises(ValueError):creator.choose_bonus(draft,'weapons','player',draw)
        draw.assert_not_called()
        changed=creator.choose_bonus(draft,'tools','player',draw)
        self.assertEqual(changed['bonus'],{'table':'tools','raw':2});draw.assert_called_once_with(20)
        self.assertIsNone(draft['bonus'])
        with self.assertRaises(ValueError):creator.choose_bonus(changed,'trinkets','player',draw)
        self.assertEqual(draw.call_count,1)

    def test_automatic_bonus_types_roll_exactly_the_required_die(self):
        expedition=draft_with_bonus(6);book=draft_with_bonus(18)
        self.assertEqual(expedition['bonus'],{'table':'expeditionary-gear','raw':1})
        self.assertEqual(book['bonus'],{'table':'spellbooks-d100','raw':1})
        self.assertEqual(creator.bonus_options(draft_with_bonus(14)),['armor','weapons'])
        self.assertEqual(creator.equipment_options(book)[-1]['options'],['Spellbook: Adhere'])

    def test_preview_rebuilds_from_unchanged_draft_without_rng_or_remote_calls(self):
        draft=creator.choose_bonus(draft_with_bonus(),'tools','player',lambda sides:1)
        before=copy.deepcopy(draft)
        with patch('secrets.randbelow',side_effect=AssertionError('Preview consumed random dice')):
            a=creator.preview(draft,{'weapons':{'weapons':'Dagger'}},'player')
            b=creator.preview(draft,{'weapons':{'weapons':'Staff'},'identity':{'name':20,'background':20}},'player')
            c=creator.preview(json.loads(json.dumps(draft)),{'weapons':{'weapons':'Dagger'}},'player')
        self.assertEqual(a,c);self.assertEqual(draft,before)
        self.assertEqual(a['name'],'Agune Abernathy');self.assertEqual(b['name'],'Yslen Abernathy')
        self.assertEqual(b['background'],'Ranger')
        self.assertEqual(a['creation']['rolls'],b['creation']['rolls'])
        self.assertEqual(a['inventorySlots'],7)
        self.assertFalse(a['creation']['complete']);self.assertEqual(a['creation']['pending'],['adapterIntegration'])

    def test_armor_none_and_combined_helmet_shield_do_not_change_original_choices(self):
        draft=draft_with_bonus(14);draft['gear']['helmets--shields']=20
        draft=creator.choose_bonus(draft,'armor','player',lambda sides:1)
        groups={g['id']:g for g in creator.equipment_options(draft)}
        self.assertEqual(groups['armor']['options'],[]);self.assertEqual(groups['bonus']['options'],[])
        self.assertEqual(groups['helmets--shields']['options'],['Helmet','Shield'])
        preview=creator.preview(draft,{'weapons':{'weapons':'Dagger'},'disposition':{
            'helmets--shields:0':'equipped','helmets--shields:1':'equipped'}},'player')
        self.assertEqual(preview['armor'],2)

    def test_unavailable_choices_permissions_and_tampered_rolls_fail_without_mutation(self):
        draft=draft_with_bonus();before=copy.deepcopy(draft)
        for choices in [{'weapons':{'weapons':'Sword'}},{'STR':18},
                {'identity':{'traits':{}}},{'disposition':{'invented':'carried'}},
                {'weapons':{'bonus':'Dagger'}}]:
            with self.assertRaises(ValueError):creator.preview(draft,choices,'player')
        with self.assertRaises(PermissionError):creator.preview(draft,{},'other')
        self.assertEqual(draft,before)
        changed=copy.deepcopy(draft);changed['core']['HP']=[7]
        with self.assertRaises(ValueError):creator.validate(changed)
        changed=copy.deepcopy(draft);changed['bonus']={'table':'armor','raw':20}
        with self.assertRaises(ValueError):creator.validate(changed)

    def test_persisted_draft_and_completed_preview_roundtrip_through_campaign_store(self):
        store=make_store();draft=draft_with_bonus()
        token=store.create('Experimental Cairn creator',{'ruleset':rules.ID,'draft':draft},'Player')
        me=store.identity(token);row,state=store.load(me['campaign'])
        self.assertEqual(state['draft'],draft)
        state['draft']=creator.choose_bonus(state['draft'],'trinkets','player',lambda sides:20)
        store.commit(me['campaign'],'choose-bonus','player','fingerprint',row['version'],state)
        _,restored=store.load(me['campaign'])
        preview=creator.preview(restored['draft'],{'weapons':{'weapons':'Dagger'}},'player')
        self.assertIn('Whistle',[e['item'] for e in preview['inventory']])
        self.assertTrue(store.completed(me['campaign'],'choose-bonus','player','fingerprint'))
