import copy
import unittest
from unittest.mock import patch
import objective_targets
from rule_pack_runtime import RulePack,RulePackError
import test_target_context as fixture
from test_rule_pack_objectives import goal


class ObjectiveTargetRoutesTests(unittest.TestCase):
    def setUp(self):
        example=fixture.AbstractTargetContextTests();example.setUp();self.pack=example.pack;self.actors=example.state['actors']
        self.goals=[goal()|{'status':'open'}]
        self.routes=[{'objective':'farol','action':'contest','field':'success','npc':'arda','inputs':{}}]

    def compile(self,routes=None):
        return objective_targets.compile_routes(self.routes if routes is None else routes,self.pack,self.goals,self.actors)

    def test_matches_exact_npc_action_and_available_goal_without_dice(self):
        original=copy.deepcopy(self.routes)
        with patch('rule_pack_runtime.secrets.randbelow',side_effect=AssertionError('Route matching rolled')):
            routes=self.compile();check=objective_targets.select(routes,self.goals,'contest','arda',{})
        self.assertEqual(check,{'objective':'farol','field':'success'});self.assertEqual(original,self.routes)
        for action,npc in [('contest','sombra'),('explore','arda')]:
            self.assertIsNone(objective_targets.select(routes,self.goals,action,npc,{}))
        for change in [{'known':False},{'status':'completed'}]:
            self.assertIsNone(objective_targets.select(routes,[self.goals[0]|change],'contest','arda',{}))

    def test_rejects_unknown_actor_wrong_output_individual_and_ambiguous_routes(self):
        for change in [{'npc':'missing'},{'field':'energy'},{'action':'explore'},{'objective':'missing'},{'inputs':{'unknown':1}}]:
            with self.assertRaises(RulePackError):self.compile([self.routes[0]|change])
        with self.assertRaises(RulePackError):self.compile(self.routes*2)

    def test_target_scoped_boolean_cannot_prove_players_objective(self):
        data=fixture.abstract_document();data['actions']['contest']['effects'][1]['scope']='target';self.pack=RulePack(data)
        with self.assertRaises(RulePackError):self.compile()

    def test_choices_use_same_defaults_types_and_bounds_as_runtime(self):
        data=fixture.abstract_document();data['actions']['contest']['inputs']={'approach':{'type':'text','label':'Enfoque',
            'maxLength':20,'options':['cauto','directo'],'default':'cauto'}};self.pack=RulePack(data)
        routes=self.compile();self.assertEqual(routes[0]['inputs'],{'approach':'cauto'})
        self.assertEqual(self.pack.action_inputs('contest',{}),routes[0]['inputs'])
        self.assertIsNone(objective_targets.select(routes,self.goals,'contest','arda',{'approach':'directo'}))
        self.assertIsNotNone(objective_targets.select(routes,self.goals,'contest','arda',{'approach':'cauto'}))
        with self.assertRaises(RulePackError):self.compile([self.routes[0]|{'inputs':{'approach':'inventado'}}])

    def test_compile_does_not_claim_future_scene_or_requirements_are_satisfied(self):
        data=fixture.abstract_document();data['actions']['contest']['requires']=[False];self.pack=RulePack(data)
        # A legal future recipe is still useful; runtime must reject its use now.
        self.assertEqual(self.compile(),self.routes)

    def test_limits_apply_to_normalized_defaults_and_unserializable_content(self):
        for routes in [[],self.routes*13,[self.routes[0]|{'inputs':{'unknown':object()}}]]:
            with self.assertRaises(RulePackError):self.compile(routes)
        data=fixture.abstract_document();data['actions']['contest']['inputs']={
            'choice'+str(index):{'type':'text','label':'Texto propio','maxLength':4000,'default':'x'*4000}
            for index in range(5)}
        self.pack=RulePack(data)
        with self.assertRaisesRegex(RulePackError,'normalizadas'):self.compile()
