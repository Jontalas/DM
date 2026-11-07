"""Global route outcomes survive revisits; no new tabletop rule or provider."""
import copy
import unittest
from unittest.mock import patch
import adventure_routes as routes
from test_adventure_routes import HOST
import test_adventure_routes
from engine import initial_state,apply_action
from test_character_builder import choices


class PersistentRouteOutcomeTests(unittest.TestCase):
    def route(self):
        route=routes.builtin()
        final=route['scenes'][-1]
        route['completion']={'scene':final['id'],'requires':['referencia']}
        final['exits']=[{'id':'volver','label':'Regresar a la entrada','to':route['start'],'requires':['referencia']}]
        return route

    def state(self,route=None):
        state=initial_state({});apply_action(state,{'type':'create_character','choices':choices()},HOST)
        routes.install(state,self.route() if route is None else route)
        import adventure
        from test_adventure import memory
        adventure.apply_memory(state,memory(),starting=True)
        return state

    def search(self,state):test_adventure_routes.RouteTests.search(self,state)

    def test_outcome_is_confirmed_once_and_survives_leaving_and_returning_to_goal_scene(self):
        state=self.state();before=copy.deepcopy(state['characters'])
        with patch('game_randomness.draw',side_effect=AssertionError('Route navigation rolled dice')):
            routes.travel(state,{'exit':'catalogo'},HOST);self.search(state)
            routes.travel(state,{'exit':'lectura'},HOST)
            self.assertFalse(routes.public_view(state)['completed']);self.search(state)
            self.assertTrue(routes.public_view(state)['completed']);self.assertTrue(state['messages'][-1]['adventureComplete'])
            attempts=copy.deepcopy(state['moduleProgress']['attempts'])
            routes.travel(state,{'exit':'volver'},HOST)
            self.assertTrue(routes.public_view(state)['completed'])
            self.assertNotIn('completion',routes.public_view(state))
            routes.travel(state,{'exit':'catalogo'},HOST);routes.travel(state,{'exit':'lectura'},HOST)
            self.assertEqual(state['moduleProgress']['attempts'],attempts)
            self.assertTrue(routes.public_view(state)['completed'])
            routes.validate_restored(state)
        self.assertEqual(state['characters'],before);self.assertEqual(state['tokens'],0)

    def test_completion_schema_rejects_unknown_duplicate_unreachable_or_unachievable_goals_before_install(self):
        source=self.route();state=initial_state({});apply_action(state,{'type':'create_character','choices':choices()},HOST)
        for completion in ({'scene':'unknown','requires':['referencia']},{'scene':'lectura','requires':[]},
            {'scene':'lectura','requires':['invented']},{'scene':'lectura','requires':['referencia','referencia']},
            {'scene':'lectura','requires':[['referencia']]},{'scene':'lectura','requires':['referencia'],'completed':True}):
            route=copy.deepcopy(source);route['completion']=completion;before=copy.deepcopy(state)
            with self.subTest(completion=completion),self.assertRaises(ValueError):routes.install(state,route)
            self.assertEqual(state,before)
        route=copy.deepcopy(source);route['scenes'][-1]['module']['opportunities'][0]['dc']=40
        with self.assertRaises(ValueError):routes.install(state,route)

    def test_completion_cannot_be_spoofed_by_a_scene_complete_boolean_or_foreign_progress(self):
        state=self.state();state['moduleProgress']['completed']=True
        self.assertFalse(routes.public_view(state)['completed'])
        with self.assertRaises(ValueError):routes.validate_restored(state)

    def test_goal_can_precede_optional_local_objective_and_emits_only_one_completion(self):
        route=self.route();final=route['scenes'][-1]['module']
        final['opportunities'].append({'id':'extra','label':'Examinar otra marca','dc':10,
            'discovery':'La marca tiene otra fecha.','failure':'Aún no identificas la fecha.','requires':['referencia']})
        final['objectives'][0]['requires']=['extra']
        state=self.state(route);routes.travel(state,{'exit':'catalogo'},HOST);self.search(state)
        routes.travel(state,{'exit':'lectura'},HOST);self.search(state)
        self.assertFalse(state['moduleProgress']['completed']);self.assertTrue(routes.public_view(state)['completed'])
        from server import queue_investigation
        queue_investigation(state,{'character':state['characters'][0]['id'],'opportunity':'extra'},HOST)
        apply_action(state,{'type':'check','request':state['pending'][-1]['check']['id'],'method':'take20'},HOST)
        self.assertTrue(state['moduleProgress']['completed'])
        self.assertEqual(sum(m.get('adventureComplete',False) for m in state['messages']),1)
