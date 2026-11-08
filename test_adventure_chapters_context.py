import copy
import io
import json
import unittest
from unittest.mock import patch
import adventure_chapters as chapters
import adventure_modules as modules
import claude_dm
import director_prompt
import legacy_director_attempt as legacy
from test_adventure import memory
import test_adventure_chapters as fixture


def generated(state):
    previous=modules.builtin('la-carta-perdida')
    result={key:previous[key] for key in ('title','premise','location','description','goal','preparation','conclusion')}
    result.update(title='El sello de la archivera',premise=state['adventureChapterTransition']['premise'],location=state['location'],goal='Averiguar quién dejó el sello aquí.',preparation='PRIVATE-NEW-CHAPTER')
    for key,item in zip(('firstSearch','secondSearch'),previous['opportunities']):
        result[key]={field:item[field] for field in ('label','dc','discovery','failure')}
    result['firstSearch'].update(label='Examinar el sello del banco',discovery='La marca del sello coincide con la archivera.')
    result['secondSearch'].update(label='Examinar la nota junto al sello',discovery='La nota confirma quién dejó el sello aquí.')
    return result


def reply(state):
    return {'narration':'Otro objetivo espera aquí. Tú decides qué examinas.',
        'memory':memory(summary='La carta anterior está localizada; el nuevo sello sigue sin examinar.',location=state['location']),
        'worldUpdates':{'npcs':[],'places':[],'relationships':[]},'generatedAdventure':generated(state)}


class ChapterContextTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixture.AdventureChapterTests();self.fixture.setUp()
        self.state=chapters.prepare_next(self.fixture.state,self.fixture.body,self.fixture.me)

    def raw(self,value):return json.dumps({'stop_reason':'end_turn','content':[{'type':'text','text':json.dumps(value)}]}).encode()

    def test_schema_locks_location_and_context_keeps_history_private_with_confirmed_facts(self):
        before=copy.deepcopy(self.state);schema=claude_dm.response_schema(self.state,starting=True)
        self.assertEqual(schema['properties']['generatedAdventure']['properties']['location']['enum'],[self.state['location']])
        context=claude_dm.build_context(self.state,self.fixture.body['premise'],[],starting=True)
        self.assertNotIn('adventureChapters',context['state']);self.assertNotIn('PRIVATE-OLD-CHAPTER',str(context))
        history=context['state']['adventureChaptersView'];self.assertTrue(history['clockUncertain']);self.assertEqual(len(history['completed'][0]['discoveries']),2)
        self.assertEqual(history['references'][0]['sha256'],self.state['adventureChapters']['completed'][0]['sha256'])
        self.assertEqual(self.state,before)

    def test_generated_teleport_and_malformed_transition_are_rejected(self):
        bad=reply(self.state);bad['generatedAdventure']['location']='Un bosque lejano'
        with self.assertRaisesRegex(ValueError,'director:chapter-transition'):claude_dm.parse_response(self.state,self.raw(bad),starting=True)
        self.state['adventureChapterTransition']['previousSha256']='0'*64
        with self.assertRaises(ValueError):claude_dm.response_schema(self.state,starting=True)

    def test_sdk_requests_same_place_and_capture_replays_with_complete_old_archive_untouched(self):
        before=copy.deepcopy(self.state);sent=[]
        def response(request,**options):sent.append(json.loads(request.data));return io.BytesIO(self.raw(reply(self.state)))
        with patch.dict('os.environ',{'ANTHROPIC_API_KEY':'fixture-never-sent'}),patch('urllib.request.urlopen',side_effect=response):
            parsed=claude_dm.ai_reply(self.state,self.fixture.body['premise'],[],starting=True)
        self.assertIn(director_prompt.CHAPTER_START,sent[0]['system'])
        self.assertEqual(parsed['adventureModule']['location'],before['location'])
        prepared=legacy.prepare(self.state,self.fixture.body['premise'],[],starting=True)
        with patch.object(claude_dm,'ai_reply',side_effect=AssertionError('Chapter restore called provider')):
            result=legacy.restore(prepared,{'kind':'report','value':parsed,'latencyMs':0},legacy.SCHEME)
        self.assertEqual(result['adventureModule'],parsed['adventureModule']);self.assertEqual(self.state,before)
        self.assertNotIn('PRIVATE-OLD-CHAPTER',str(prepared['captureRequest']))
