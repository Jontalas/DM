import unittest
from unittest.mock import patch
import npc_catalog
import combat
from engine import initial_state,apply_action
from test_character_builder import choices


class NpcCatalogTests(unittest.TestCase):
    def test_printed_goblin_values_include_favored_hp_and_small_weapon(self):
        data,proof=npc_catalog.prepare('pf1-goblin-warrior-1','pathfinder-1e')
        self.assertEqual((data['hp'],data['maxHp'],data['ac'],data['attack'],data['damage'],data['initiative']),(7,7,16,2,'1d4',6))
        self.assertEqual(data['meleeProfile'],{'flatAc':14,'criticalMin':19,'multiplier':2})
        self.assertEqual(data['saves'],[3,2,-1]);self.assertEqual(proof['profile']['touchAc'],13)
        self.assertEqual((proof['sources'][0]['pdfPage'],proof['sources'][0]['printedPage']),(167,166))
        self.assertEqual(proof['license'],'OGL-1.0a');self.assertTrue(proof['coverage']['pending'])

    def test_only_declared_system_and_mode_are_accepted(self):
        for identifier,system,mode in [('missing','pathfinder-1e','basic-melee'),('pf1-goblin-warrior-1','cairn-1e','basic-melee'),
            ('pf1-goblin-warrior-1','pathfinder-1e','ranged')]:
            with self.assertRaises(ValueError):npc_catalog.prepare(identifier,system,mode=mode)

    def test_preparation_does_not_roll_or_mutate_the_cached_catalog(self):
        with patch('secrets.randbelow',side_effect=AssertionError('NPC preparation rolled')):
            data,proof=npc_catalog.prepare('pf1-goblin-warrior-1','pathfinder-1e',name='Vigía')
        data['hp']=999;proof['sources'][0]['pdfPage']=0
        again,original=npc_catalog.prepare('pf1-goblin-warrior-1','pathfinder-1e')
        self.assertEqual(again['hp'],7);self.assertEqual(original['sources'][0]['pdfPage'],167)

    def test_prepared_melee_profile_uses_existing_engine_without_manual_totals(self):
        me={'id':'host','name':'Ana','host':True};state=initial_state({})
        apply_action(state,{'type':'create_character','choices':choices()},me)
        data,_=npc_catalog.prepare('pf1-goblin-warrior-1','pathfinder-1e')
        apply_action(state,{'type':'character','character':data|{'enemy':True}},me)
        hero,goblin=state['characters']
        state['board'].update(active=True,order=[{'id':goblin['id'],'roll':20,'modifier':6},{'id':hero['id'],'roll':1,'modifier':hero['initiative']}],
            turn=0,acted=[goblin['id'],hero['id']],spent={})
        result=combat.attack(state,{'character':goblin['id'],'target':hero['id'],
            'physical':{'attack':[19],'confirmation':[20],'damage':[3,4]}},me,
            lambda sides,physical:physical)
        self.assertTrue(result['critical']);self.assertEqual(result['modifier'],2);self.assertEqual(result['damage'],7)
        self.assertEqual(hero['hp'],hero['maxHp']-7)
