import copy
import json
from pathlib import Path
import unittest
from unittest.mock import Mock,patch
from rule_pack_runtime import RulePack,RulePackError,read_document


ROOT=Path(__file__).parent/'test_fixtures'/'rule_packs'


def document(name):return json.loads((ROOT/(name+'.json')).read_text(encoding='utf-8'))
def field(name):return {'ref':['fields',name]}
def roll(name,prop='total'):return {'ref':['rolls',name,prop]}
def op(name,*args):return {'op':name,'args':list(args)}


class RulePackRuntimeTests(unittest.TestCase):
    def test_same_interpreter_preserves_different_games_natural_die_rules(self):
        cairn=RulePack((ROOT/'cairn-saves.json').read_bytes())
        base=cairn.new_sheet('ana')
        base,_=cairn.execute(base,'generate_attribute',{},'ana',physical={'ability':[4,4,4]})
        for target in range(3,25):
            sheet=copy.deepcopy(base);sheet['fields']['dex']=target
            for raw in range(1,21):
                resolved,trace=cairn.execute(sheet,'save',{},'ana',physical={'save':[raw]})
                self.assertEqual(resolved['fields']['success'],raw==1 or raw!=20 and raw<=target)
                self.assertEqual(trace['rolls']['save']['origin'],'physical')
        pf=RulePack((ROOT/'pathfinder-skill-check.json').read_text(encoding='utf-8'))
        for bonus in (-4,0,4):
            sheet=pf.new_sheet('ana');sheet['fields']['bonus']=bonus
            for dc in (0,5,15,25,40):
                for raw in range(1,21):
                    resolved,_=pf.execute(sheet,'check',{'dc':dc},'ana',physical={'d20':[raw]})
                    self.assertEqual(resolved['fields']['success'],raw+bonus>=dc)
                    self.assertEqual(pf.view(resolved)['fields']['margin'],raw+bonus-dc)

    def test_new_json_package_can_use_resources_tables_and_automatic_conditions(self):
        data=document('original-pool-example');data['id']='another-imported-game'
        engine=RulePack(json.dumps(data));sheet=engine.new_sheet('ana')
        for dice,success in [([3,4],True),([1,1],False),([6,6],True)]:
            sheet,trace=engine.execute(sheet,'attempt',{},'ana',physical={'pool':dice})
            self.assertEqual(sheet['fields']['success'],success)
        self.assertEqual(sheet['fields']['energy'],0);self.assertTrue(sheet['fields']['exhausted'])
        self.assertEqual(trace['triggers'][0]['id'],'exhaustion')
        draw=Mock(side_effect=AssertionError('Failed requirement rolled'))
        before=copy.deepcopy(sheet)
        with self.assertRaises(RulePackError):engine.execute(sheet,'attempt',{},'ana',draw=draw)
        draw.assert_not_called();self.assertEqual(sheet,before)

    def test_views_and_formula_queries_do_not_roll_or_change_state(self):
        engine=RulePack(document('pathfinder-skill-check'));sheet=engine.new_sheet('ana');before=copy.deepcopy(sheet)
        with patch('rule_pack_runtime.secrets.randbelow',side_effect=AssertionError('Read-only operation rolled')):
            for _ in range(20):self.assertEqual(engine.view(sheet)['fields']['margin'],-15)
        self.assertEqual(sheet,before);self.assertNotIn('margin',sheet['fields'])

    def test_packages_and_versions_are_content_bound_and_callers_cannot_mutate_them(self):
        data=document('original-pool-example');engine=RulePack(data);sheet=engine.new_sheet('ana')
        data['fields']['energy']['initial']=99
        exported=engine.document();exported['fields']['energy']['initial']=99
        self.assertEqual(engine.new_sheet('ana')['fields']['energy'],3)
        modified=engine.document();modified['name']='Changed metadata'
        with self.assertRaises(RulePackError):RulePack(modified).view(sheet)
        sorted_copy=RulePack(json.dumps(engine.document(),sort_keys=True))
        self.assertEqual(sorted_copy.digest,engine.digest)
        a,t=engine.execute(sheet,'attempt',{},'ana',physical={'pool':[3,4]})
        b,u=sorted_copy.execute(sheet,'attempt',{},'ana',physical={'pool':[3,4]})
        self.assertEqual((a,t),(b,u))

    def test_role_inputs_and_physical_dice_are_validated_before_any_randomness(self):
        engine=RulePack(document('original-pool-example'));sheet=engine.new_sheet('ana');before=copy.deepcopy(sheet)
        draw=Mock(side_effect=AssertionError('Invalid action rolled'))
        with self.assertRaises(PermissionError):engine.execute(sheet,'attempt',{},'other',host=True,draw=draw)
        for arguments in [dict(inputs={'energy':3}),dict(inputs={},physical={'pool':[True,6]}),
                dict(inputs={},physical={'pool':[7,1]}),dict(inputs={},physical={'unknown':[1]})]:
            with self.assertRaises(RulePackError):engine.execute(sheet,'attempt',actor='ana',draw=draw,**arguments)
        self.assertEqual(sheet,before);draw.assert_not_called()

    def test_unknown_operators_capabilities_and_external_references_are_rejected(self):
        for change in ('operator','capability','reference','source','derived-write'):
            data=document('pathfinder-skill-check')
            if change=='operator':data['fields']['margin']['derive']=op('exec','__import__("os")')
            elif change=='capability':data['requires'].append('python-code')
            elif change=='reference':data['fields']['margin']['derive']={'ref':['environment','SECRET']}
            elif change=='source':data['actions']['check']['sources']=['invented-book']
            else:data['actions']['check']['effects'].append({'field':'margin','value':0})
            with self.assertRaises(RulePackError):RulePack(data)

    def test_formula_cycles_table_overlap_and_non_integer_numbers_are_rejected(self):
        data=document('pathfinder-skill-check');data['fields']['margin']['derive']=field('margin')
        with self.assertRaises(RulePackError):RulePack(data)
        data=document('original-pool-example');data['tables']['outcomes']['rows'][1]['min']=6
        with self.assertRaises(RulePackError):RulePack(data)
        data=document('original-pool-example');data['tables']['outcomes']['rows'][1]['min']='seven'
        with self.assertRaises(RulePackError):RulePack(data)
        data=document('original-pool-example');data['fields']['energy']['initial']=True
        with self.assertRaises(RulePackError):RulePack(data)
        with self.assertRaises(RulePackError):read_document('{"format":1,"format":2}')
        with self.assertRaises(RulePackError):read_document('{"value":NaN}')

    def test_trigger_cycle_or_uncatalogued_table_result_rolls_back_every_effect(self):
        data=document('original-pool-example')
        data['triggers']['a']={'label':'Toggle up','sources':['original-example'],'when':op('eq',field('energy'),2),'effects':[{'field':'energy','value':1}]}
        data['triggers']['b']={'label':'Toggle down','sources':['original-example'],'when':op('eq',field('energy'),1),'effects':[{'field':'energy','value':2}]}
        engine=RulePack(data);sheet=engine.new_sheet('ana');before=copy.deepcopy(sheet)
        with self.assertRaises(RulePackError):engine.execute(sheet,'attempt',{},'ana',physical={'pool':[3,4]})
        self.assertEqual(sheet,before)
        data=document('original-pool-example');data['tables']['outcomes']['rows'][0]['max']=5;data['tables']['outcomes']['rows'][1]['min']=8
        engine=RulePack(data);sheet=engine.new_sheet('ana');before=copy.deepcopy(sheet)
        with self.assertRaises(RulePackError):engine.execute(sheet,'attempt',{},'ana',physical={'pool':[3,4]})
        self.assertEqual(sheet,before)

    def test_highest_lowest_and_conditional_rolls_need_no_game_specific_code(self):
        for keep,total in [('highest',10),('lowest',5)]:
            data=document('original-pool-example');data['actions']['attempt']['rolls'][0].update(count=3,keep=keep,keepCount=2)
            engine=RulePack(data);sheet,trace=engine.execute(engine.new_sheet('ana'),'attempt',{},'ana',physical={'pool':[1,6,4]})
            self.assertEqual(sheet['fields']['total'],total)
            self.assertEqual(trace['rolls']['pool']['values'],[1,6,4])
        data=document('original-pool-example')
        data['fields']['wound']={'type':'integer','label':'Example wound','initial':0,'min':0,'max':4,'sources':['original-example']}
        data['actions']['attempt']['rolls'].append({'id':'injury','count':1,'sides':4,'keep':'all','when':op('lt',roll('pool'),7)})
        data['actions']['attempt']['effects'].append({'field':'wound','value':op('if',roll('injury','rolled'),roll('injury'),0)})
        engine=RulePack(data)
        for dice,wound,calls in [([6,6],0,2),([1,1,4],4,3)]:
            draw=Mock(side_effect=dice)
            sheet,trace=engine.execute(engine.new_sheet('ana'),'attempt',{},'ana',draw=draw)
            self.assertEqual(sheet['fields']['wound'],wound);self.assertEqual(draw.call_count,calls)
        draw=Mock(side_effect=AssertionError('Invalid future physical die rolled'))
        with self.assertRaises(RulePackError):engine.execute(engine.new_sheet('ana'),'attempt',{},'ana',physical={'injury':[5]},draw=draw)
        draw.assert_not_called()

    def test_effect_batches_are_simultaneous_and_budget_limits_precede_rng(self):
        data=document('original-pool-example')
        data['fields']['total']['initial']=2
        data['actions']['swap']={'label':'Swap example values','sources':['original-example'],'inputs':{},'requires':[],'rolls':[],
            'effects':[{'field':'energy','value':field('total')},{'field':'total','value':field('energy')}]}
        engine=RulePack(data);sheet,_=engine.execute(engine.new_sheet('ana'),'swap',{},'ana')
        self.assertEqual((sheet['fields']['energy'],sheet['fields']['total']),(2,3))
        data['actions']['attempt']['rolls'][0]['count']=101
        engine=RulePack(data);draw=Mock(side_effect=AssertionError('Excessive dice rolled'))
        with self.assertRaises(RulePackError):engine.execute(engine.new_sheet('ana'),'attempt',{},'ana',draw=draw)
        draw.assert_not_called()
