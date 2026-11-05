import copy
import json
import unittest
from unittest.mock import patch
import rule_pack_campaign as campaign
from rule_pack_runtime import RulePack,RulePackError
from rule_pack_composition import compose
from test_rule_pack_runtime import document


class RulePackCreationTests(unittest.TestCase):
    def setUp(self):
        self.doc=document('original-creation-example');self.pack=RulePack(self.doc)
        self.me={'id':'ana','name':'Ana','campaign':'creation-room','host':True}

    def test_choices_and_all_creation_dice_ranges_are_calculated_from_data(self):
        for role in ('vigía','cronista'):
            for focus in range(2 if role=='vigía' else 3):
                for die in range(1,7):
                    with patch('rule_pack_runtime.secrets.randbelow',side_effect=AssertionError('Physical dice rolled')):
                        sheet,trace=self.pack.create_character('ana',{'role':role,'focus':focus},physical={'aptitude':[die]})
                    self.assertEqual(sheet['fields']['talent'],die+focus)
                    self.assertEqual(sheet['fields']['role'],role);self.assertEqual(sheet['revision'],1)
                    self.assertEqual(trace['rolls']['aptitude']['origin'],'physical')

    def test_illegal_choice_and_repeated_creation_reject_before_randomness(self):
        with patch('rule_pack_runtime.secrets.randbelow',side_effect=AssertionError('Rejected creation rolled')):
            for inputs in ({},{'role':'vigía','focus':2},{'role':'inventado'},{'role':'cronista','focus':True}):
                with self.assertRaises(RulePackError):self.pack.create_character('ana',inputs)
            for physical in ({'aptitude':[7]},{'aptitude':[1,2]},{'unknown':[1]}):
                with self.assertRaises(RulePackError):self.pack.create_character('ana',{'role':'cronista'},physical=physical)
            sheet,_=self.pack.create_character('ana',{'role':'cronista'},physical={'aptitude':[4]})
            with self.assertRaises(RulePackError):self.pack.execute(sheet,'generate',{'role':'cronista'},'ana')
            with self.assertRaises(RulePackError):self.pack.execute(sheet,'generate',{'role':'cronista'},'ana',creating=True)
            with self.assertRaises(RulePackError):self.pack.execute(self.pack.new_sheet('ana'),'explore',{},'ana',creating=True)
            with self.assertRaises(RulePackError):self.pack.execute(self.pack.new_sheet('ana'),'explore',{},'ana')

    def test_creation_definition_and_capability_are_validated(self):
        for mutation in ('missing','host','capability','shape'):
            doc=copy.deepcopy(self.doc)
            if mutation=='missing':doc['creation']['action']='absent'
            elif mutation=='host':doc['actions']['generate']['permission']='host'
            elif mutation=='capability':doc['requires'].remove('character-creation')
            else:doc['creation']['extra']='unknown'
            with self.assertRaises(RulePackError):RulePack(doc)

    def test_authoring_examples_must_create_first_without_hidden_randomness(self):
        import rule_pack_authoring as authoring
        import test_rule_pack_authoring as fixture
        raw=fixture.request();raw['document']['pages'][0]['text']=self.doc['sources'][0]['locator']
        prepared=authoring.prepare_input(raw);data=copy.deepcopy(self.doc);data.update(raw['identity'])
        data['license']=raw['license'];data['sources']=prepared['sources']
        for group in ('fields','actions','triggers'):
            for spec in data[group].values():spec['sources']=[prepared['sources'][0]['id']]
        steps=[{'action':'generate','inputs':{'role':'cronista','focus':2},'physical':{'aptitude':[4]}},
            {'action':'explore','inputs':{},'physical':{'pool':[3,4]}}]
        reply={'status':'candidate','packageJson':json.dumps(data),'issues':[],
            'examples':[{'name':'Crear y explorar','stepsJson':json.dumps(steps),'expectedJson':json.dumps({'talent':6,'energy':2,'success':True})}]}
        with patch('rule_pack_runtime.secrets.randbelow',side_effect=AssertionError('Example rolled')):
            report=authoring.validate_reply(prepared,reply)
            authoring.validate_record({'request':raw,'sha256':prepared['sha256'],'sourceScheme':prepared['sourceScheme'],'report':report})
            for bad_steps in (steps[1:],steps[:1]*2,[steps[0]|{'physical':{}}]):
                altered=copy.deepcopy(reply);altered['examples'][0]['stepsJson']=json.dumps(bad_steps)
                with self.assertRaises(RulePackError):authoring.validate_reply(prepared,altered)

    def test_campaign_recovery_replays_creation_and_rejects_tampering(self):
        state=campaign.execute_action(campaign.initial_state({}),{'type':'install_rule_pack','package':self.doc,'policy':'provided-rules'},self.me)
        state=campaign.execute_action(state,{'type':'create_pack_sheet','name':'Aria','inputs':{'role':'cronista','focus':2},'physical':{'aptitude':[4]}},self.me)
        identifier=state['characters'][0]['id']
        state=campaign.execute_action(state,{'type':'run_pack_action','character':identifier,'action':'explore','inputs':{},'physical':{'pool':[3,4]}},self.me)
        with patch('rule_pack_runtime.secrets.randbelow',side_effect=AssertionError('Recovery rolled')):
            campaign.validate_restored(state)
            recovered=campaign.import_campaign(state,self.me|{'id':'eva'})
            self.assertEqual(recovered['characters'][0]['owner'],'eva')
            for mutation in ('missing','inputs','dice','talent','trace'):
                bad=copy.deepcopy(state);char=bad['characters'][0]
                if mutation=='missing':char.pop('creation')
                elif mutation=='inputs':char['creation']['inputs']['focus']=0
                elif mutation=='dice':char['creation']['trace']['rolls']['aptitude']['values']=[]
                elif mutation=='talent':char['sheet']['fields']['talent']=8
                else:char['creation']['trace']['changes']={}
                with self.assertRaises(RulePackError):campaign.validate_restored(bad)

    def test_composition_preserves_creator_and_rejects_competing_creator(self):
        other=copy.deepcopy(self.doc);other.pop('creation');other['actions'].pop('generate');other['coverage']['implemented'].append('Segundo bloque de prueba')
        for ordered in ([self.doc,other],[other,self.doc]):
            result=compose(ordered,'1.1.0')['document'];self.assertEqual(result['creation'],self.doc['creation'])
            self.assertEqual(RulePack(result).creation,'generate')
        other['actions']['other_creator']=copy.deepcopy(self.doc['actions']['generate']);other['creation']={'action':'other_creator'}
        with self.assertRaises(RulePackError):compose([self.doc,other],'1.1.0')
