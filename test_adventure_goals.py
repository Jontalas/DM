import copy
import unittest
from unittest.mock import patch
import adventure
import adventure_chapters as chapters
import adventure_goals as goals
import adventure_modules as modules
import campaign_world
import claude_dm
from engine import initial_state,apply_action
from server import queue_investigation
from test_adventure import memory
from test_character_builder import choices

HOST={'id':'host','host':True,'name':'Ana'}
GUEST={'id':'guest','host':False,'name':'Luis'}


class AdventureGoalTests(unittest.TestCase):
    def setUp(self):
        self.state=initial_state({'mode':'online'})
        for me,name in ((HOST,'Liria'),(GUEST,'Taro')):
            apply_action(self.state,{'type':'create_character','choices':{**choices(),'name':name}},me)
        modules.install(self.state,modules.builtin('la-carta-perdida'))
        adventure.apply_memory(self.state,memory(),starting=True)
        self.state['campaignWorld']=campaign_world.empty()
        for me,opportunity in ((HOST,'rastro'),(GUEST,'carta')):
            actor=next(c for c in self.state['characters'] if c['owner']==me['id'])
            queue_investigation(self.state,{'character':actor['id'],'opportunity':opportunity},me)
            apply_action(self.state,{'type':'check','request':self.state['pending'][0]['check']['id'],'method':'take20'},me)
        self.body={'type':goals.PROPOSE,'premise':'Investigar aquí la historia de Gaspar, sin recoger la carta.'}

    def acceptance(self,state=None):
        state=self.state if state is None else state;proposal=state[goals.FIELD]
        return {'type':'next_adventure','premise':proposal['premise'],'proposalId':proposal['id'],
                'worldMemoryContract':campaign_world.CONTRACT,'captureContract':'pf-director-action-1'}

    def test_proposal_is_deterministic_and_only_other_owner_can_accept(self):
        before=copy.deepcopy(self.state)
        self.state=goals.propose(self.state,self.body,HOST)
        self.assertEqual(goals.propose(before,self.body,HOST),self.state);self.assertNotIn(goals.FIELD,before)
        with self.assertRaises(PermissionError):goals.accept(self.state,self.acceptance(),HOST)
        approved=goals.accept(self.state,self.acceptance(),GUEST)
        self.assertEqual(approved['owners'],['guest','host'])
        view=goals.public_view(self.state,GUEST);self.assertTrue(view['proposal']['canAccept'])
        self.assertNotIn('bindingSha256',str(view));self.assertFalse(goals.public_view(self.state,HOST)['proposal']['canAccept'])
        with patch('game_randomness.draw',side_effect=AssertionError('Preparing chapter rolled dice')):
            next_state=chapters.prepare_next(self.state,self.acceptance(),GUEST)
        self.assertNotIn(goals.FIELD,next_state);self.assertEqual(next_state['characters'],self.state['characters'])
        self.assertEqual(next_state['location'],self.state['location']);self.assertEqual(next_state['worldTime'],self.state['worldTime'])

    def test_alternative_does_not_inherit_other_owners_acceptance(self):
        self.state=goals.propose(self.state,self.body,HOST);old=self.acceptance()
        self.state=goals.propose(self.state,{**self.body,'premise':'Averiguar aquí el origen de las placas.'},GUEST)
        self.assertNotEqual(old['proposalId'],self.state[goals.FIELD]['id'])
        with self.assertRaises(PermissionError):goals.accept(self.state,self.acceptance(),GUEST)
        with self.assertRaises(ValueError):goals.accept(self.state,old,HOST)
        self.assertEqual(goals.accept(self.state,self.acceptance(),HOST)['premise'],self.state[goals.FIELD]['premise'])

    def test_ooc_private_chat_and_views_do_not_change_binding_but_game_changes_do(self):
        self.state=goals.propose(self.state,self.body,HOST);body=self.acceptance()
        self.state['messages'].append({'kind':'ooc','text':'Un comentario','owner':'host'})
        self.state['private']['guest']='Una nota privada';self.state['nextAdventureView']={'rendered':True}
        goals.accept(self.state,body,GUEST)
        for mutate in (lambda s:s['characters'][0].update(hp=15),lambda s:s.update(worldTime='Más tarde'),
                       lambda s:s['campaignWorld'].update(revision=1)):
            changed=copy.deepcopy(self.state);mutate(changed)
            with self.subTest(mutate=mutate),self.assertRaisesRegex(ValueError,'situación ha cambiado'):
                goals.accept(changed,body,GUEST)
            self.assertFalse(goals.public_view(changed,GUEST)['proposal']['canAccept'])

    def test_only_owners_and_exact_premise_are_accepted(self):
        self.state=goals.propose(self.state,self.body,HOST);body=self.acceptance()
        observer={'id':'observer','host':True}
        with self.assertRaises(PermissionError):goals.propose(self.state,self.body,observer)
        with self.assertRaises(PermissionError):goals.accept(self.state,body,observer)
        with self.assertRaises(ValueError):goals.accept(self.state,{**body,'premise':'Abrimos la carta.'},GUEST)
        for key in ('author','acceptedBy','owners'):
            with self.subTest(key=key),self.assertRaises(ValueError):goals.propose(self.state,{**self.body,key:['guest']},HOST)

    def test_no_fallback_for_wrong_group_pending_or_archive_limit(self):
        for mutate in (lambda s:s.update(mode='shared'),lambda s:s['characters'][1].update(owner='host'),
                       lambda s:s['characters'][1].update(hp=0),lambda s:s['characters'][1].update(owner={}),
                       lambda s:s['pending'].append({'reason':'Pendiente'})):
            changed=copy.deepcopy(self.state);mutate(changed)
            with self.subTest(mutate=mutate),self.assertRaises(ValueError):goals.propose(changed,self.body,HOST)
        with patch.object(chapters,'MAX_ARCHIVE_BYTES',100):
            with self.assertRaises(ValueError):goals.propose(self.state,self.body,HOST)

    def test_group_final_action_requires_durable_contract_and_proposal_id(self):
        self.state=goals.propose(self.state,self.body,HOST)
        for key in ('captureContract','proposalId'):
            body=self.acceptance();body.pop(key)
            with self.subTest(key=key),self.assertRaises(ValueError):chapters.prepare_next(self.state,body,GUEST)

    def test_unaccepted_goal_and_proposal_messages_stay_out_of_director_context(self):
        self.state=goals.propose(self.state,self.body,HOST)
        self.state['messages'].append({'kind':'action','speaker':'Liria','owner':'host','text':self.body['premise'],
                                      'chapterGoalProposed':self.state[goals.FIELD]['id']})
        context=claude_dm.build_context(self.state,'Un comentario de la mesa.',[])
        self.assertNotIn(goals.FIELD,str(context));self.assertNotIn(self.body['premise'],str(context))
        prepared=chapters.prepare_next(self.state,self.acceptance(),GUEST)
        context=claude_dm.build_context(prepared,self.body['premise'],[],starting=True)
        self.assertEqual(context['state']['adventureChapterTransition']['premise'],self.body['premise'])
        self.assertEqual(len(context['state']['characters']),2)
