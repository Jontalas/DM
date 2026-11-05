import copy
import io
import json
import os
import unittest
import urllib.error
from unittest.mock import patch
import rule_pack_authoring as authoring
from rule_pack_runtime import RulePackError
from test_rule_pack_runtime import document


def request():
    return {'identity':{'id':'lantern-example','name':'La linterna','edition':'Ejemplo original 1','version':'1.0.0'},
        'license':{'id':'CC0-1.0','attribution':'Ejemplo propio para probar la preparación.'},
        'permission':'redistributable','scope':'Recurso, tirada, tabla y agotamiento del ejemplo.',
        'document':{'title':'Reglas propias de la linterna','edition':'Ejemplo original 1',
            'pages':[{'page':1,'text':'La energía inicial es 3. Cada intento requiere energía positiva y gasta 1. Se tiran 2d6: un total de 7 a 12 es éxito, 2 a 6 es fallo. Al quedar sin energía se activa agotamiento.'}]}}


def reply(prepared):
    data=document('original-pool-example');data.update(prepared['request']['identity'])
    data['license']=prepared['request']['license'];data['sources']=prepared['sources']
    for group in ('fields','tables','actions','triggers'):
        for spec in data[group].values():spec['sources']=[prepared['sources'][0]['id']]
    return {'status':'candidate','packageJson':json.dumps(data),'issues':[],
        'examples':[{'name':'Éxito y gasto de energía','stepsJson':json.dumps([{'action':'attempt','inputs':{},'physical':{'pool':[3,4]}}]),
            'expectedJson':json.dumps({'energy':2,'success':True,'exhausted':False})},
            {'name':'Agotamiento automático','stepsJson':json.dumps([{'action':'attempt','inputs':{},'physical':{'pool':[1,1]}}]*3),
            'expectedJson':json.dumps({'energy':0,'success':False,'exhausted':True})}]}


class RulePackAuthoringTests(unittest.TestCase):
    def setUp(self):self.prepared=authoring.prepare_input(request())

    def test_target_math_is_not_advertised_until_authoring_examples_support_two_sheets(self):
        self.assertNotIn('target-sheets',authoring.context(self.prepared)['engine']['capabilities'])
        response=reply(self.prepared);data=json.loads(response['packageJson'])
        data['requires'].append('target-sheets');data['actions']['attempt']['target']=True
        response['packageJson']=json.dumps(data)
        with self.assertRaisesRegex(RulePackError,'preparador'):authoring.validate_reply(self.prepared,response)
        # Capability presentation does not change an already captured request key.
        with patch.object(authoring,'CAPABILITIES',authoring.CAPABILITIES|{'future-library-capability'}):
            self.assertEqual(authoring.prepare_input(request())['sha256'],self.prepared['sha256'])

    def test_legacy_prompt_identity_wrapper_is_flattened_without_changing_rules(self):
        original=reply(self.prepared);data=json.loads(original['packageJson'])
        expected=copy.deepcopy(data);data['identity']={key:data.pop(key) for key in ('id','name','edition','version')}
        original['packageJson']=json.dumps(data);before=copy.deepcopy(original)
        report=authoring.validate_reply(self.prepared,original)
        self.assertEqual(report['candidate'],expected);self.assertEqual(original,before)
        self.assertIn('identity →',report['issues'][-1]['message'])
        authoring.validate_record({'request':self.prepared['request'],'sha256':self.prepared['sha256'],
            'sourceScheme':self.prepared['sourceScheme'],'report':report})
        # The deterministic package interpreter remains strict; only the known
        # provider representation is converted at the preparation boundary.
        from rule_pack_runtime import RulePack
        with self.assertRaises(RulePackError):RulePack(data)
        for kind in ('mismatch','mixed','unknown','bad-rule'):
            altered=copy.deepcopy(data)
            if kind=='mismatch':altered['identity']['id']='another-game'
            elif kind=='mixed':altered['id']=expected['id']
            elif kind=='unknown':altered['unrequested']='unknown'
            else:altered['actions']['attempt']['effects'][0]['value']={'op':'execute-code','args':[]}
            invalid=copy.deepcopy(original);invalid['packageJson']=json.dumps(altered)
            with self.subTest(kind=kind),self.assertRaises(RulePackError):authoring.validate_reply(self.prepared,invalid)

    def test_source_identity_and_hashes_are_stable_and_isolated(self):
        raw=request();prepared=authoring.prepare_input(raw);raw['document']['pages'][0]['text']='Changed'
        self.assertEqual(prepared,self.prepared)
        self.assertNotEqual(authoring.prepare_input(raw)['sha256'],prepared['sha256'])
        self.assertNotEqual(authoring.prepare_input(raw)['sources'][0]['id'],prepared['sources'][0]['id'])
        self.assertEqual(prepared['sources'][0]['locator'],'Página/fragmento aportado 1')
        view=authoring.context(prepared);view['fragments'][0]['text']='Changed context'
        self.assertNotEqual(view['fragments'][0]['text'],prepared['fragments'][0]['text'])
        self.assertNotIn('permission',authoring.context(prepared))

    def test_pdf_provenance_preserves_page_numbers_and_rejects_invalid_claims(self):
        raw=request();raw['document']['origin']={'kind':'pdf','sha256':'a'*64,'pageCount':4,'extractor':'pdfjs-6.5.438'}
        prepared=authoring.prepare_input(raw)
        self.assertIn('PDF p.1',prepared['sources'][0]['locator']);self.assertIn('a'*64,prepared['sources'][0]['locator'])
        self.assertNotEqual(prepared['sha256'],self.prepared['sha256'])
        for key,value in [('sha256','bad'),('pageCount',True),('extractor','python-eval'),('pageCount',0)]:
            altered=copy.deepcopy(raw);altered['document']['origin'][key]=value
            with self.subTest(key=key,value=value),self.assertRaises(RulePackError):authoring.prepare_input(altered)
        raw['document']['pages'][0]['page']=5
        with self.assertRaises(RulePackError):authoring.prepare_input(raw)

    def test_fragment_identity_is_stable_across_scope_version_and_page_selection(self):
        raw=request();prepared=authoring.prepare_input(raw)
        raw['scope']='Preparar otro bloque de la misma página'
        raw['identity']['version']='1.0.1';raw['identity']['id']='another-package-name'
        raw['document']['pages'].append({'page':2,'text':'Otro fragmento del mismo documento.'})
        changed=authoring.prepare_input(raw)
        self.assertEqual(prepared['sources'][0],changed['sources'][0])
        self.assertNotEqual(prepared['sha256'],changed['sha256'])
        raw['document']['pages'].reverse()
        self.assertEqual(authoring.prepare_input(raw)['sources'][1],prepared['sources'][0])
        for key in ('text','title','edition','page'):
            altered=request()
            if key in ('title','edition'):altered['document'][key]+=' changed'
            elif key=='page':altered['document']['pages'][0]['page']=2
            else:altered['document']['pages'][0]['text']+=' changed'
            with self.subTest(key=key):self.assertNotEqual(authoring.prepare_input(altered)['sources'][0]['id'],prepared['sources'][0]['id'])

    def test_pdf_identity_uses_original_hash_but_not_extractor_if_text_is_unchanged(self):
        raw=request();raw['document']['origin']={'kind':'pdf','sha256':'a'*64,'pageCount':4,'extractor':'pdfjs-6.5.438'}
        prepared=authoring.prepare_input(raw);raw['document']['origin']['extractor']='pdfjs-6.5.439'
        self.assertEqual(authoring.prepare_input(raw)['sources'],prepared['sources'])
        raw['document']['origin']['sha256']='b'*64
        self.assertNotEqual(authoring.prepare_input(raw)['sources'][0]['id'],prepared['sources'][0]['id'])

    def test_legacy_record_replays_original_request_based_source_ids(self):
        prepared=authoring.prepare_input(request(),authoring.LEGACY_SOURCE_SCHEME)
        self.assertEqual(prepared['sources'][0]['id'],'source-'+prepared['sha256'][:12]+'-p1')
        record={'request':request(),'sha256':prepared['sha256'],'report':authoring.validate_reply(prepared,reply(prepared))}
        with patch.object(authoring,'propose',side_effect=AssertionError('Legacy recovery called provider')):
            self.assertEqual(authoring.validate_record(record)['sources'],prepared['sources'])
        record['sourceScheme']='unknown'
        with self.assertRaises(RulePackError):authoring.validate_record(record)

    def test_composing_separate_preparations_does_not_duplicate_the_same_fragment(self):
        from rule_pack_composition import compose
        first_prepared=authoring.prepare_input(request())
        first=json.loads(reply(first_prepared)['packageJson']);first['triggers']={}
        later=request();later['scope']='Preparar el desencadenante de agotamiento';later['identity']['version']='1.0.1'
        second=json.loads(reply(authoring.prepare_input(later))['packageJson'])
        result=compose([first,second],'1.1.0')['document']
        self.assertEqual(len(result['sources']),1);self.assertIn('exhaustion',result['triggers'])

    def test_preflight_rejects_unbounded_missing_and_ambiguous_input_shape(self):
        for mutate in ('large','duplicate','bool-page','permission','unknown','empty'):
            raw=request()
            if mutate=='large':raw['document']['pages'][0]['text']='x'*(authoring.MAX_TEXT+1)
            elif mutate=='duplicate':raw['document']['pages']*=2
            elif mutate=='bool-page':raw['document']['pages'][0]['page']=True
            elif mutate=='permission':raw['permission']='certified'
            elif mutate=='unknown':raw['execute']='code'
            else:raw['document']['pages'][0]['text']=' '
            with self.subTest(mutate=mutate),self.assertRaises(RulePackError):authoring.prepare_input(raw)

    def test_candidate_checks_examples_with_no_rng_or_source_certification(self):
        original=reply(self.prepared);before=copy.deepcopy(original)
        with patch('rule_pack_runtime.secrets.randbelow',side_effect=AssertionError('Example rolled')):
            result=authoring.validate_reply(self.prepared,original)
        self.assertEqual(result['status'],'candidate');self.assertEqual(len(result['checks']),2)
        self.assertEqual(result['sourceVerification'],'unverified');self.assertEqual(original,before)
        self.assertEqual(result['candidate']['sources'],self.prepared['sources'])

    def test_no_candidate_on_missing_mechanics_and_no_fallback(self):
        for status,kind in [('ambiguous','ambiguity'),('unsupported','unsupported')]:
            blocked={'status':status,'packageJson':'','examples':[],
                'issues':[{'kind':kind,'message':'Falta el procedimiento necesario.','sources':[self.prepared['sources'][0]['id']]}]}
            result=authoring.validate_reply(self.prepared,blocked)
            self.assertIsNone(result['candidate']);self.assertEqual(result['checks'],[])
            blocked['issues']=[]
            with self.assertRaises(RulePackError):authoring.validate_reply(self.prepared,blocked)

    def test_rejects_invented_sources_identity_license_operations_and_unresolved_issues(self):
        for kind in ('source','identity','license','operation','issue','issue-source'):
            answer=reply(self.prepared);data=json.loads(answer['packageJson'])
            if kind=='source':data['sources'][0]['locator']='Another page'
            elif kind=='identity':data['edition']='Another edition'
            elif kind=='license':data['license']['id']='invented-permission'
            elif kind=='operation':data['actions']['attempt']['effects'][0]['value']={'op':'python','args':[]}
            elif kind=='issue':answer['issues']=[{'kind':'ambiguity','message':'Required rule missing','sources':[self.prepared['sources'][0]['id']]}]
            else:answer['issues']=[{'kind':'coverage','message':'Unknown source','sources':['not-provided']}]
            answer['packageJson']=json.dumps(data)
            with self.subTest(kind=kind),self.assertRaises(RulePackError):authoring.validate_reply(self.prepared,answer)

    def test_rejects_vacuous_wrong_or_nondeterministic_examples(self):
        for kind in ('empty','expected','types','dice','step','extra','no-examples'):
            answer=reply(self.prepared)
            if kind=='empty':answer['examples'][0]['expectedJson']='{}'
            elif kind=='expected':answer['examples'][0]['expectedJson']='{"energy":3}'
            elif kind=='types':answer['examples'][0]['expectedJson']='{"success":1}'
            elif kind=='dice':answer['examples'][0]['stepsJson']='[{"action":"attempt","inputs":{},"physical":{}}]'
            elif kind=='step':answer['examples'][0]['stepsJson']='[{"action":"attempt","inputs":{},"physical":{"pool":[3,4]},"fields":{"energy":99}}]'
            elif kind=='extra':answer['verified']=True
            else:answer['examples']=[]
            with self.subTest(kind=kind),patch('rule_pack_runtime.secrets.randbelow',side_effect=AssertionError('Bad example rolled')),self.assertRaises(RulePackError):
                authoring.validate_reply(self.prepared,answer)

    def test_single_provider_call_bounded_context_schema_and_usage(self):
        answer=reply(self.prepared)
        output={'stop_reason':'end_turn','content':[{'type':'text','text':json.dumps(answer)}],'usage':{'input_tokens':300,'output_tokens':700}}
        with patch.dict(os.environ,{'ANTHROPIC_API_KEY':'fake-authoring-key'}),patch.object(authoring.urllib.request,'urlopen',return_value=io.BytesIO(json.dumps(output).encode())) as call:
            result=authoring.propose(self.prepared)
        self.assertEqual(call.call_count,1);payload=json.loads(call.call_args.args[0].data)
        self.assertEqual(payload['max_tokens'],8000);self.assertEqual(result['usage']['inputTokens'],300)
        self.assertEqual(payload['output_config']['format']['schema'],authoring.SCHEMA)
        self.assertNotIn('fake-authoring-key',json.dumps(payload));self.assertNotIn('campaign',json.dumps(payload))
        self.assertEqual(json.loads(payload['messages'][0]['content'])['sources'],self.prepared['sources'])

    def test_provider_failure_never_retries_or_installs_anything(self):
        outputs=[b'broken-json',json.dumps({'stop_reason':'max_tokens','content':[]}).encode(),b'x'*(authoring.MAX_RESPONSE+1)]
        for raw in outputs:
            with patch.dict(os.environ,{'ANTHROPIC_API_KEY':'fake-authoring-key'}),patch.object(authoring.urllib.request,'urlopen',return_value=io.BytesIO(raw)) as call:
                with self.assertRaises(RulePackError):authoring.propose(self.prepared)
                self.assertEqual(call.call_count,1)
        with patch.dict(os.environ,{'ANTHROPIC_API_KEY':''}),patch.object(authoring.urllib.request,'urlopen') as call:
            with self.assertRaises(RulePackError):authoring.propose(self.prepared)
            call.assert_not_called()

    def test_imported_preparation_rechecks_sources_examples_and_claims_without_provider(self):
        report=authoring.validate_reply(self.prepared,reply(self.prepared))
        report['usage']={'inputTokens':123,'outputTokens':456,'latencyMs':2}
        record={'request':request(),'sha256':self.prepared['sha256'],'sourceScheme':self.prepared['sourceScheme'],'report':report}
        with patch.object(authoring,'propose',side_effect=AssertionError('Import called provider')):
            self.assertEqual(authoring.validate_record(record)['sha256'],record['sha256'])
            for kind in ('source','check','verification','digest'):
                altered=copy.deepcopy(record)
                if kind=='source':altered['request']['document']['pages'][0]['text']='Altered original'
                elif kind=='check':altered['report']['checks'][0]['expected']['energy']=99
                elif kind=='verification':altered['report']['sourceVerification']='certified'
                else:altered['report']['sha256']='0'*64
                with self.subTest(kind=kind),self.assertRaises(RulePackError):authoring.validate_record(altered)


if __name__=='__main__':unittest.main()
