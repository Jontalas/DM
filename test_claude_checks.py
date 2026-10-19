import io,json,unittest
from unittest.mock import patch
import claude_dm
from engine import initial_state


class ClaudeCheckContractTests(unittest.TestCase):
    def call(self,result,state=None):
        response={'stop_reason':'end_turn','content':[{'type':'text','text':json.dumps(result)}]}
        with patch.dict('os.environ',{'ANTHROPIC_API_KEY':'test-only'}),patch('urllib.request.urlopen',return_value=io.BytesIO(json.dumps(response).encode())) as provider:
            out=claude_dm.ai_reply(state or initial_state({}),'Intento abrir',[],check_actors=['actor'])
        body=json.loads(provider.call_args.args[0].data)
        context=json.loads(body['messages'][0]['content'])
        self.assertEqual(context['checkActors'],['actor'])
        self.assertIn('checks',body['output_config']['format']['schema']['properties'])
        self.assertTrue(all('creation' not in c for c in context['state']['characters']))
        return out

    def test_creation_audit_is_not_sent_as_duplicate_paid_context(self):
        state=initial_state({});state['characters']=[{'id':'actor','hp':10,'creation':{'details':{'large':'audit'}}}]
        self.call({'narration':'Fixture','proposals':[]},state)
        self.assertIn('creation',state['characters'][0])

    def test_optional_requests_are_backwards_compatible(self):
        result={'narration':'Texto de prueba','proposals':[]}
        self.assertEqual(self.call(result),result)

    def test_valid_structured_request_and_invalid_numeric_values(self):
        check={'character':'actor','kind':'ability','key':'str','dc':15,'reason':'CD adjudicada'}
        result={'narration':'Texto de prueba','proposals':[],'checks':[check]}
        self.assertEqual(self.call(result),result)
        for invalid in [True,'15',-1,1001]:
            with self.subTest(value=invalid),self.assertRaises(ValueError):self.call({**result,'checks':[{**check,'dc':invalid}]})
        with self.assertRaises(ValueError):self.call({**result,'checks':[check]*4})


if __name__=='__main__':unittest.main()
