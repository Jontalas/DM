import copy
import unittest
from unittest.mock import patch
import engine
import adventure_modules
import adventure_routes
import board_scenes
import pf_encounters
import pf_scene_transition
from test_character_builder import choices


class PreparedCourtyardRouteTests(unittest.TestCase):
    def setUp(self):
        self.me={'id':'host','name':'Ana','host':True};self.state=engine.initial_state({})
        engine.apply_action(self.state,{'type':'create_character','choices':choices()},self.me)
        self.actor=self.state['characters'][0]['id']
        engine.apply_action(self.state,{'type':'enter_pf_encounter','encounter':pf_encounters.ID,
            'encounterVersion':'1.4.0','character':self.actor},self.me)
        engine.apply_action(self.state,{'type':'choose_pf_encounter','choice':'parley'},self.me)
        self.before=copy.deepcopy(self.state)
        engine.apply_action(self.state,{'type':'continue_pf_encounter'},self.me)

    def search(self,key):
        spec=adventure_modules.investigation(self.state,{'character':self.actor,'opportunity':key},self.me)
        engine.apply_action(self.state,{'type':'request_check','character':self.actor,'checkKind':spec['checkKind'],
            'key':spec['key'],'dc':spec['dc'],'reason':spec['reason']},self.me)
        pending=self.state['pending'][-1];pending['investigation']=key
        engine.apply_action(self.state,{'type':'check','request':pending['check']['id'],'method':'take10'},self.me)

    def open_exits(self):
        self.search('registro');self.search('recibo')

    def travel(self,key):
        adventure_routes.travel(self.state,{'type':'travel_scene','exit':key},self.me)

    def validate(self):
        board_scenes.validate_restored(self.state);pf_encounters.validate_restored(self.state)
        adventure_modules.validate_restored(self.state);adventure_routes.validate_restored(self.state)
        pf_scene_transition.validate_restored(self.state)

    def test_route_entry_keeps_original_health_positions_board_and_encounter(self):
        before=self.before;after=self.state
        self.assertEqual([{k:v for k,v in c.items() if k!='sceneId'} for c in after['characters']],before['characters'])
        for key in ('board','worldTime','pfEncounter'):self.assertEqual(after[key],before[key])
        self.assertEqual(after['pfContinuation']['format'],'cronicas-pf-continuation-2')
        self.assertEqual(after['routeProgress']['current'],'patio');self.validate()

    def test_unavailable_exit_and_wrong_owner_fail_without_dice_or_mutation(self):
        before=copy.deepcopy(self.state)
        with patch('game_randomness.draw',side_effect=AssertionError('Locked exit rolled')):
            with self.assertRaises(ValueError):self.travel('almacen')
        self.assertEqual(self.state,before)
        for host in (False,True):
            with self.assertRaises(PermissionError):adventure_modules.investigation(self.state,{'character':self.actor,'opportunity':'registro'},{'id':'other','host':host})
        self.assertEqual(self.state,before)
        self.open_exits();before=copy.deepcopy(self.state)
        for host in (False,True):
            with self.assertRaises(PermissionError):adventure_routes.travel(self.state,{'exit':'almacen'},{'id':'other','host':host})
        self.assertEqual(self.state,before)

    def test_optional_path_return_keeps_guard_in_patio_and_all_confirmed_discoveries(self):
        self.open_exits()
        engine.apply_action(self.state,{'type':'move','character':self.actor,'path':[[0,1]],'acknowledge':True},self.me)
        self.travel('cobertizo');self.assertEqual(self.state['characters'][1]['sceneId'],'patio')
        self.assertEqual([c['id'] for c in board_scenes.characters(self.state)],[self.actor]);self.search('marca')
        self.travel('patio');self.assertEqual(self.state['characters'][0]['y'],1)
        self.assertEqual([v['id'] for v in self.state['moduleProgress']['discoveries']],['registro','recibo'])
        self.assertEqual(self.state['routeProgress']['saved']['cobertizo']['discoveries'][0]['id'],'marca')
        self.assertEqual([c['hp'] for c in self.state['characters']],[16,7]);self.validate()

    def test_both_paths_reach_same_final_facts_without_picking_opening_or_rewards(self):
        baseline=copy.deepcopy(self.state)
        for optional in (False,True):
            self.state=copy.deepcopy(baseline);self.open_exits()
            if optional:self.travel('cobertizo');self.search('marca')
            self.travel('almacen');self.search('bulto');self.search('recepcion')
            self.assertTrue(adventure_routes.public_view(self.state)['completed'])
            self.assertEqual([c['hp'] for c in self.state['characters']],[16,7])
            self.assertEqual(self.state['worldTime'],baseline['worldTime'])
            self.assertEqual(self.state['pfEncounter'],baseline['pfEncounter'])
            self.assertEqual(self.state['characters'][0]['equipment'],baseline['characters'][0]['equipment'])
            self.assertEqual(self.state['characters'][1]['sceneId'],'patio');self.validate()

    def test_copy_rejects_route_changes_moved_guard_and_scene_progress_mismatch(self):
        self.open_exits();self.travel('almacen');bads=[]
        s=copy.deepcopy(self.state);s['characters'][1]['sceneId']='almacen';bads.append(s)
        s=copy.deepcopy(self.state);s['adventureRoute']['title']='Otra ruta';bads.append(s)
        s=copy.deepcopy(self.state);s['pfContinuation']['routeSha256']='0'*64;bads.append(s)
        s=copy.deepcopy(self.state);s['boardScenes']['current']='patio';bads.append(s)
        for state in bads:
            with self.assertRaises(ValueError):pf_scene_transition.validate_restored(state)

    def test_combat_elsewhere_preserves_original_encounter_and_never_pulls_guard_initiative(self):
        self.open_exits();self.travel('almacen');before=copy.deepcopy(self.state['pfEncounter'])
        with patch('game_randomness.draw',return_value=20) as rng,patch('game_randomness.initiative_tie',return_value=0):
            engine.apply_action(self.state,{'type':'combat'},self.me)
        self.assertEqual(rng.call_count,1);self.assertEqual([v['id'] for v in self.state['board']['order']],[self.actor])
        self.assertEqual(self.state['pfEncounter'],before);self.validate()

    def test_remote_patient_blocks_investigation_and_further_travel_atomically(self):
        self.open_exits();self.travel('cobertizo');self.state['characters'][1]['hp']=-1
        before=copy.deepcopy(self.state)
        with self.assertRaises(ValueError):self.search('marca')
        with self.assertRaises(ValueError):self.travel('patio')
        self.assertEqual(self.state,before)

    def test_completed_route_context_distinguishes_visited_places_from_available_exits(self):
        import claude_dm
        self.open_exits();self.travel('cobertizo');self.search('marca');self.travel('patio')
        self.travel('almacen');self.search('bulto');self.search('recepcion')
        before=copy.deepcopy(self.state)
        context=claude_dm.build_context(self.state,'Narra los resultados confirmados',[],check_actors=[self.actor])
        route=context['state']['adventureRouteView']
        self.assertTrue(route['completed']);self.assertEqual(route['exits'],[])
        self.assertEqual([s['id'] for s in route['visitedScenes']],['patio','cobertizo','almacen'])
        with patch('game_randomness.draw',side_effect=AssertionError('Unavailable return rolled dice')):
            for destination in ('patio','cobertizo'):
                with self.assertRaises(ValueError):self.travel(destination)
        self.assertEqual(self.state,before)
