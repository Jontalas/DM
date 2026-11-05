import copy
import unittest
from unittest.mock import Mock
from rule_pack_runtime import RulePackError
import rule_pack_campaign as campaign
import test_rule_pack_narrative as fixture


class NarrativeAgencyTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixture.RulePackNarrativeTests();self.fixture.setUp()
        self.state=self.fixture.start();self.before=copy.deepcopy(self.state)

    def talk(self,answer):
        return campaign.execute_action(self.state,{'type':'talk_pack_adventure','character':self.fixture.character,
            'text':'Declaro Intentar para investigar la marca del farol.','mode':'action'},self.fixture.me,narrative_call=Mock(return_value=answer))

    def test_observed_live_undeclared_movement_and_memory_assertions_are_rejected(self):
        observed='Aria se acerca al mostrador del Archivo del Farol. La marca grabada en el cristal del farol de cobre es un signo de viento intrincado.'
        for field,text in [('narration',observed),('summary','Aria entra en el archivo.'),('preparation','Aria decide aceptar el encargo.'),('narration','Te acercas al mostrador y tomas el farol.')]:
            with self.assertRaises(RulePackError):self.talk(fixture.reply('intentar',**{field:text}))
            self.assertEqual(self.state,self.before)

    def test_world_only_requests_attributed_intentions_and_questions_remain_legal(self):
        for text in ['La marca permanece sobre el mostrador. Arda espera; falta resolver Intentar.',
                     'Aria declara que quiere investigar la marca. Arda espera los dados.',
                     '¿Te acercas al mostrador o prefieres preguntar a Arda?']:
            state=self.talk(fixture.reply('intentar',narration=text))
            self.assertIsNotNone(state['narrative']['pending']);self.assertEqual(state['characters'],self.state['characters'])
