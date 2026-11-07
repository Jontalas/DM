import copy
import unittest
import board_scenes as scenes
import engine
import combat
import tactics
from unittest.mock import patch


class BoardSceneTests(unittest.TestCase):
    def setUp(self):
        self.state=engine.initial_state({});self.state['location']='Patio'
        self.state['characters']=[{'id':'player','enemy':False,'hp':10,'abilities':[10]*6,'x':0,'y':0},
            {'id':'guard','enemy':True,'hp':7,'abilities':[10]*6,'x':1,'y':0}]
        self.state['board']['combatSerial']=4

    def test_old_campaign_keeps_every_character_present_without_mutation(self):
        before=copy.deepcopy(self.state)
        self.assertEqual(scenes.characters(self.state),self.state['characters'])
        self.assertTrue(all(scenes.present(self.state,c) for c in self.state['characters']))
        scenes.validate_restored(self.state);self.assertEqual(self.state,before)

    def test_entry_into_scene_scope_does_not_move_heal_or_reset_combat_epoch(self):
        before=copy.deepcopy(self.state);scenes.initialize(self.state,'patio')
        for c,old in zip(self.state['characters'],before['characters']):self.assertEqual({k:v for k,v in c.items() if k!='sceneId'},old)
        for key in ('board','location','worldTime'):self.assertEqual(self.state[key],before[key])
        scenes.validate_restored(self.state)

    def test_player_changes_scene_guard_stays_and_return_restores_positions_and_terrain(self):
        scenes.initialize(self.state,'patio');self.state['board']['terrain']={'2,2':'wall'}
        self.state['characters'][0]['x']=3
        scenes.move_player(self.state,'almacen','player','Almacén')
        player,guard=self.state['characters']
        self.assertEqual((player['sceneId'],player['x'],player['y']),('almacen',0,0))
        self.assertEqual((guard['sceneId'],guard['x'],guard['y']),('patio',1,0))
        self.assertEqual([c['id'] for c in scenes.characters(self.state)],['player'])
        self.assertEqual(self.state['board']['terrain'],{});self.assertEqual(self.state['board']['combatSerial'],4)
        with self.assertRaises(ValueError):scenes.require_present(self.state,guard)
        self.state['board']['terrain']={'4,4':'difficult'};player['y']=2
        scenes.move_player(self.state,'patio','player','Patio')
        self.assertEqual([c['id'] for c in scenes.characters(self.state)],['player','guard'])
        self.assertEqual(self.state['characters'][0]['x'],3)
        self.assertEqual(self.state['board']['terrain'],{'2,2':'wall'})
        self.assertEqual(self.state['board']['combatSerial'],4)
        scenes.move_player(self.state,'almacen','player','Almacén')
        self.assertEqual(self.state['characters'][0]['y'],2)
        self.assertEqual(self.state['board']['terrain'],{'4,4':'difficult'})
        self.assertEqual(self.state['worldTime'],'Comienzo de la aventura')

    def test_pending_recovery_or_conditions_reject_transition_atomically(self):
        scenes.initialize(self.state,'patio');baseline=copy.deepcopy(self.state)
        for field,value in (('hp',-1),('conditions','Fatigado')):
            self.state=copy.deepcopy(baseline);self.state['characters'][1][field]=value;before=copy.deepcopy(self.state)
            with self.assertRaises(ValueError):scenes.move_player(self.state,'almacen','player','Almacén')
            self.assertEqual(self.state,before)

    def test_import_rejects_unknown_scene_archived_position_mismatch_and_cross_scene_initiative(self):
        scenes.initialize(self.state,'patio');scenes.move_player(self.state,'almacen','player','Almacén')
        bads=[]
        s=copy.deepcopy(self.state);s['characters'][1]['sceneId']='unknown';bads.append(s)
        s=copy.deepcopy(self.state);s['characters'][1]['x']=3;bads.append(s)
        s=copy.deepcopy(self.state);s['boardScenes']['saved']['patio']['positions']['guard']=[True,0];bads.append(s)
        s=copy.deepcopy(self.state);s['board'].update(active=True,order=[{'id':'guard'}],turn=0);bads.append(s)
        s=copy.deepcopy(self.state);s['boardScenes']['saved']['almacen']=copy.deepcopy(s['boardScenes']['saved']['patio']);bads.append(s)
        for state in bads:
            with self.assertRaises(ValueError):scenes.validate_restored(state)

    def test_failed_initialization_or_wrong_destination_name_preserves_original(self):
        self.state['pending']=[{'reason':'Pendiente'}];before=copy.deepcopy(self.state)
        with self.assertRaises(ValueError):scenes.initialize(self.state,'patio')
        self.assertEqual(self.state,before)
        self.state['pending']=[];scenes.initialize(self.state,'patio');scenes.move_player(self.state,'almacen','player','Almacén')
        before=copy.deepcopy(self.state)
        with self.assertRaises(ValueError):scenes.move_player(self.state,'patio','player','Otro patio')
        self.assertEqual(self.state,before)


class ScopedBoardEngineTests(unittest.TestCase):
    def setUp(self):
        self.me={'id':'host','name':'Ana','host':True};self.state=engine.initial_state({'location':'Patio'})
        self.add('Aria',False);self.add('Guardia',True);self.add('Aliada',False)
        self.player,self.guard,self.ally=[c['id'] for c in self.state['characters']]
        scenes.initialize(self.state,'patio');scenes.move_player(self.state,'almacen',self.player,'Almacén')

    def add(self,name,enemy):
        engine.apply_action(self.state,{'type':'character','character':{'name':name,'enemy':enemy,
            'abilities':[14,14,12,10,10,10],'hp':30,'maxHp':30,'ac':16,'attack':4,'damage':'1d6+2',
            'meleeProfile':{'flatAc':14,'criticalMin':19,'multiplier':2}}},self.me)
        return self.state['characters'][-1]

    def test_off_scene_tokens_do_not_block_movement_or_current_terrain(self):
        engine.apply_action(self.state,{'type':'move','character':self.player,'path':[[1,0]],'acknowledge':True},self.me)
        self.assertEqual(self.state['characters'][0]['x'],1)
        self.assertEqual(self.state['characters'][1]['x'],1)
        engine.apply_action(self.state,{'type':'terrain','x':2,'y':0,'terrain':'wall'},self.me)
        self.assertEqual(self.state['board']['terrain']['2,0'],'wall')

    def test_off_scene_actor_cannot_move_or_attack_even_if_controlled_by_host(self):
        before=copy.deepcopy(self.state)
        for body in ({'type':'move','character':self.guard,'path':[[1,1]],'acknowledge':True},
            {'type':'attack','character':self.player,'target':self.guard}):
            with patch('game_randomness.draw',side_effect=AssertionError('Off-scene action rolled')):
                with self.assertRaises(ValueError):engine.apply_action(self.state,body,self.me)
            self.assertEqual(self.state,before)
        self.assertFalse(combat.adjacent(self.state['characters'][0],self.state['characters'][1]))

    def test_only_current_tokens_roll_initiative_and_off_scene_ally_does_not_flank(self):
        enemy=self.add('Adversario del almacén',True)
        self.assertEqual((enemy['sceneId'],enemy['x'],enemy['y']),('almacen',1,0))
        with patch('game_randomness.draw',side_effect=[20,1]) as rng,patch('game_randomness.initiative_tie',return_value=0):
            engine.apply_action(self.state,{'type':'combat'},self.me)
        self.assertEqual(rng.call_count,2)
        self.assertEqual({v['id'] for v in self.state['board']['order']},{self.player,enemy['id']})
        engine.apply_action(self.state,{'type':'attack','character':self.player,'target':enemy['id'],
            'physical':{'attack':[12],'damage':[1]}},self.me)
        result=self.state['messages'][-1]['combat'];self.assertFalse(result['flanking']);self.assertEqual(result['modifier'],4)
        scenes.validate_restored(self.state)

    def test_tactics_never_targets_an_off_scene_player(self):
        enemy=self.add('Adversario del almacén',True);self.state['characters'][0]['hp']=-12
        self.assertEqual(tactics.plan(self.state,enemy),{'path':[],'target':None})
        with self.assertRaises(ValueError):tactics.plan(self.state,self.state['characters'][1])

    def test_off_scene_patient_blocks_new_time_bearing_actions_before_dice(self):
        self.state['characters'][1]['hp']=-1;before=copy.deepcopy(self.state)
        with patch('game_randomness.draw',side_effect=AssertionError('Unresolved remote patient rolled')):
            with self.assertRaises(ValueError):engine.apply_action(self.state,{'type':'combat'},self.me)
        self.assertEqual(self.state,before)

    def test_manual_edit_preserves_scene_and_recovery_copy_scope(self):
        guard=self.state['characters'][1]
        engine.apply_action(self.state,{'type':'character','character':{**guard,'notes':'Nota fuera de escena'}},self.me)
        self.assertEqual(self.state['characters'][1]['sceneId'],'patio');scenes.validate_restored(self.state)
