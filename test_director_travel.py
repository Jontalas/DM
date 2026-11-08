import copy
import json
import unittest
from unittest.mock import patch
import claude_dm
import director_travel
import adventure_routes
import engine
import hashlib
import legacy_director_attempt as legacy
from rule_pack_authoring import canonical
import test_adventure_routes as route_tests


class DirectorTravelTests(unittest.TestCase):
    me={'id':'host','name':'Ana','host':True}

    def setUp(self):
        self.state=route_tests.RouteTests().state()
        self.body={'type':'talk','kind':'action','text':'Voy a consultar el catálogo','director':True,'character':self.state['characters'][0]['id']}
        engine.apply_action(self.state,self.body,self.me)

    def parse(self,result,**options):
        raw={'stop_reason':'end_turn','content':[{'type':'text','text':json.dumps(result)}]}
        return claude_dm.parse_response(self.state,json.dumps(raw),**options)

    def test_schema_lists_only_current_exits_and_never_future_places(self):
        schema=claude_dm.response_schema(self.state)
        self.assertEqual(schema['properties']['routeTravel']['properties']['exit']['enum'],['catalogo','estantes'])
        context=claude_dm.build_context(self.state,self.body['text'],[])
        self.assertEqual(context['routeTravelActor'],self.body['character'])
        self.assertNotIn('adventureRoute',context['state'])
        for options in ({'rules':True},{'starting':True}):
            self.assertNotIn('routeTravel',claude_dm.response_schema(self.state,**options)['properties'])
            self.assertNotIn('routeTravelActor',claude_dm.build_context(self.state,'Consulta',[],**options))

    def test_player_declared_travel_reuses_engine_without_dice_or_other_state_changes(self):
        before=copy.deepcopy(self.state)
        result=self.parse({'narration':'El camino está despejado.','proposals':[],'routeTravel':{'exit':'catalogo'}})
        with patch('game_randomness.draw',side_effect=AssertionError('Travel rolled')):
            director_travel.apply(self.state,result['routeTravel'],self.body,self.me)
        self.assertEqual(self.state['routeProgress']['current'],'catalogo')
        self.assertEqual(self.state['characters'],before['characters'])
        self.assertEqual(self.state['worldTime'],before['worldTime'])
        self.assertEqual(self.state['messages'][-1]['routeTransition'],{'from':'entrada','to':'catalogo'})
        adventure_routes.validate_restored(self.state)

    def test_parser_rejects_unavailable_combined_or_non_action_travel(self):
        baseline=copy.deepcopy(self.state)
        for case in ('unavailable','combined','extra','dialogue','ooc','rules','opening','pending','combat'):
            self.state=copy.deepcopy(baseline)
            result={'narration':'Fixture','proposals':[],'routeTravel':{'exit':'catalogo'}};options={}
            if case=='unavailable':result['routeTravel']['exit']='lectura'
            elif case=='combined':result['proposals']=[{'type':'manual','reason':'Revisar'}]
            elif case=='extra':result['routeTravel']['heal']=True
            elif case in ('dialogue','ooc'):self.state['messages'][-1]['kind']=case
            elif case=='rules':options['rules']=True
            elif case=='opening':options['starting']=True
            elif case=='pending':self.state['pending']=[{'reason':'Pendiente'}]
            else:self.state['board']['active']=True
            before=copy.deepcopy(self.state)
            with self.subTest(case=case),self.assertRaisesRegex(ValueError,'route-travel'):self.parse(result,**options)
            self.assertEqual(self.state,before)

    def test_host_cannot_choose_for_another_owner_and_direct_calls_are_strict(self):
        before=copy.deepcopy(self.state)
        with self.assertRaises(PermissionError):director_travel.apply(self.state,{'exit':'catalogo'},self.body,{**self.me,'id':'other'})
        for item,body in (({'exit':'catalogo','hp':99},self.body),({'exit':'lectura'},self.body),({'exit':'catalogo'},{**self.body,'kind':'dialogue'})):
            with self.assertRaises(ValueError):director_travel.apply(self.state,item,body,self.me)
        self.assertEqual(self.state,before)

    def test_private_capture_can_restore_travel_without_raw_route_or_another_call(self):
        prepared=legacy.prepare(self.state,self.body['text'],[])
        value={'narration':'El camino está despejado.','proposals':[],'routeTravel':{'exit':'catalogo'}}
        before=copy.deepcopy(prepared)
        with patch.object(claude_dm,'ai_reply',side_effect=AssertionError('Capture called provider')):
            result=legacy.restore(prepared,{'kind':'report','value':value,'latencyMs':0},legacy.SCHEME)
        self.assertEqual(result,value);self.assertEqual(prepared,before)
        old_request=copy.deepcopy(prepared['request']);old_request['context'].pop('routeTravelActor')
        self.assertEqual(prepared['sha256'],hashlib.sha256(canonical(old_request).encode()).hexdigest())
        old_value={'narration':'Texto histórico sin ejecutar un viaje.','proposals':[]}
        restored=legacy.restore(prepared,{'kind':'report','value':old_value,'latencyMs':0},legacy.SCHEME)
        self.assertEqual(restored,old_value)
