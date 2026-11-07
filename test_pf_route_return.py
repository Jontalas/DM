import copy
import json
import unittest
from unittest.mock import patch
import engine
import adventure_routes
import pf_night_rest
import pf_scene_transition
from test_character_builder import choices
import test_pf_courtyard_route


class CourtyardReturnTests(unittest.TestCase):
    search=test_pf_courtyard_route.PreparedCourtyardRouteTests.search
    travel=test_pf_courtyard_route.PreparedCourtyardRouteTests.travel
    validate=test_pf_courtyard_route.PreparedCourtyardRouteTests.validate

    def setUp(self):
        self.me={'id':'host','name':'Ana','host':True};self.state=engine.initial_state({})
        engine.apply_action(self.state,{'type':'create_character','choices':choices()},self.me)
        self.actor=self.state['characters'][0]['id']
        engine.apply_action(self.state,{'type':'enter_pf_encounter','encounter':'patio-del-peaje',
            'encounterVersion':'1.6.0','character':self.actor},self.me)
        engine.apply_action(self.state,{'type':'choose_pf_encounter','choice':'parley'},self.me)

    def begin(self,sleep=False):
        if sleep:engine.apply_action(self.state,{'type':'rest_pf_night'},self.me)
        engine.apply_action(self.state,{'type':'continue_pf_encounter'},self.me)
        self.search('registro');self.search('recibo')

    def test_can_leave_without_finishing_then_return_and_keep_goal_after_finishing(self):
        self.begin();before=copy.deepcopy(self.state)
        with patch('game_randomness.draw',side_effect=AssertionError('Return route rolled dice')):
            self.travel('almacen');self.search('bulto');self.travel('patio')
            self.assertFalse(adventure_routes.public_view(self.state)['completed'])
            self.travel('almacen');self.assertEqual(len(self.state['moduleProgress']['discoveries']),1)
            self.search('recepcion');self.assertTrue(adventure_routes.public_view(self.state)['completed'])
            self.travel('patio');self.assertTrue(adventure_routes.public_view(self.state)['completed'])
            self.assertTrue(self.state['moduleProgress']['completed'])
            self.travel('cobertizo');self.assertTrue(adventure_routes.public_view(self.state)['completed'])
            self.assertFalse(self.state['moduleProgress']['completed']);self.search('marca')
            self.travel('almacen');self.assertTrue(adventure_routes.public_view(self.state)['completed'])
        self.assertEqual(len(self.state['moduleProgress']['discoveries']),2)
        self.assertEqual(sum(m.get('adventureComplete',False) for m in self.state['messages']),1)
        self.assertEqual(self.state['characters'][1]['sceneId'],'patio')
        self.assertEqual([c['hp'] for c in self.state['characters']],[16,7])
        for key in ('tokens','worldTime','pfEncounter'):self.assertEqual(self.state[key],before[key])
        self.validate()

    def test_sleep_receipt_positions_and_global_result_survive_repeated_visits_and_copy(self):
        self.begin(sleep=True);clock=self.state['worldTime']
        engine.apply_action(self.state,{'type':'move','character':self.actor,'path':[[0,1]],'acknowledge':True},self.me)
        self.travel('almacen');self.search('bulto');self.search('recepcion')
        self.travel('patio');self.assertEqual(self.state['characters'][0]['y'],1)
        self.assertEqual(self.state['worldTime'],clock);self.assertTrue(adventure_routes.public_view(self.state)['completed'])
        restored=json.loads(json.dumps(self.state));pf_night_rest.validate_restored(restored)
        pf_scene_transition.validate_restored(restored);adventure_routes.validate_restored(restored)
        self.assertEqual(restored,self.state)
        before=copy.deepcopy(self.state)
        with self.assertRaises(ValueError):engine.apply_action(self.state,{'type':'rest_pf_night'},self.me)
        self.assertEqual(self.state,before)

    def test_return_never_skips_a_remote_patient_or_accepts_a_substituted_global_goal(self):
        self.begin();self.travel('almacen');self.search('bulto');self.search('recepcion')
        altered=copy.deepcopy(self.state);altered['adventureRoute']['completion']={'scene':'patio','requires':['recibo']}
        with self.assertRaises(ValueError):pf_scene_transition.validate_restored(altered)
        self.state['characters'][1]['hp']=-1;before=copy.deepcopy(self.state)
        with patch('game_randomness.draw',side_effect=AssertionError('Invalid return rolled dice')):
            with self.assertRaises(ValueError):self.travel('patio')
        self.assertEqual(self.state,before)
