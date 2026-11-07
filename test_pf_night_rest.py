import copy
import unittest
from unittest.mock import patch
import engine
import pf_encounters
import pf_night_rest as rest
import pf_scene_transition
from test_character_builder import choices


class PreparedNightRestTests(unittest.TestCase):
    def setUp(self):
        self.me={'id':'host','name':'Ana','host':True}
        self.state=engine.initial_state({})
        engine.apply_action(self.state,{'type':'create_character','choices':choices()},self.me)
        self.actor=self.state['characters'][0]['id']
        engine.apply_action(self.state,{'type':'enter_pf_encounter','encounter':pf_encounters.ID,
            'encounterVersion':'1.5.0','character':self.actor},self.me)

    def act(self,kind,**body):
        engine.apply_action(self.state,{'type':kind,**body},self.me)

    def agree(self):self.act('choose_pf_encounter',choice='parley')

    def wounded_victory(self):
        with patch('game_randomness.draw',side_effect=[1,20,18,3]),patch('game_randomness.initiative_tie',return_value=0):
            self.act('choose_pf_encounter',choice='combat')
        self.assertEqual(self.state['characters'][0]['hp'],13)
        with patch('game_randomness.draw',side_effect=[20,20,8,8]):
            self.act('attack',character=self.actor,target=self.state['characters'][1]['id'])
        self.assertEqual(self.state['pfEncounter']['phase'],'resolved')
        self.assertLessEqual(self.state['characters'][1]['hp'],-self.state['characters'][1]['abilities'][2])

    def test_organic_combat_then_sleep_heals_one_hp_and_preserves_every_other_stat(self):
        self.wounded_victory();before=copy.deepcopy(self.state)
        with patch('game_randomness.draw',side_effect=AssertionError('Sleep rolled dice')):
            self.act('rest_pf_night')
        self.assertEqual(self.state['characters'][0]['hp'],14)
        expected=copy.deepcopy(before['characters']);expected[0]['hp']=14
        self.assertEqual(self.state['characters'],expected)
        for key in ('pfEncounter','board','location','consequences','tokens'):self.assertEqual(self.state[key],before[key])
        self.assertEqual(self.state['worldTime'],rest.END_TIME)
        rest.validate_restored(self.state)

    def test_full_health_sleep_is_capped_and_guard_stays_awake_without_healing(self):
        self.agree();before=copy.deepcopy(self.state['characters'])
        self.act('rest_pf_night')
        self.assertEqual(self.state['characters'],before)
        result=self.state['pfNightRest']['result']
        self.assertEqual(result['healing']['amount'],0);self.assertEqual(result['npcActivity'],'awake-watch')
        before=copy.deepcopy(self.state)
        with self.assertRaises(ValueError):self.act('rest_pf_night')
        self.assertEqual(self.state,before)

    def test_sleep_is_a_player_decision_even_when_another_user_is_host(self):
        self.agree();before=copy.deepcopy(self.state)
        for host in (False,True):
            with self.assertRaises(PermissionError):rest.rest(self.state,{'type':'rest_pf_night'},self.me|{'id':'other','host':host})
        self.assertEqual(self.state,before)

    def test_preflight_rejects_every_unscheduled_patient_or_effect_without_mutation(self):
        self.agree();baseline=copy.deepcopy(self.state)
        for change in ('negative-player','dead-player','negative-guard','wounded-guard','condition','remote-patient',
            'pending','event','terrain','profile','armor','clock','combat','extra-hours','extended','second-combat'):
            self.state=copy.deepcopy(baseline)
            actor,npc=self.state['characters'];body={'type':'rest_pf_night'}
            if change=='negative-player':actor['hp']=-1
            elif change=='dead-player':actor['hp']=-actor['abilities'][2]
            elif change=='negative-guard':npc['hp']=-1
            elif change=='wounded-guard':npc['hp']=1
            elif change=='condition':npc['conditions']='Fatigado'
            elif change=='remote-patient':
                self.state['characters'].append(copy.deepcopy(npc)|{'id':'other','hp':-1,'sceneId':'other'})
            elif change=='pending':self.state['pending']=[{'reason':'Sin resolver'}]
            elif change=='event':self.state['consequences']=[{'interpreted':False}]
            elif change=='terrain':self.state['board']['terrain']={'2,2':'wall'}
            elif change=='profile':actor['creation']['manualOverride']=True
            elif change=='armor':actor['creation']['choices']['armor']='scale'
            elif change=='clock':self.state['worldTime']='Al día siguiente'
            elif change=='combat':self.state['board']['active']=True
            elif change=='extra-hours':body['hours']=80
            elif change=='extended':self.state['board']['round']=101
            elif change=='second-combat':self.state['board']['combatSerial']=2
            before=copy.deepcopy(self.state)
            with self.subTest(change=change),patch('game_randomness.draw',side_effect=AssertionError('Rejected sleep rolled')):
                with self.assertRaises(ValueError):rest.rest(self.state,body,self.me)
                self.assertEqual(self.state,before)

    def test_receipt_replays_and_rejects_altered_healing_time_and_orphans(self):
        self.wounded_victory();self.act('rest_pf_night');baseline=copy.deepcopy(self.state)
        for change in ('healing','time','origin','encounter','actor','missing','log','repeat-log'):
            altered=copy.deepcopy(baseline);receipt=altered['pfNightRest']
            if change=='healing':receipt['result']['healing']['hpAfter']+=1
            elif change=='time':receipt['result']['seconds']=1
            elif change=='origin':receipt['start']['hp']=0
            elif change=='encounter':receipt['encounterSha256']='0'*64
            elif change=='actor':receipt['character']='other'
            elif change=='missing':del altered['pfNightRest']
            elif change=='log':altered['messages'][-1]['nightRestSha256']='0'*64
            else:altered['messages'].append(copy.deepcopy(altered['messages'][-1]))
            with self.subTest(change=change),self.assertRaises(ValueError):rest.validate_restored(altered)
        self.assertEqual(self.state,baseline)

    def test_route_after_sleep_preserves_health_clock_and_can_be_copied(self):
        self.wounded_victory();self.act('rest_pf_night');before=copy.deepcopy(self.state)
        self.act('continue_pf_encounter')
        self.assertEqual(self.state['pfEncounter']['definition']['continuation']['version'],'1.1.0')
        self.assertEqual(self.state['worldTime'],before['worldTime'])
        self.assertEqual(self.state['characters'][0]['hp'],14)
        rest.validate_restored(self.state);pf_scene_transition.validate_restored(self.state)
        with self.assertRaises(ValueError):self.act('rest_pf_night')

    def test_previous_scenario_does_not_gain_sleep_and_context_omits_replay_inputs(self):
        import claude_dm
        self.agree();self.act('rest_pf_night')
        context=claude_dm.build_context(self.state,'Narra el resultado',[])
        self.assertNotIn('pfNightRest',context['state'])
        self.assertEqual(context['state']['nightRestResult'],self.state['pfNightRest']['result'])
        self.assertNotIn('nightRestResult',claude_dm.build_context(self.state,'Consulta',[],rules=True)['state'])
        self.state['pfNightRestView']={'completed':False,'reason':'INJECTED-VIEW'}
        self.assertNotIn('pfNightRestView',claude_dm.build_context(self.state,'Narra',[])['state'])
        state=copy.deepcopy(self.state);state.pop('pfNightRest')
        state['pfEncounter']['definition']=pf_encounters.definition('1.4.0')
        self.assertIn('no incluye',rest.limitation(state))
