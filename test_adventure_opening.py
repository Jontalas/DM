import copy
import unittest
from unittest.mock import patch
import adventure
import adventure_opening as opening
import adventure_modules as modules
import adventure_routes as routes
import engine
import campaign_world
from test_character_builder import choices
import test_adventure_chapters as chapter_fixture


class AuthoredOpeningTests(unittest.TestCase):
    def setUp(self):
        self.me={'id':'host','name':'Ana','host':True};self.state=engine.initial_state({})
        engine.apply_action(self.state,{'type':'create_character','choices':choices()},self.me)
        modules.install(self.state,modules.builtin('la-carta-perdida'))

    def confirm(self,state):
        result=opening.prepared_reply(state);adventure.apply_memory(state,result['memory'],starting=True)
        state['preparedOpening']=opening.receipt(state)
        state['messages'].append({'kind':'scene','speaker':'Escena preparada','text':result['narration'],'preparedOpeningSha256':state['preparedOpening']['moduleSha256']})

    def test_exact_authored_intro_and_private_preparation_without_dice_or_mutation(self):
        before=copy.deepcopy(self.state)
        with patch('game_randomness.draw',side_effect=AssertionError('Intro rolled')):reply=opening.prepared_reply(self.state)
        self.assertEqual(reply['narration'],self.state['adventureModule']['description'])
        self.assertEqual(reply['memory']['preparation'],self.state['adventureModule']['preparation'])
        self.assertEqual(self.state,before);self.assertNotIn('worldUpdates',reply)
        self.state['campaignWorld']=campaign_world.empty();self.assertEqual(opening.prepared_reply(self.state)['worldUpdates'],{'npcs':[],'places':[],'relationships':[]})

    def test_receipt_survives_searches_without_discovering_anything_at_start(self):
        self.confirm(self.state);opening.validate_restored(self.state)
        self.assertEqual(self.state['moduleProgress']['discoveries'],[])
        self.assertFalse(self.state['moduleProgress']['completed'])
        with self.assertRaises(ValueError):opening.prepared_reply(self.state)
        with self.assertRaises(ValueError):adventure.validate_start({**self.state,'adventure':None},{},self.me)

    def test_original_receipt_remains_bound_to_first_chapter_after_new_objective(self):
        fixture=chapter_fixture.AdventureChapterTests();fixture.setUp()
        fixture.state['preparedOpening']=opening.receipt(fixture.state)
        fixture.state['messages'].append({'kind':'scene','preparedOpeningSha256':fixture.state['preparedOpening']['moduleSha256']})
        from adventure_chapters import prepare_next
        result=fixture.finish_opening(prepare_next(fixture.state,fixture.body,fixture.me))
        opening.validate_restored(result)
        result['adventureChapters']['completed'][0]['module']['preparation']='Otro original'
        with self.assertRaises(ValueError):opening.validate_restored(result)

    def test_route_intro_is_bound_to_original_start_scene_not_current_destination(self):
        state=engine.initial_state({});engine.apply_action(state,{'type':'create_character','choices':choices()},self.me)
        routes.install(state,routes.builtin());self.confirm(state)
        other=next(scene for scene in state['adventureRoute']['scenes'] if scene['id']!=state['adventureRoute']['start'])
        state['routeProgress']['current']=other['id'];modules.install(state,other['module'])
        opening.validate_restored(state)

    def test_forged_missing_or_unbound_receipts_are_rejected(self):
        self.confirm(self.state);baseline=copy.deepcopy(self.state)
        for case in ('missing','marker','original','format'):
            altered=copy.deepcopy(baseline)
            if case=='missing':del altered['preparedOpening']
            elif case=='marker':altered['messages']=[m for m in altered['messages'] if 'preparedOpeningSha256' not in m]
            elif case=='original':altered['adventureModule']['preparation']='Alterado'
            else:altered['preparedOpening']['format']='unknown'
            with self.subTest(case=case),self.assertRaises(ValueError):opening.validate_restored(altered)
