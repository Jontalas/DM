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

    def test_unconscious_or_dead_owned_character_cannot_act_or_speak_even_without_selected_speaker(self):
        for hp in (-1,-14):
            self.state['characters'][0].update(hp=hp,stable=False);before=copy.deepcopy(self.state)
            for kind in ('action','dialogue'):
                for character in (self.actor,None):
                    with self.subTest(hp=hp,kind=kind,character=character),self.assertRaises(ValueError):
                        engine.apply_action(self.state,{'type':'talk','text':'Me levanto y hablo','kind':kind,'character':character},self.guest)
                    self.assertEqual(self.state,before)

    def test_zero_or_verified_negative_conscious_character_can_speak_without_hp_or_action_cost(self):
        import pf_recovery
        actor=self.state['characters'][0]
        for hp in (0,-1):
            actor.update(hp=hp,stable=True)
            if hp<0:
                pf_recovery.record_stabilization(actor,assisted=False,round_number=1)
                pf_recovery.apply_hour(actor,20)
            before=copy.deepcopy(actor);board=copy.deepcopy(self.state['board'])
            for kind in ('action','dialogue'):
                for character in (self.actor,None):engine.apply_action(self.state,{'type':'talk','text':'Pregunto por el registro','kind':kind,'character':character},self.guest)
            self.assertEqual(actor,before);self.assertEqual(self.state['board'],board)

    def test_out_of_character_and_private_notes_remain_available_while_unconscious(self):
        self.state['characters'][0].update(hp=-1,stable=False);before=copy.deepcopy(self.state['characters'])
        for kind in ('ooc','private'):
            for character in (self.actor,None):engine.apply_action(self.state,{'type':'talk','text':'Nota del jugador','kind':kind,'character':character},self.guest)
        self.assertEqual(self.state['characters'],before)

    def test_host_cannot_voice_unconscious_npc_but_can_record_explicit_notes(self):
        engine.apply_action(self.state,{'type':'create_npc','template':'pf1-goblin-warrior-1'},self.host)
        npc=self.state['characters'][1];npc.update(hp=-1,stable=False);before=copy.deepcopy(self.state)
        with self.assertRaises(ValueError):engine.apply_action(self.state,{'type':'talk','text':'Hablo','kind':'dialogue','character':npc['id']},self.host)
        self.assertEqual(self.state,before)
        engine.apply_action(self.state,{'type':'talk','text':'Nota sobre el PNJ','kind':'ooc','character':npc['id']},self.host)
