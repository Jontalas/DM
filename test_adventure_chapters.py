import copy
import unittest
from unittest.mock import patch
import adventure
import adventure_chapters as chapters
import adventure_modules as modules
import campaign_world
from test_adventure import memory
import test_adventure_modules as fixture
from test_rule_pack_world import npc


class AdventureChapterTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixture.InvestigationTests();self.state=self.fixture.state()
        self.state['adventureModule']['preparation']='PRIVATE-OLD-CHAPTER: conserva este original.'
        for opportunity in ('rastro','carta'):self.fixture.search(self.state,opportunity,method='take20')
        self.body={'type':'next_adventure','premise':'Quiero saber quién vio a la archivera aquí.','worldMemoryContract':campaign_world.CONTRACT}
        self.me=fixture.HOST

    def finish_opening(self,state):
        result=copy.deepcopy(state);transition=result.pop('adventureChapterTransition')
        module=modules.builtin('la-carta-perdida');module['title']='Otro misterio en la posada'
        modules.install(result,module);adventure.apply_memory(result,memory(summary='Un nuevo objetivo aquí, sin viaje.'))
        result['messages'].append({'kind':'director','text':'Otro objetivo aquí.','adventureChapterStart':{'number':transition['to'],'previousSha256':transition['previousSha256']}})
        return result

    def test_prepare_is_deterministic_complete_and_does_not_touch_ficha_clock_or_original(self):
        before=copy.deepcopy(self.state)
        with patch('game_randomness.draw',side_effect=AssertionError('Chapter rolled')):
            first=chapters.prepare_next(self.state,self.body,self.me);second=chapters.prepare_next(self.state,self.body,self.me)
        self.assertEqual(first,second);self.assertEqual(self.state,before)
        for key in ('characters','board','worldTime','private','secrets','directorNotes','directorMemory','adventure'):self.assertEqual(first.get(key),before.get(key))
        self.assertNotIn('adventureModule',first);self.assertNotIn('moduleProgress',first)
        entry=first['adventureChapters']['completed'][0]
        self.assertEqual(entry['module'],before['adventureModule']);self.assertEqual(entry['progress'],before['moduleProgress'])
        self.assertIn('PRIVATE-OLD-CHAPTER',entry['module']['preparation'])
        self.assertEqual(first['adventureChapterTransition']['location'],before['location'])

    def test_existing_world_is_preserved_and_old_campaign_can_opt_in_only_on_explicit_new_step(self):
        self.state['campaignWorld']=campaign_world.apply(campaign_world.empty(),{'npcs':[npc()],'places':[],'relationships':[]})
        result=chapters.prepare_next(self.state,self.body,self.me)
        self.assertEqual(result['campaignWorld'],self.state['campaignWorld']);self.assertIsNot(result['campaignWorld'],self.state['campaignWorld'])
        for body in ({**self.body,'worldMemoryContract':'unknown'},{k:v for k,v in self.body.items() if k!='worldMemoryContract'}):
            with self.assertRaises(ValueError):chapters.prepare_next(self.state,body,self.me)

    def test_private_history_stays_out_of_public_view_and_time_uncertainty_survives_new_module(self):
        state=self.finish_opening(chapters.prepare_next(self.state,self.body,self.me));chapters.validate_restored(state)
        self.assertEqual(state['moduleProgress']['searchActions'],0)
        public=chapters.public_view(state['adventureChapters']);self.assertTrue(public['clockUncertain'])
        self.assertNotIn('PRIVATE',str(public));self.assertNotIn('preparation',str(public));self.assertEqual(len(public['completed'][0]['discoveries']),2)
        self.assertEqual(state['worldTime'],self.state['worldTime']);self.assertEqual(state['characters'],self.state['characters'])

    def test_owner_pending_injury_routes_manual_stats_and_location_limits_precede_changes(self):
        baseline=copy.deepcopy(self.state)
        for case in ('owner','guest','pending','injured','condition','combat','route','stats','location','unresolved','extra-character'):
            self.state=copy.deepcopy(baseline);me=self.me
            if case=='owner':me={**self.me,'id':'other'}
            elif case=='guest':me={**self.me,'host':False}
            elif case=='pending':self.state['pending']=[{'reason':'Pendiente'}]
            elif case=='injured':self.state['characters'][0]['hp']=0
            elif case=='condition':self.state['characters'][0]['conditions']='Fatigado'
            elif case=='combat':self.state['board']['active']=True
            elif case=='route':self.state['adventureRoute']={'id':'unsupported'}
            elif case=='stats':self.state['characters'][0]['ac']+=1
            elif case=='location':self.state['location']='Otro lugar'
            elif case=='unresolved':self.state['consequences']=[{'interpreted':False}]
            else:self.state['characters'].append(copy.deepcopy(self.state['characters'][0]))
            before=copy.deepcopy(self.state)
            with self.subTest(case=case),self.assertRaises((ValueError,PermissionError)):chapters.prepare_next(self.state,self.body,me)
            self.assertEqual(self.state,before)

    def test_corrupt_archive_incomplete_progress_missing_marker_and_teleport_are_rejected(self):
        good=self.finish_opening(chapters.prepare_next(self.state,self.body,self.me))
        for case in ('checksum','progress','number','missing-marker','missing-archive','location'):
            altered=copy.deepcopy(good)
            if case=='checksum':altered['adventureChapters']['completed'][0]['summary']='Modificado'
            elif case=='progress':
                entry=altered['adventureChapters']['completed'][0];entry['progress']['completed']=False;entry['sha256']=chapters._digest(entry)
            elif case=='number':altered['adventureChapters']['current']=True
            elif case=='missing-marker':altered['messages']=[m for m in altered['messages'] if 'adventureChapterStart' not in m]
            elif case=='missing-archive':del altered['adventureChapters']
            else:altered['adventureModule']['location']='Otro lugar'
            with self.subTest(case=case),self.assertRaises(ValueError):chapters.validate_restored(altered)

    def test_archive_limit_is_checked_before_any_generation_and_keeps_original(self):
        before=copy.deepcopy(self.state)
        with patch.object(chapters,'MAX_ARCHIVE_BYTES',100):
            self.assertIn('límite',chapters.limitation(self.state,self.me))
            with self.assertRaises(ValueError):chapters.prepare_next(self.state,self.body,self.me)
        self.assertEqual(self.state,before)

    def test_positive_wounds_and_token_position_are_not_reset_to_builder_defaults(self):
        self.state['characters'][0].update(hp=7,x=3,y=4)
        result=self.finish_opening(chapters.prepare_next(self.state,self.body,self.me))
        self.assertEqual(result['characters'],self.state['characters']);self.assertEqual(result['characters'][0]['hp'],7)
        chapters.validate_restored(result)

    def test_eight_chapters_are_contiguous_and_the_next_one_stops_before_generation(self):
        state=self.state
        for number in range(2,chapters.MAX_CHAPTERS+1):
            state=self.finish_opening(chapters.prepare_next(state,self.body,self.me))
            for opportunity in ('rastro','carta'):self.fixture.search(state,opportunity,method='take20')
            chapters.validate_restored(state);self.assertEqual(state['adventureChapters']['current'],number)
        before=copy.deepcopy(state)
        with self.assertRaises(ValueError):chapters.prepare_next(state,self.body,self.me)
        self.assertEqual(state,before)
        altered=copy.deepcopy(state);entry=altered['adventureChapters']['completed'][0];entry['module']['location']='Otro lugar';entry['sha256']=chapters._digest(entry)
        altered['messages'][next(i for i,m in enumerate(altered['messages']) if 'adventureChapterStart' in m)]['adventureChapterStart']['previousSha256']=entry['sha256']
        with self.assertRaises(ValueError):chapters.validate_restored(altered)
