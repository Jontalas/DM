import copy
import io
import json
import unittest
from unittest.mock import patch
from narrative_text import repair_text,normalize_response
from claude_dm import ai_reply,build_context
from engine import initial_state


class NarrativeTextTests(unittest.TestCase):
    def test_recorded_live_opening_and_mixed_healthy_unicode(self):
        broken='El salÃ³n huele a pan reciÃ©n horneado. â€”Perdone... Â¿La carta? El pequeÃ±o fragmento. —Sí, Lucía. 🎲'
        expected='El salón huele a pan recién horneado. —Perdone... ¿La carta? El pequeño fragmento. —Sí, Lucía. 🎲'
        self.assertEqual(repair_text(broken),expected)
        self.assertEqual(repair_text(expected),expected)

    def test_healthy_names_incomplete_bytes_and_double_encoding(self):
        for value in ['Ãngela y Ângelo','— ¿Qué hace Lucía? El pingüino 🎲','Ã','â€','中文 Ελληνικά','A\u0301','x\x00y']:
            self.assertEqual(repair_text(value),value)
        expected='Una habitación y un dado 🎲'
        broken=expected.encode('utf-8').decode('cp1252')
        self.assertEqual(repair_text(broken),expected)
        self.assertEqual(repair_text('salÃƒÂ³n'),'salón')

    def test_fields_identifiers_and_player_text_are_not_rewritten(self):
        original={'narration':'El salÃ³n.', 'proposals':[],
                  'checks':[{'character':'Ã³','key':'Ã³','reason':'SituaciÃ³n','dc':15}],
                  'memory':{'summary':'La habitaciÃ³n.','location':'SalÃ³n','goal':'InvestigaciÃ³n',
                            'objectives':['ConversaciÃ³n'],'preparation':'El niÃ±o.'}}
        before=copy.deepcopy(original);result=normalize_response(original)
        self.assertEqual(result['checks'][0]['character'],'Ã³');self.assertEqual(result['checks'][0]['key'],'Ã³')
        self.assertEqual(result['checks'][0]['dc'],15)
        self.assertEqual(result['memory']['preparation'],'El niño.')
        self.assertEqual(original,before)
        state=initial_state({});state['messages']=[{'speaker':'Ana','kind':'dialogue','text':'Digo literalmente Ã³'},
                                                {'speaker':'Director','kind':'director','text':'El salÃ³n.'}]
        context=build_context(state,'Continúa',[])
        self.assertEqual(context['history'][0]['text'],'Digo literalmente Ã³')
        self.assertEqual(context['history'][1]['text'],'El salón.')
        self.assertEqual(context['playerAgency'],{'declarationsInHistory':[0],'activeDeclaration':None})

    def test_provider_json_roundtrip_is_utf8_and_normalizes_only_model_prose(self):
        state=initial_state({});state['messages']=[{'speaker':'Ana','kind':'action','text':'Saludo, sin moverme.'}]
        response={'stop_reason':'end_turn','content':[{'type':'text','text':json.dumps({'narration':'El salÃ³n. —Sí.','proposals':[]},ensure_ascii=False)}]}
        with patch.dict('os.environ',{'ANTHROPIC_API_KEY':'test-only'}),patch('urllib.request.urlopen',return_value=io.BytesIO(json.dumps(response,ensure_ascii=False).encode('utf-8'))):
            self.assertEqual(ai_reply(state,'Saludo, sin moverme.',[])['narration'],'El salón. —Sí.')
        context=build_context(state,'Saludo, sin moverme.',[])
        self.assertEqual(context['playerAgency']['activeDeclaration'],0)
