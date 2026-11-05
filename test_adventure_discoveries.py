import copy
import unittest
from adventure_discoveries import prepare,validate,bind,resolve,public_view
from rule_pack_runtime import RulePackError
from unittest.mock import Mock,patch
import rule_pack_campaign as campaign
import rule_pack_director as director
from test_rule_pack_runtime import document
from test_rule_pack_narrative import reply
from test_rule_pack_objectives import goal


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
        self.assertEqual(prepare(self.source,[self.definition|{'field':'success_flag'}],'provided-adventure')['definitions'][0]['field'],'success_flag')
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


class DiscoveryCampaignTests(unittest.TestCase):
    def setUp(self):
        self.me={'id':'ana','name':'Ana','host':True,'campaign':'discovery-test'}
        state=campaign.execute_action(campaign.initial_state({}),{'type':'install_rule_pack','package':document('original-narrative-results-example'),'policy':'provided-rules'},self.me)
        state=campaign.execute_action(state,{'type':'create_pack_sheet','name':'Aria'},self.me)
        self.cid=state['characters'][0]['id'];self.source='Fuente propia CC0. La señal conduce al archivo. Otro secreto privado.'
        self.state=self.apply(state,'start_pack_adventure',answer=reply(objectiveUpdates=[goal()]),character=self.cid,
            sourceTitle='Escena propia',sourceText=self.source,sourcePolicy='provided-adventure')
        text='La señal conduce al archivo.';start=self.source.index(text)
        self.definitions=[{'id':'archivo','objective':'farol','field':'success','start':start,'end':start+len(text),'text':text}]

    def apply(self,state,kind,answer=None,**data):
        return campaign.execute_action(state,{'type':kind,**data},self.me,narrative_call=Mock(return_value=answer or reply()))

    def prepared(self):
        with patch.object(director,'propose',side_effect=AssertionError('Preparation called AI')):
            return self.apply(self.state,'prepare_pack_discoveries',definitions=self.definitions,policy='provided-adventure')

    def pending(self,state,linked=True):
        return self.apply(state,'talk_pack_adventure',character=self.cid,text='Examino la marca.',mode='action',
            answer=reply('intentar',objectiveCheck={'objective':'farol','field':'success'} if linked else {'objective':'','field':''}))

    def resolved(self,state,values):
        return self.apply(state,'resolve_pack_request',request=state['narrative']['pending']['id'],physical={'dice':values})

    def test_bound_reveal_copy_privacy_and_new_contract(self):
        state=self.prepared();campaign.validate_restored(state)
        self.assertEqual(campaign.public_view(state,self.me)['narrativeView']['discoveries'],[])
        self.assertNotIn('La señal conduce',str(campaign.public_view(state,self.me|{'host':False})))
        pending=self.pending(state);campaign.validate_restored(pending)
        self.assertEqual(len(pending['narrative']['pending']['discoveryBindings']),1)
        resolved=self.resolved(pending,[3,4]);campaign.validate_restored(resolved)
        public=campaign.public_view(resolved,self.me|{'host':False})
        self.assertEqual(public['narrativeView']['discoveries'][0]['text'],self.definitions[0]['text'])
        self.assertNotIn('Otro secreto privado',str(public))
        pack=campaign.runtime(resolved,self.me['campaign'])
        request=director.prepare(resolved,'continue',resolved['characters'][0],'','action',pack)['request']
        self.assertEqual(request['contract'],director.DISCOVERY_CONTRACT)
        self.assertEqual(request['verifiedResolution']['discoveriesRevealed'],request['confirmedDiscoveries'])
        with patch('rule_pack_runtime.secrets.randbelow',side_effect=AssertionError('Copy rolled')):
            copied=campaign.import_campaign(resolved,self.me|{'id':'eva'})
        self.assertEqual(copied['narrative']['discoveries'],resolved['narrative']['discoveries'])
        continued=self.apply(resolved,'continue_pack_adventure');campaign.validate_restored(continued)
        self.assertEqual(continued['narrative']['discoveries'],resolved['narrative']['discoveries'])

    def test_failed_unbound_edited_or_cancelled_requests_do_not_reveal(self):
        state=self.prepared()
        for linked,values in [(True,[1,1]),(False,[3,4])]:
            resolved=self.resolved(self.pending(state,linked),values);campaign.validate_restored(resolved)
            self.assertEqual(resolved['narrative']['discoveries']['receipts'],[])
        pending=self.pending(state)
        cancelled=self.apply(pending,'cancel_pack_request',request=pending['narrative']['pending']['id'])
        self.assertEqual(cancelled['narrative']['discoveries']['receipts'],[])
        bad=copy.deepcopy(pending);bad['narrative']['pending'].pop('discoveryBindings')
        with self.assertRaises(RulePackError):campaign.validate_restored(bad)
        with patch('rule_pack_runtime.secrets.randbelow',side_effect=AssertionError('Invalid binding rolled')):
            with self.assertRaises(RulePackError):self.apply(bad,'resolve_pack_request',request=bad['narrative']['pending']['id'])

    def test_tampered_receipts_source_and_preparation_permissions(self):
        state=self.prepared();resolved=self.resolved(self.pending(state),[3,4])
        changes=[lambda s:s['narrative']['discoveries']['receipts'].clear(),
            lambda s:s['messages'][-1].pop('discoveryReveals'),
            lambda s:s['narrative']['discoveries']['catalog']['definitions'][0].update(text='Inventado'),
            lambda s:s['narrative']['discoveries'].update(installedAt=len(s['messages'])-1)]
        for change in changes:
            bad=copy.deepcopy(resolved);change(bad)
            with self.assertRaises(RulePackError):campaign.validate_restored(bad)
        with self.assertRaises(PermissionError):campaign.execute_action(self.state,{'type':'prepare_pack_discoveries','definitions':self.definitions,'policy':'provided-adventure'},self.me|{'host':False})
        with self.assertRaises(RulePackError):self.apply(state,'prepare_pack_discoveries',definitions=self.definitions,policy='provided-adventure')
