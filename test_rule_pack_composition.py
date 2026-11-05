import copy
import unittest
from unittest.mock import patch
from rule_pack_composition import compose
from rule_pack_runtime import RulePack,RulePackError
from test_rule_pack_runtime import document


def blocks():
    first=document('original-pool-example');second=copy.deepcopy(first);second['version']='1.0.1'
    second['sources'].append({'id':'reserve-example','title':'Reserva del ejemplo propio','edition':'1','locator':'Reserva inicial 2; gastar un punto requiere reserva positiva.'})
    second['fields']['reserve']={'type':'integer','label':'Reserva','initial':2,'min':0,'max':2,'sources':['reserve-example']}
    second['actions']['use_reserve']={'label':'Usar reserva','sources':['reserve-example'],'inputs':{},
        'requires':[{'op':'gt','args':[{'ref':['fields','reserve']},0]}],'rolls':[],
        'effects':[{'field':'reserve','value':{'op':'sub','args':[{'ref':['fields','reserve']},1]}}]}
    second['coverage']['implemented'].append('Reserva del ejemplo propio')
    return first,second


class RulePackCompositionTests(unittest.TestCase):
    def test_same_engine_composes_data_and_preserves_both_actions_without_rng(self):
        first,second=blocks();before=copy.deepcopy([first,second])
        with patch('rule_pack_runtime.secrets.randbelow',side_effect=AssertionError('Composition rolled')):
            result=compose([first,second],'1.1.0')
            pack=RulePack(result['document']);sheet=pack.new_sheet('ana')
            sheet,_=pack.execute(sheet,'use_reserve',{},'ana')
            sheet,_=pack.execute(sheet,'attempt',{},'ana',physical={'pool':[3,4]})
        self.assertEqual(sheet['fields']['reserve'],1);self.assertEqual(sheet['fields']['energy'],2)
        self.assertEqual([first,second],before);self.assertEqual(len(result['document']['sources']),2)
        self.assertEqual(result['sourceVerification'],'unverified');self.assertEqual(result['stateMigration'],'not-performed')
        self.assertEqual(result['provenance']['packageSha256'],pack.digest)

    def test_input_order_never_selects_a_winner_or_changes_the_digest(self):
        first,second=blocks()
        self.assertEqual(compose([first,second],'1.1.0'),compose([second,first],'1.1.0'))

    def test_conflicts_and_cross_game_edition_license_changes_are_rejected(self):
        for key in ('id','edition','license','field','action','source'):
            first,second=blocks()
            if key=='id':second['id']='another-game'
            elif key=='edition':second['edition']='Another edition'
            elif key=='license':second['license']['attribution']='Another attribution'
            elif key=='field':second['fields']['energy']['initial']=2
            elif key=='action':second['actions']['attempt']['label']='Changed action'
            else:second['sources'][0]['locator']='Different source'
            with self.subTest(key=key),self.assertRaises(RulePackError):compose([first,second],'1.1.0')

    def test_same_definition_can_retain_additional_sources_without_silent_replacement(self):
        first,second=blocks();second['fields']['energy']['sources'].append('reserve-example')
        result=compose([first,second],'1.1.0')
        self.assertEqual(result['document']['fields']['energy']['sources'],['original-example','reserve-example'])
        self.assertEqual(result['document']['coverage']['pending'],first['coverage']['pending'])
        old=RulePack(first).new_sheet('ana')
        with self.assertRaises(RulePackError):RulePack(result['document']).view(old)

    def test_duplicate_inputs_version_regressions_and_aggregate_bounds_reject(self):
        first,second=blocks()
        for data,version in [([first],'1.1.0'),([first,first],'1.1.0'),([first,second],'1.0.0'),([first,second],'invalid')]:
            with self.assertRaises(RulePackError):compose(data,version)
        first['coverage']['pending']=[f'Gap {n}' for n in range(60)]
        second['coverage']['pending']=[f'Other gap {n}' for n in range(60)]
        with self.assertRaises(RulePackError):compose([first,second],'1.1.0')


if __name__=='__main__':unittest.main()
