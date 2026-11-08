import copy
import base64
import io
import json
import unittest
from unittest.mock import patch
import adventure_routes
import board_scenes
import claude_dm
import engine
import legacy_director_attempt as legacy
import rule_preparation_attempt as attempts
import test_adventure_routes as fixture
from test_support import TestStore


class ArchivedBoardContextTests(unittest.TestCase):
    me={'id':'host','name':'Ana','host':True}

    def setUp(self):
        self.state=fixture.RouteTests().state();self.actor=self.state['characters'][0]['id']
        board_scenes.initialize(self.state,'entrada')
        self.state['characters'][0].update(x=3,y=2)
        self.terrain={f'{x},{y}':'difficult' for x in range(20) for y in range(20)}
        self.state['board']['terrain']=copy.deepcopy(self.terrain)
        adventure_routes.travel(self.state,{'exit':'catalogo'},self.me)
        board_scenes.validate_restored(self.state);adventure_routes.validate_restored(self.state)

    def test_projection_omits_past_geometry_preserves_positions_and_never_changes_the_campaign(self):
        before=copy.deepcopy(self.state);context=claude_dm.build_context(self.state,'Pregunto por el archivo',[])
        view=context['state']['boardScenes']
        self.assertEqual(view['format'],'cronicas-board-scenes-context-1');self.assertEqual(view['current'],'catalogo')
        self.assertEqual(view['knownScenes']['entrada']['positions'][self.actor],[3,2])
        self.assertNotIn('terrain',view['knownScenes']['entrada']);self.assertNotIn('difficult',json.dumps(view))
        self.assertEqual(context['state']['board'],self.state['board'])
        self.assertLess(len(json.dumps(view)),len(json.dumps(self.state['boardScenes']))//4)
        view['knownScenes']['entrada']['positions'][self.actor][0]=9
        self.assertEqual(self.state,before)
        probe=copy.deepcopy(self.state);probe['boardScenes']=view
        with self.assertRaises(ValueError):board_scenes.validate_restored(probe)

    def test_return_still_restores_every_tile_and_original_position(self):
        claude_dm.build_context(self.state,'Vuelvo a la entrada',[])
        adventure_routes.travel(self.state,{'exit':'volver'},self.me)
        self.assertEqual(self.state['board']['terrain'],self.terrain)
        self.assertEqual([self.state['characters'][0][k] for k in ('x','y')],[3,2])
        board_scenes.validate_restored(self.state);adventure_routes.validate_restored(self.state)

    def test_old_full_context_paid_key_and_capture_are_reused_after_projection(self):
        with patch.object(board_scenes,'director_view',return_value=None):old=legacy.prepare(self.state,'Pregunto por el archivo',[])
        new=legacy.prepare(self.state,'Pregunto por el archivo',[])
        self.assertEqual(old['sha256'],new['sha256'])
        self.assertGreater(len(json.dumps(old['request'])),len(json.dumps(new['request']))+5000)
        store=TestStore();value={'narration':'El archivo permanece en silencio.','proposals':[]}
        with patch.dict('os.environ',{'ANTHROPIC_API_KEY':'fixture-never-sent'}):
            attempts.run(store,'room','host',old,converter=lambda *a,**k:value,restore=legacy.restore)
        cold=TestStore();cold.preparations=copy.deepcopy(store.preparations)
        with patch.dict('os.environ',{'ANTHROPIC_API_KEY':''}):
            result=attempts.run(cold,'room','host',new,converter=lambda *a,**k:self.fail('Projection repeated provider'),restore=legacy.restore)
        self.assertEqual(result,value)

    def test_actual_adapter_sends_only_current_geometry_and_archived_positions(self):
        value={'narration':'La entrada ya visitada sigue al otro lado.','proposals':[]}
        raw=json.dumps({'stop_reason':'end_turn','content':[{'type':'text','text':json.dumps(value)}]}).encode()
        with patch.dict('os.environ',{'ANTHROPIC_API_KEY':'fixture-never-sent'}),patch('urllib.request.urlopen',return_value=io.BytesIO(raw)) as provider:
            self.assertEqual(claude_dm.ai_reply(self.state,'Pregunto por la entrada',[]),value)
        body=json.loads(provider.call_args.args[0].data);context=json.loads(body['messages'][0]['content'])
        self.assertEqual(context['state']['board']['terrain'],{})
        self.assertEqual(context['state']['boardScenes']['knownScenes']['entrada']['positions'][self.actor],[3,2])
        self.assertNotIn('terrain',context['state']['boardScenes']['knownScenes']['entrada'])

    def test_changed_geometry_or_projection_cannot_reuse_the_original_hash(self):
        prepared=legacy.prepare(self.state,'Pregunto por el archivo',[])
        for kind in ('archive','projection'):
            forged=copy.deepcopy(prepared)
            if kind=='archive':forged['captureRequest']['context']['state']['boardScenes']['saved']['entrada']['terrain']['0,0']='wall'
            else:forged['request']['context']['state']['boardScenes']['knownScenes']['entrada']['positions'][self.actor]=[9,9]
            store=TestStore()
            with self.subTest(kind=kind),self.assertRaises(ValueError):
                store.begin_rule_preparation('room',attempts.key('host',prepared['sha256']),'host',forged)
            self.assertEqual(store.preparations,{})

    def test_upgrade_keeps_original_capabilities_and_never_activates_a_future_field(self):
        engine.apply_action(self.state,{'type':'talk','kind':'action','text':'Vuelvo a la entrada','character':self.actor},self.me)
        new=legacy.prepare(self.state,'Vuelvo a la entrada',[])
        original=copy.deepcopy(new['captureRequest']);original['context'].pop('routeTravelActor')
        old={**new,'request':original,'captureRequest':original}
        store=TestStore();identifier=attempts.key('host',old['sha256'])
        store.begin_rule_preparation('room',identifier,'host',old)
        value={'narration':'La entrada está al otro lado.','proposals':[],'routeTravel':{'exit':'volver'}}
        raw=json.dumps({'stop_reason':'end_turn','content':[{'type':'text','text':json.dumps(value)}]}).encode()
        store.save_rule_preparation_response('room',identifier,'host',old['sha256'],attempts.pack(
            {'kind':'raw','value':base64.b64encode(raw).decode(),'latencyMs':0}))
        with self.assertRaisesRegex(ValueError,'route-travel'):
            attempts.run(store,'room','host',new,converter=lambda *a,**k:self.fail('Upgrade repeated provider'),restore=legacy.restore)
        self.assertEqual(self.state['routeProgress']['current'],'catalogo')
