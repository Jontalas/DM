import copy,json,subprocess,unittest,shutil
from unittest.mock import patch
from character_builder import CATALOG,build
from engine import initial_state,apply_action

HOST={'id':'host','name':'Ana','host':True}
GUEST={'id':'guest','name':'Luis','host':False}


def choices(preset='guardian'):
    return {**copy.deepcopy(CATALOG['presets'][preset]),'name':'Aria','race':'human','class':'fighter','level':1,
        'favored':'hp','feats':['focus','initiative','toughness'],'skills':['climb','intimidate','perception'],'languages':[]}


class CharacterBuilderTests(unittest.TestCase):
    def test_guardian_is_ready_for_checks_and_melee(self):
        data,creation=build(choices());d=creation['details']
        self.assertEqual(data['abilities'],[18,14,14,10,12,8])
        self.assertEqual((data['maxHp'],data['ac'],data['attack'],data['damage'],data['initiative']),(16,18,6,'1d8+4',6))
        self.assertEqual(data['saves'],[4,2,1]);self.assertEqual(data['meleeProfile'],{'flatAc':16,'criticalMin':19,'multiplier':2})
        self.assertEqual((data['speed'],d['penalty'],d['pointCost']),(6,4,20))
        self.assertEqual(next(s['total'] for s in data['skillTotals'] if s['name']=='Trepar'),4)
        self.assertNotIn('Saber (dungeons)',[s['name'] for s in data['skillTotals']])
        self.assertEqual(d['coins'],[47,3,8]);self.assertEqual(d['weight'],6116)

    def test_two_handed_damage_critical_and_shield_constraints(self):
        c=choices('vanguard');c['abilities'][0]=15
        data,_=build(c);self.assertEqual(data['damage'],'2d6+4')  # Strength 17 => floor(3 * 1.5).
        c['shield']='light'
        with self.assertRaises(ValueError):build(c)
        axe,_=build(choices('sentinel'));self.assertEqual(axe['meleeProfile']['multiplier'],3)
        self.assertEqual((axe['maxHp'],axe['speed']),(18,4))

    def test_feats_skill_ranks_and_languages_recalculate(self):
        c=choices();c['abilities']=[14,12,14,14,10,10];c['feats']=['initiative','fortitude','will'];c['favored']='skill'
        c['skills']=['climb','swim','ride','perception','engineering','animals'];c['languages']=['Élfico','Enano']
        data,creation=build(c)
        self.assertEqual(creation['details']['skillPoints'],6)
        self.assertEqual((data['maxHp'],data['attack'],data['saves']),(12,4,[6,1,2]))
        self.assertEqual(next(s['total'] for s in data['skillTotals'] if s['name']=='Saber (ingeniería)'),6)
        c['skills'].pop()
        with self.assertRaises(ValueError):build(c)
        c['skills'].append('animals');c['languages']=[]
        with self.assertRaises(ValueError):build(c)

    def test_load_and_negative_dexterity_do_not_stack_penalties_or_erase_penalties(self):
        c=choices();c['abilities']=[10,18,10,10,10,10];c['bonus']=1;c['armor']='scale'
        data,d=build(c);d=d['details']
        self.assertEqual(d['load'],2);self.assertEqual(d['dexAc'],1)
        self.assertEqual(d['penalty'],6);self.assertEqual(data['speed'],4)
        c['abilities']=[10,7,10,10,10,10];c['bonus']=0
        data,d=build(c);self.assertEqual(d['details']['dexAc'],-2);self.assertEqual(data['meleeProfile']['flatAc'],data['ac'])

    def test_invalid_choices_rejected_without_state_changes(self):
        variants=[{'abilities':[18]*6},{'abilities':[True]*6},{'race':'elf'},{'class':'wizard'},{'level':2},
            {'weapon':'invented'},{'feats':['toughness','fortitude','will']},{'feats':['focus']*3},{'skills':[]},
            {'skills':['climb','climb','perception']},{'languages':['Druídico']},{'name':''},{'abilities':[7,10,10,10,10,10]}]
        for change in variants:
            with self.subTest(change=change),self.assertRaises(ValueError):build({**choices(),**change})
        state=initial_state({});before=copy.deepcopy(state)
        with self.assertRaises(PermissionError):apply_action(state,{'type':'create_character','choices':choices(),'enemy':True},GUEST)
        self.assertEqual(state,before)

    def test_server_calculates_ownership_profile_and_provenance(self):
        state=initial_state({});c=choices();c.update({'attack':999,'owner':'host','hp':999})
        apply_action(state,{'type':'create_character','choices':c},GUEST)
        created=state['characters'][0];self.assertEqual(created['owner'],'guest');self.assertFalse(created['enemy'])
        self.assertEqual(created['attack'],6);self.assertIn('creation',created)
        with patch('engine.dice',return_value=[12]):apply_action(state,{'type':'check','character':created['id'],'checkKind':'ability','key':'str'},GUEST)
        self.assertEqual(state['messages'][-1]['check']['total'],16)
        apply_action(state,{'type':'character','character':copy.deepcopy(created)},GUEST)
        self.assertTrue(state['characters'][0]['creation']['manualOverride'])

    def test_generated_player_and_adversary_enter_automatic_combat(self):
        state=initial_state({})
        apply_action(state,{'type':'create_character','choices':choices()},GUEST)
        apply_action(state,{'type':'create_character','choices':{**choices(),'name':'Bandido'},'enemy':True},HOST)
        with patch('engine.dice',return_value=[12]):apply_action(state,{'type':'combat'},HOST)
        player,enemy=state['characters'];state['board']['turn']=next(i for i,v in enumerate(state['board']['order']) if v['id']==player['id'])
        physical={'attack':[18],'damage':[4]}
        apply_action(state,{'type':'attack','character':player['id'],'target':enemy['id'],'physical':physical},HOST)
        self.assertEqual(enemy['hp'],8)

    @unittest.skipUnless(shutil.which('node'),'Node es necesario para contrastar la vista previa local')
    def test_browser_preview_matches_authoritative_python_calculation(self):
        cases=[]
        for preset in CATALOG['presets']:
            for armor in CATALOG['armors']:
                for bonus in range(6):
                    c=choices(preset);c.update(armor=armor,bonus=bonus)
                    mod=(c['abilities'][3]+(2 if bonus==3 else 0)-10)//2
                    count=max(1,2+mod)+1
                    c['skills']=list(CATALOG['skills'])[:count];c['languages']=CATALOG['languages'][:max(0,mod)]
                    cases.append(c)
        script="const fs=require('fs'),r=require('./static/creation-rules.js'),c=require('./static/creation-catalog.json');process.stdout.write(JSON.stringify(JSON.parse(fs.readFileSync(0,'utf8')).map(x=>r.calculate(c,x))));"
        output=subprocess.run(['node','-e',script],input=json.dumps(cases),text=True,encoding='utf-8',capture_output=True,check=True)
        for c,preview in zip(cases,json.loads(output.stdout)):
            data,creation=build(c)
            for key,value in preview['data'].items():self.assertEqual(data[key],value,(c,key))
            self.assertEqual(creation['details'],preview['details']);self.assertEqual(preview['errors'],[])


if __name__=='__main__':unittest.main()
