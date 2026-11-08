import copy
import unittest
from unittest.mock import patch
import engine
import pf_ceasefire
import pf_encounters
import pf_scene_transition
from test_character_builder import choices


class PreparedCeasefireTests(unittest.TestCase):
    def setUp(self):
        self.me={'id':'host','name':'Ana','host':True}
        self.state=engine.initial_state({})
        selected=choices()
        selected['abilities'][3]=12
        selected['abilities'][4]=10
        selected['languages']=['Goblin']
        selected['skills'].append('swim')
        self.act('create_character',choices=selected)
        self.actor,self.npc=self.state['characters'][0]['id'],None
        self.act('enter_pf_encounter',encounter=pf_encounters.ID,encounterVersion='1.8.0',character=self.actor)
        self.npc=self.state['characters'][1]['id']

    def act(self,kind,**body):engine.apply_action(self.state,{'type':kind,**body},self.me)

    def wound_guard(self):
        with patch('game_randomness.draw',side_effect=[20,1]),patch('game_randomness.initiative_tie',return_value=0):
            self.act('choose_pf_encounter',choice='combat')
        with patch('game_randomness.draw',side_effect=[12,1]):
            self.act('attack',character=self.actor,target=self.npc)
        self.assertEqual(self.state['characters'][1]['hp'],2)

    def test_accepting_preserves_health_positions_actions_and_route_copy(self):
        self.wound_guard();before=copy.deepcopy(self.state)
        self.assertIsNone(pf_ceasefire.limitation(self.state))
        with patch('game_randomness.draw',side_effect=AssertionError('Speech rolled')):
            self.act('accept_pf_ceasefire')
        self.assertEqual(self.state['characters'],before['characters'])
        self.assertEqual(self.state['worldTime'],before['worldTime'])
        self.assertEqual(self.state['board']['spent'],before['board']['spent'])
        self.assertFalse(self.state['board']['active'])
        self.assertEqual(self.state['pfEncounter']['phase'],'agreement')
        pf_encounters.validate_restored(self.state)
        self.act('continue_pf_encounter')
        pf_encounters.validate_restored(self.state);pf_scene_transition.validate_restored(self.state)

    def test_owner_duplicate_and_unsupported_conditions_do_not_mutate(self):
        self.wound_guard();baseline=copy.deepcopy(self.state)
        for case in ('owner','healthy','language','condition','second-combat','out-of-turn','pending','extra'):
            self.state=copy.deepcopy(baseline);me=self.me;body={'type':'accept_pf_ceasefire'}
            if case=='owner':me={**me,'id':'other'}
            elif case=='healthy':self.state['characters'][1]['hp']=7
            elif case=='language':self.state['characters'][0]['creation']['choices']['languages']=[]
            elif case=='condition':self.state['characters'][0]['conditions']='Fatigado'
            elif case=='second-combat':self.state['board']['combatSerial']=2
            elif case=='out-of-turn':self.state['board']['turn']=1
            elif case=='pending':self.state['pending']=[{'reason':'Pendiente'}]
            else:body['heal']=True
            before=copy.deepcopy(self.state)
            with self.subTest(case=case),self.assertRaises(PermissionError if case=='owner' else ValueError):
                pf_ceasefire.accept(self.state,body,me)
            self.assertEqual(self.state,before)
        self.state=copy.deepcopy(baseline);self.act('accept_pf_ceasefire');before=copy.deepcopy(self.state)
        with self.assertRaises(ValueError):self.act('accept_pf_ceasefire')
        self.assertEqual(self.state,before)

    def test_brief_acceptance_at_zero_hp_is_free_and_does_not_trigger_exertion_damage(self):
        self.wound_guard()
        for _ in range(4):
            with patch('game_randomness.draw',side_effect=[19,1,4]):self.act('turn')
        self.assertEqual(self.state['characters'][0]['hp'],0)
        self.assertEqual(self.state['characters'][1]['hp'],2)
        before=copy.deepcopy(self.state['characters'])
        self.act('accept_pf_ceasefire')
        self.assertEqual(self.state['characters'],before)
        self.assertEqual(self.state['pfEncounter']['ceasefire']['actorHp'],0)
        pf_encounters.validate_restored(self.state)
        with self.assertRaises(ValueError):self.act('continue_pf_encounter')

    def test_receipt_and_marker_cannot_be_forged_removed_or_transferred_to_old_scene(self):
        self.wound_guard();self.act('accept_pf_ceasefire');baseline=copy.deepcopy(self.state)
        for case in ('hp','round','serial','character','missing','marker','old','encounter'):
            altered=copy.deepcopy(baseline);record=altered['pfEncounter'];proof=record['ceasefire']
            if case=='hp':proof['npcHp']=7
            elif case=='round':proof['round']=0
            elif case=='serial':proof['combatSerial']=True
            elif case=='character':proof['character']='other'
            elif case=='missing':del record['ceasefire']
            elif case=='marker':altered['messages'][-1]['ceasefireSha256']='0'*64
            elif case=='old':record['definition']=pf_encounters.definition('1.7.0')
            else:altered['pfEncounter']=None
            with self.subTest(case=case),self.assertRaises(ValueError):pf_encounters.validate_restored(altered)
        self.assertEqual(self.state,baseline)
