import copy
import unittest
import engine
from test_character_builder import choices


class SpeakerAgencyTests(unittest.TestCase):
    host={'id':'host','name':'Ana','host':True}
    guest={'id':'guest','name':'Luis','host':False}

    def setUp(self):
        self.state=engine.initial_state({})
        engine.apply_action(self.state,{'type':'create_character','choices':choices()},self.guest)
        self.actor=self.state['characters'][0]['id']

    def test_even_host_cannot_declare_another_players_actions_or_words(self):
        before=copy.deepcopy(self.state)
        for kind in ('action','dialogue'):
            with self.subTest(kind=kind),self.assertRaises(PermissionError):
                engine.apply_action(self.state,{'type':'talk','text':'Acepto el trato','kind':kind,'character':self.actor},self.host)
            self.assertEqual(self.state,before)

    def test_owner_can_speak_and_host_can_add_explicit_non_character_notes(self):
        for kind in ('action','dialogue'):
            engine.apply_action(self.state,{'type':'talk','text':'Elijo esperar','kind':kind,'character':self.actor},self.guest)
            self.assertEqual(self.state['messages'][-1]['owner'],self.guest['id'])
        for kind in ('ooc','private'):
            engine.apply_action(self.state,{'type':'talk','text':'Nota sobre la situación','kind':kind,'character':self.actor},self.host)
            self.assertEqual(self.state['messages'][-1]['kind'],kind)
        self.assertEqual(self.state['messages'][-1]['visibility'],'private')

    def test_host_npc_speech_remains_a_separate_manual_role(self):
        engine.apply_action(self.state,{'type':'create_npc','template':'pf1-goblin-warrior-1'},self.host)
        npc=self.state['characters'][1]['id']
        engine.apply_action(self.state,{'type':'talk','text':'Intervención excepcional del PNJ','kind':'dialogue','character':npc},self.host)
        self.assertEqual(self.state['messages'][-1]['speaker'],'Goblin · Ana')
