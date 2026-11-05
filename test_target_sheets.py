import copy
import unittest
from unittest.mock import patch
from rule_pack_runtime import RulePack,RulePackError
from test_creation_profiles import profile_document


def target_document():
    data=profile_document();data['id']='original-target-sheets-example';data['requires'].append('target-sheets')
    data['sources'][0]['locator']='Reglas propias CC0: prueba 2d6 contra aptitud objetivo +5, coste de energía propio 1 y pérdida de energía objetivo 1 al acertar. No son reglas de Pathfinder.'
    roll={'ref':['rolls','pool','total']};difficulty={'op':'add','args':[{'ref':['target','talent']},5]};hit={'op':'ge','args':[roll,difficulty]}
    data['actions']['contest']={'label':'Prueba entre fichas propia','sources':['staged-source'],'target':True,'inputs':{},
        'requires':[{'op':'gt','args':[{'ref':['fields','energy']},0]},{'op':'gt','args':[{'ref':['target','energy']},0]}],
        'rolls':[{'id':'pool','count':2,'sides':6,'keep':'all'}],
        'effects':[{'field':'energy','value':{'op':'sub','args':[{'ref':['fields','energy']},1]}},
            {'field':'success','value':hit},{'scope':'target','field':'energy','when':hit,'value':{'op':'sub','args':[{'ref':['target','energy']},1]}}],
        'resultFields':['success']}
    return data


class TargetSheetTests(unittest.TestCase):
    def setUp(self):
        self.pack=RulePack(target_document())
        self.actor,_=self.pack.create_character('ana',physical={'aptitude':[1]})
        self.actor,_=self.pack.advance_character(self.actor,'training',{'role':'cronista','focus':1},'ana')
        self.target,_=self.pack.create_character('director',profile='support')

    def test_two_sheet_effects_and_triggers_use_confirmed_fields_without_mutating_inputs(self):
        before=copy.deepcopy((self.actor,self.target))
        actor,target,trace=self.pack.execute_targeted(self.actor,self.target,'contest',{},'ana',physical={'pool':[3,4]})
        self.assertEqual((self.actor,self.target),before)
        self.assertEqual(actor['fields']['energy'],2);self.assertEqual(target['fields']['energy'],1)
        self.assertEqual(trace['results'],{'success':True});self.assertEqual(trace['target']['changes']['energy'],{'before':2,'after':1})
        actor,target,trace=self.pack.execute_targeted(actor,target,'contest',{},'ana',physical={'pool':[3,4]})
        self.assertTrue(target['fields']['exhausted']);self.assertEqual(target['fields']['energy'],0)
        self.assertEqual(trace['target']['triggers'][0]['id'],'exhaustion')
        with patch('rule_pack_runtime.secrets.randbelow',side_effect=AssertionError('Invalid target rolled')):
            with self.assertRaises(RulePackError):self.pack.execute_targeted(actor,target,'contest',{},'ana')

    def test_miss_preview_and_individual_route_do_not_fake_target_execution(self):
        preview=self.pack.preview_targeted(self.actor,self.target,'contest',{},'ana');self.assertEqual(preview['rolls'][0]['count'],2)
        actor,target,trace=self.pack.execute_targeted(self.actor,self.target,'contest',{},'ana',physical={'pool':[1,1]})
        self.assertEqual(target['fields'],self.target['fields']);self.assertEqual(trace['target']['changes'],{})
        self.assertEqual(trace['results'],{'success':False});self.assertEqual(actor['fields']['energy'],2)
        with patch('rule_pack_runtime.secrets.randbelow',side_effect=AssertionError('Missing target rolled')):
            with self.assertRaises(RulePackError):self.pack.execute(self.actor,'contest',{},'ana')
            with self.assertRaises(RulePackError):self.pack.execute_targeted(self.actor,self.target,'explore',{},'ana')
        bad=copy.deepcopy(self.target);bad['package']['sha256']='0'*64
        with self.assertRaises(RulePackError):self.pack.preview_targeted(self.actor,bad,'contest',{},'ana')

    def test_scopes_require_capability_and_cannot_escape_into_creation_or_derived_fields(self):
        changes=[lambda d:d['requires'].remove('target-sheets'),lambda d:d['actions']['contest'].update(target=False),
            lambda d:d['actions']['contest']['effects'].append(copy.deepcopy(d['actions']['contest']['effects'][-1])),
            lambda d:d['actions']['contest']['effects'][-1].update(scope='other'),
            lambda d:d['creationProfiles']['support'].update(steps=['contest'])]
        for transform in changes:
            data=target_document();transform(data)
            with self.assertRaises(RulePackError):RulePack(data)

    def test_effects_read_original_snapshots_not_execution_order(self):
        data=target_document();action=data['actions']['contest'];action['rolls']=[];action['requires']=[]
        action['effects']=[{'field':'energy','value':1},{'field':'energy','scope':'target','value':{'ref':['fields','energy']}}]
        pack=RulePack(data);actor,_=pack.create_character('ana',physical={'aptitude':[1]})
        actor,_=pack.advance_character(actor,'training',{'role':'cronista','focus':1},'ana');target,_=pack.create_character('director',profile='support')
        result,other,_=pack.execute_targeted(actor,target,'contest',{},'ana')
        self.assertEqual(result['fields']['energy'],1);self.assertEqual(other['fields']['energy'],3)

    def test_target_trigger_failure_leaves_both_original_sheets_intact(self):
        data=target_document();data['fields']['npcflag']={'type':'boolean','label':'Marca propia','sources':['staged-source'],'initial':False}
        data['actions']['prepare-support']['effects'].append({'field':'npcflag','value':True})
        for identifier,before,after in [('cycle-a',1,2),('cycle-b',2,1)]:
            data['triggers'][identifier]={'label':'Ciclo de prueba','sources':['staged-source'],
                'when':{'op':'and','args':[{'ref':['fields','npcflag']},{'op':'eq','args':[{'ref':['fields','energy']},before]}]},
                'effects':[{'field':'energy','value':after}]}
        # Template starts with 2 energy; deactivate cycles at creation and enable
        # only for target resolution by requiring success already set on target.
        for identifier in ('cycle-a','cycle-b'):data['triggers'][identifier]['when']['args'].append({'ref':['fields','success']})
        data['actions']['contest']['effects'].append({'scope':'target','field':'success','value':True})
        pack=RulePack(data);actor,_=pack.create_character('ana',physical={'aptitude':[1]})
        actor,_=pack.advance_character(actor,'training',{'role':'cronista','focus':1},'ana');target,_=pack.create_character('director',profile='support')
        original=copy.deepcopy((actor,target))
        with self.assertRaisesRegex(RulePackError,'ciclo'):pack.execute_targeted(actor,target,'contest',{},'ana',physical={'pool':[3,4]})
        self.assertEqual((actor,target),original)
