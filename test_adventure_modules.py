import copy
import unittest
from unittest.mock import patch
import adventure
import adventure_modules as modules
import claude_dm
from engine import initial_state,apply_action
from server import queue_investigation,view
from test_adventure import memory
from test_character_builder import choices

HOST={'id':'host','name':'Ana','host':True}
GUEST={'id':'guest','name':'Luis','host':False}


class InvestigationTests(unittest.TestCase):
    def state(self):
        state=initial_state({})
        apply_action(state,{'type':'create_character','choices':choices()},HOST)
        modules.install(state,modules.builtin('la-carta-perdida'))
        adventure.apply_memory(state,memory(),starting=True)
        return state

    def search(self,state,opportunity,method='roll',physical=None):
        queue_investigation(state,{'character':state['characters'][0]['id'],'opportunity':opportunity},HOST)
        body={'type':'check','request':state['pending'][-1]['check']['id'],'method':method}
        if physical is not None:body['physical']=[physical]
        apply_action(state,body,HOST)

    def test_failure_retry_fixed_values_discovery_and_goal_are_automatic(self):
        state=self.state();before=copy.deepcopy(state['characters'])
        self.search(state,'rastro',physical=1)
        self.assertFalse(state['moduleProgress']['discoveries']);self.assertEqual(state['moduleProgress']['searchActions'],1)
        with patch('engine.secrets.randbelow',side_effect=AssertionError('Choosing 10/20 must not roll')):
            self.search(state,'rastro','take10');self.search(state,'carta','take20')
        self.assertTrue(state['moduleProgress']['completed']);self.assertEqual(state['moduleProgress']['searchActions'],22)
        self.assertEqual(state['moduleProgress']['attempts'],{'rastro':2,'carta':1})
        self.assertEqual(state['characters'],before);self.assertEqual(state['objectives'],[])
        self.assertEqual([v['id'] for v in state['moduleProgress']['discoveries']],['rastro','carta'])
        self.assertTrue(state['messages'][-1]['adventureComplete'])
        with self.assertRaises(ValueError):self.search(state,'carta')

    def test_hidden_clues_and_conclusion_stay_private_until_confirmed(self):
        state=self.state();public=modules.public_view(state)
        self.assertEqual(public['conclusion'],'')
        self.assertEqual(public['opportunities'],[{'id':'rastro','label':'Examinar de cerca la zona del banco'}])
        self.assertEqual(public['discoveries'],[])
        context=claude_dm.build_context(state,'Examino',[])
        self.assertNotIn('adventureModule',context['state'])
        self.assertIn('adventureModule',context['directorKnowledge'])
        context=claude_dm.build_context(state,'Consulta',[],rules=True)
        self.assertNotIn('directorKnowledge',context)
        self.assertNotIn('adventureModule',context['state'])
        self.search(state,'rastro','take10')
        self.assertEqual(modules.public_view(state)['opportunities'][0]['id'],'carta')

    def test_ownership_lock_prerequisites_and_pending_tampering_precede_rng(self):
        state=self.state();cid=state['characters'][0]['id']
        with patch('engine.secrets.randbelow',side_effect=AssertionError('Invalid request consumed dice')):
            with self.assertRaises(PermissionError):modules.investigation(state,{'character':cid,'opportunity':'rastro'},GUEST)
            with self.assertRaises(ValueError):modules.investigation(state,{'character':cid,'opportunity':'carta'},HOST)
            queue_investigation(state,{'character':cid,'opportunity':'rastro'},HOST)
            with self.assertRaises(ValueError):modules.investigation(state,{'character':cid,'opportunity':'rastro'},HOST)
            state['pending'][-1]['check']['dc']=0
            with self.assertRaises(ValueError):apply_action(state,{'type':'check','request':state['pending'][-1]['check']['id']},HOST)
        state=self.state();state['board']['active']=True
        with self.assertRaises(ValueError):modules.investigation(state,{'character':cid,'opportunity':'rastro'},HOST)

    def test_module_validation_rejects_unsupported_rules_and_unreachable_graphs(self):
        original=modules.builtin('la-carta-perdida')
        mutations=[lambda m:m.update(scope='combat'),lambda m:m.update(inventory=['key']),
                   lambda m:m['opportunities'][0].update(dc=True),lambda m:m['opportunities'][0].update(dc=41),
                   lambda m:m['opportunities'][0].update(requires=['carta']),
                   lambda m:m['objectives'][0].update(requires=['missing']),lambda m:m['opportunities'][0].update(id='Bad ID')]
        for mutate in mutations:
            value=copy.deepcopy(original);mutate(value)
            with self.assertRaises(ValueError):modules.validate_module(value)
        self.assertEqual(modules.validate_module(original),original)

    def test_restored_progress_is_checked_and_narration_cannot_reopen_goals(self):
        state=self.state();self.search(state,'rastro','take10');self.search(state,'carta','take20')
        modules.validate_restored(state)
        adventure.apply_memory(state,memory(objectives=['Objetivo inventado'],location='Otro lugar'))
        self.assertEqual(state['objectives'],[]);self.assertEqual(state['location'],state['adventureModule']['location'])
        for mutate in [lambda s:s['moduleProgress'].update(completed=False),
                       lambda s:s['moduleProgress']['discoveries'][0].update(text='Pista inventada'),
                       lambda s:s['moduleProgress'].update(searchActions=0)]:
            altered=copy.deepcopy(state);mutate(altered)
            with self.assertRaises(ValueError):modules.validate_restored(altered)

    def test_choose10_outside_verified_module_is_rejected(self):
        state=self.state();cid=state['characters'][0]['id']
        with patch('engine.secrets.randbelow',side_effect=AssertionError('Invalid request consumed dice')):
            with self.assertRaises(ValueError):apply_action(state,{'type':'check','character':cid,'checkKind':'ability','key':'str','method':'take10'},HOST)

    def test_required_clues_must_be_reachable_without_changing_author_dc(self):
        state=self.state();module=modules.builtin('la-carta-perdida');module['opportunities'][0]['dc']=40
        before=copy.deepcopy(state)
        with self.assertRaises(ValueError):modules.install(state,module)
        self.assertEqual(state,before)
