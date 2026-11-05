import copy
import unittest
from adventure_discoveries import prepare,validate,bind,resolve,public_view
from rule_pack_runtime import RulePackError


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.source='Texto propio CC0.\r\nLa señal indica el archivo.\r\nOtro secreto.'
        text='La señal indica el archivo.';start=self.source.index(text)
        self.definition={'id':'archivo','objective':'farol','field':'success','start':start,'end':start+len(text),'text':text}
        self.catalog=prepare(self.source,[self.definition],'provided-adventure')
        self.check={'objective':'farol','field':'success'}
        self.binding=bind(self.catalog,'archivo',self.check,'request-1')
        self.proof={**self.check,'request':'request-1','matchedInputs':True,'met':True}

    def test_exact_unicode_source_and_immutable_definition(self):
        self.assertEqual(validate(self.catalog,self.source),self.catalog)
        self.assertEqual(self.source[self.definition['start']:self.definition['end']],self.definition['text'])
        self.definition['text']='Modificado'
        self.assertNotEqual(self.catalog['definitions'][0]['text'],self.definition['text'])
        for source in [self.source.replace('\r\n','\n'),self.source+' ']:
            with self.assertRaises(RulePackError):validate(self.catalog,source)

    def test_only_same_successful_bound_request_reveals(self):
        self.assertEqual(public_view(self.catalog,[]),[])
        for proof in [self.proof|{'met':False},self.proof|{'matchedInputs':False}]:
            self.assertIsNone(resolve(self.catalog,self.binding,proof,7))
        receipt=resolve(self.catalog,self.binding,self.proof,7)
        self.assertEqual(public_view(self.catalog,[receipt]),[{'id':'archivo','text':self.catalog['definitions'][0]['text'],'message':7}])
        self.assertNotIn('Otro secreto',str(public_view(self.catalog,[receipt])))
        for key,value in [('request','other'),('objective','other'),('field','other'),('met',1),('matchedInputs',1)]:
            with self.assertRaises(RulePackError):resolve(self.catalog,self.binding,self.proof|{key:value},7)
        with self.assertRaises(RulePackError):public_view(self.catalog,[receipt,receipt])
        for bad in [None,[],receipt|{'objective':'other'},receipt|{'message':True},receipt|{'reward':10}]:
            with self.assertRaises(RulePackError):public_view(self.catalog,[bad])

    def test_definitions_cannot_invent_text_rules_or_source(self):
        for change in [{'text':'Recompensa inventada'},{'start':True},{'end':99999},{'reward':10},{'id':'npc:archivo'}]:
            with self.assertRaises(RulePackError):prepare(self.source,[self.definition|change],'provided-adventure')
        with self.assertRaises(RulePackError):prepare(self.source,[self.definition,self.definition],'provided-adventure')
        with self.assertRaises(RulePackError):prepare(self.source,[self.definition],'verified-rules')
        bad=copy.deepcopy(self.catalog);bad['definitions'][0]['text']='Otro secreto'
        with self.assertRaises(RulePackError):validate(bad,self.source)
        with self.assertRaises(RulePackError):bind(self.catalog,'archivo',self.check|{'objective':'otro'},'request-1')
        with self.assertRaises(RulePackError):resolve(self.catalog,self.binding|{'sourceSha256':'0'*64},self.proof,7)
