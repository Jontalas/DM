import copy
import json
import unittest
from unittest.mock import patch
import adventure
import adventure_routes as routes
import adventure_modules as modules
import claude_dm
from engine import initial_state,apply_action
from server import queue_investigation
from test_adventure import memory
from test_character_builder import choices

HOST={'id':'host','name':'Ana','host':True}


class RouteTests(unittest.TestCase):
    def state(self):
        state=initial_state({})
        apply_action(state,{'type':'create_character','choices':choices()},HOST)
        routes.install(state,routes.builtin());adventure.apply_memory(state,memory(),starting=True)
        return state

    def search(self,state):
        queue_investigation(state,{'character':state['characters'][0]['id'],'opportunity':'referencia'},HOST)
        apply_action(state,{'type':'check','request':state['pending'][-1]['check']['id'],'method':'take20'},HOST)

    def test_alternative_routes_revisits_and_final_are_deterministic(self):
        for branch in ['catalogo','estantes']:
            state=self.state();sheet=copy.deepcopy(state['characters'])
            with patch('engine.secrets.randbelow',side_effect=AssertionError('No dice on travel or take20')):
                routes.travel(state,{'exit':branch},HOST)
                self.assertEqual([e['id'] for e in routes.public_view(state)['exits']],['volver'])
                self.search(state)
                self.assertFalse(state['messages'][-1]['adventureComplete'])
                self.assertFalse(routes.public_view(state)['completed'])
                routes.travel(state,{'exit':'volver'},HOST)
                routes.travel(state,{'exit':branch},HOST)
                self.assertEqual(state['moduleProgress']['attempts'],{'referencia':1})
                self.assertEqual(state['moduleProgress']['searchActions'],20)
                self.assertEqual(state['objectives'],[])
                routes.travel(state,{'exit':'lectura'},HOST);self.search(state)
            self.assertTrue(routes.public_view(state)['completed'])
            self.assertTrue(state['messages'][-1]['adventureComplete'])
            self.assertEqual(state['scene'],5);self.assertEqual(state['tokens'],0)
            self.assertEqual(sheet,state['characters'])
            restored=json.loads(json.dumps(state));routes.validate_restored(restored);modules.validate_restored(restored)
            self.assertEqual(restored,state)

    def test_private_future_scenes_never_enter_public_or_rules_context(self):
        state=self.state();secret='PRIVATE-FUTURE'
        state['adventureRoute']['scenes'][1]['module']['preparation']=secret
        context=claude_dm.build_context(state,'Hola',[])
        self.assertNotIn(secret,json.dumps(context))
        self.assertNotIn('adventureRoute',context['state'])
        self.assertNotIn('routeProgress',context['state'])
        self.assertNotIn('adventureRouteView',claude_dm.build_context(state,'Consulta',[],rules=True)['state'])

    def test_guards_precede_all_state_changes(self):
        state=self.state()
        for changes,body,me,error in [
            ({},{'exit':'inexistente'},HOST,ValueError),
            ({},{'exit':'catalogo'},{'id':'guest','host':False},PermissionError),
            ({'pending':[{'reason':'Pendiente'}]},{'exit':'catalogo'},HOST,ValueError),
            ({'board':{**state['board'],'active':True}},{'exit':'catalogo'},HOST,ValueError),
        ]:
            probe={**copy.deepcopy(state),**changes};before=copy.deepcopy(probe)
            with self.assertRaises(error):routes.travel(probe,body,me)
            self.assertEqual(probe,before)
        routes.travel(state,{'exit':'catalogo'},HOST);before=copy.deepcopy(state)
        with self.assertRaises(ValueError):routes.travel(state,{'exit':'lectura'},HOST)
        self.assertEqual(state,before)

    def test_invalid_graph_and_unreachable_exit_dc_are_rejected_before_install(self):
        original=routes.builtin();state=initial_state({})
        apply_action(state,{'type':'create_character','choices':choices()},HOST)
        for change in ['unknown','duplicate','isolated','no-final','bad-prerequisite','dc']:
            route=copy.deepcopy(original)
            if change=='unknown':route['scenes'][0]['exits'][0]['to']='unknown'
            elif change=='duplicate':route['scenes'].append(copy.deepcopy(route['scenes'][0]))
            elif change=='isolated':route['scenes'][0]['exits']=route['scenes'][0]['exits'][:1]
            elif change=='no-final':route['scenes'][-1]['exits']=[{'id':'volver','label':'Volver','to':'entrada','requires':[]}]
            elif change=='bad-prerequisite':route['scenes'][1]['exits'][1]['requires']=['invented']
            else:route['scenes'][1]['module']['opportunities'][0]['dc']=40
            before=copy.deepcopy(state)
            with self.assertRaises(ValueError):routes.install(state,route)
            self.assertEqual(state,before)
        route=copy.deepcopy(original)
        module=route['scenes'][1]['module']
        module['opportunities'].append({**module['opportunities'][0],'id':'optional','dc':40})
        route['scenes'][1]['exits'][1]['requires']=['optional']
        with self.assertRaises(ValueError):routes.install(state,route)
        state['characters'].append(copy.deepcopy(state['characters'][0]))
        before=copy.deepcopy(state)
        with self.assertRaises(ValueError):routes.install(state,original)
        self.assertEqual(state,before)

    def test_restore_rejects_changed_active_scene_missing_progress_and_forged_transitions(self):
        state=self.state();routes.travel(state,{'exit':'catalogo'},HOST)
        for change in ['module','saved','path','progress','scene-number']:
            probe=copy.deepcopy(state)
            if change=='module':probe['adventureModule']['title']='Forged'
            elif change=='saved':probe['routeProgress']['saved']={}
            elif change=='path':probe['routeProgress']['history']=['entrada','lectura','catalogo']
            elif change=='progress':probe['routeProgress']['saved']['entrada']['completed']=True
            else:probe['scene']=1
            with self.assertRaises(ValueError):routes.validate_restored(probe)

