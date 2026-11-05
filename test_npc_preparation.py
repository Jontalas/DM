import copy
import unittest
from engine import initial_state,apply_action
import npc_catalog

HOST={'id':'host','name':'Ana','host':True}
GUEST={'id':'guest','name':'Luis','host':False}


class NpcPreparationTests(unittest.TestCase):
    def setUp(self):self.state=initial_state({})
    def prepare(self,**extra):apply_action(self.state,{'type':'create_npc','template':'pf1-goblin-warrior-1',**extra},HOST)

    def test_source_template_creates_director_controlled_actor_without_manual_stats(self):
        self.prepare(name='Vigía');actor=self.state['characters'][0]
        self.assertEqual((actor['name'],actor['owner'],actor['enemy'],actor['hp']),('Vigía','director',True,7))
        self.assertFalse(actor['npcCreation']['manualOverride']);self.assertEqual(actor['meleeProfile']['criticalMin'],19)
        npc_catalog.validate_restored(self.state)
        self.assertEqual(self.state['messages'][-1]['refs'],[{'book':'bestiario','page':167}])

    def test_permissions_raw_stats_wrong_system_and_active_combat_reject_without_mutation(self):
        before=copy.deepcopy(self.state)
        with self.assertRaises(PermissionError):apply_action(self.state,{'type':'create_npc','template':'pf1-goblin-warrior-1'},GUEST)
        with self.assertRaises(ValueError):self.prepare(attack=999)
        self.assertEqual(before,self.state)
        self.state['ruleset']='cairn-1e'
        with self.assertRaises(ValueError):self.prepare()
        self.state.pop('ruleset');self.state['board']['active']=True
        with self.assertRaises(ValueError):self.prepare()

    def test_copy_verifies_template_but_accepts_combat_hp_changes(self):
        self.prepare();changed=copy.deepcopy(self.state);changed['characters'][0]['hp']=-2
        npc_catalog.validate_restored(changed)
        for update in [{'ac':99},{'level':True},{'owner':'host'},{'enemy':False},{'hp':8}]:
            changed=copy.deepcopy(self.state);changed['characters'][0].update(update)
            with self.assertRaises(ValueError):npc_catalog.validate_restored(changed)

    def test_manual_correction_is_explicit_and_cannot_transfer_npc_to_player(self):
        self.prepare();actor=self.state['characters'][0]
        apply_action(self.state,{'type':'character','character':actor|{'ac':17}},HOST)
        current=self.state['characters'][0];self.assertTrue(current['npcCreation']['manualOverride'])
        npc_catalog.validate_restored(self.state);before=copy.deepcopy(self.state)
        for update in [{'owner':'host'},{'enemy':False},{'hp':9999}]:
            with self.assertRaises(ValueError):apply_action(self.state,{'type':'character','character':current|update},HOST)
            self.assertEqual(self.state,before)

    def test_placement_is_free_and_never_overwrites_previous_actor(self):
        self.state['board']['terrain']['0,0']='wall';self.prepare();self.prepare()
        a,b=self.state['characters'];self.assertNotEqual((a['x'],a['y']),(b['x'],b['y']))
        self.assertNotEqual((a['x'],a['y']),(0,0));self.assertNotEqual(a['id'],b['id'])
        npc_catalog.validate_restored(self.state)

    def test_director_receives_current_stats_without_repeated_source_audit(self):
        import json
        from claude_dm import build_context
        self.prepare();self.state['characters'][0]['npcCreation']['sources'][0]['edition']='AUDIT-ONLY-SOURCE'
        context=build_context(self.state,'Situación del encuentro',[])
        self.assertEqual(context['state']['characters'][0]['hp'],7)
        self.assertNotIn('npcCreation',context['state']['characters'][0])
        self.assertNotIn('AUDIT-ONLY-SOURCE',json.dumps(context))

    def test_export_carries_complete_source_notices_without_changing_campaign(self):
        self.assertEqual(npc_catalog.export_notices(self.state),{})
        self.prepare();before=copy.deepcopy(self.state);notices=npc_catalog.export_notices(self.state)
        for name in ('OGL-1.0a-Bestiary.txt','OGL-1.0a-Core-Rulebook.txt'):
            self.assertIn('OPEN GAME LICENSE Version 1.0a',notices[name]);self.assertIn('15. COPYRIGHT NOTICE',notices[name])
        self.assertIn('Pathfinder RPG Bestiary',notices['OGL-1.0a-Bestiary.txt'])
        self.assertIn('Pathfinder Roleplaying Game Core Rulebook',notices['OGL-1.0a-Core-Rulebook.txt'])
        notices.clear();self.assertTrue(npc_catalog.export_notices(self.state));self.assertEqual(self.state,before)
