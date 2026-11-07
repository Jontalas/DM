import copy
import unittest

import pf_shared_recovery as shared


class SharedRecoveryClockTests(unittest.TestCase):
    def start(self,*,npc_help=False,simultaneous=False,player_con=14):
        order=['player','npc']
        def patient(identifier,hp,con,helped,round_number,initiative):
            return {'id':identifier,'hp':hp,'constitution':con,'stable':True,'care':{
                'format':'cronicas-pf-care-3','assisted':helped,'round':round_number,
                'epoch':1,'initiative':initiative,'order':order[:]}}
        return {'epoch':1,'round':2,'initiative':'npc','order':order,
            'patients':[patient('player',-1,player_con,False,2,'player'),
                patient('npc',-3,12,npc_help,2 if simultaneous else 1,'player' if npc_help else 'npc')]}

    def test_earlier_npc_event_runs_before_players_hour_and_does_not_mutate_input(self):
        start=self.start(npc_help=True);before=copy.deepcopy(start);roles=[]
        result=shared.simulate(start,lambda role:roles.append(role) or 20)
        self.assertEqual(roles,[1,0]);self.assertEqual(result['seconds'],3600)
        self.assertEqual(result['status'],'conscious');self.assertEqual([p['hp'] for p in result['patients']],[-1,-3])
        self.assertTrue(all(p['recoveryState']['conscious'] for p in result['patients']));self.assertEqual(start,before)

    def test_simultaneous_npc_check_is_kept_after_pc_wakes(self):
        start=self.start(npc_help=True,simultaneous=True);raws=iter([20,1]);roles=[]
        result=shared.simulate(start,lambda role:roles.append(role) or next(raws))
        self.assertEqual(roles,[0,1]);self.assertEqual(result['status'],'conscious')
        self.assertFalse(result['patients'][1]['recoveryState']['conscious']);self.assertEqual(result['patients'][1]['hp'],-3)

    def test_future_npc_check_is_not_pulled_earlier_when_player_wakes(self):
        start=self.start();start['patients'][1]['care']['round']=2
        roles=[];result=shared.simulate(start,lambda role:roles.append(role) or 20)
        self.assertEqual(roles,[0]);self.assertNotIn('recoveryState',result['patients'][1]);self.assertEqual(result['seconds'],3600)

    def test_unassisted_checks_can_kill_both_without_fictitious_healing(self):
        start=self.start();start['patients'][1]['hp']=-1
        result=shared.simulate(start,lambda role:1)
        self.assertEqual(result['status'],'dead');self.assertEqual(result['seconds'],13*3600)
        self.assertEqual([p['hp'] for p in result['patients']],[-14,-12]);self.assertEqual(len(result['rolls']),24)

    def test_assisted_npc_rest_boundary_stops_before_unknown_night_effects(self):
        start=self.start(npc_help=True,player_con=20)
        result=shared.simulate(start,lambda role:1)
        self.assertEqual(result['status'],'rest-boundary');self.assertEqual(result['seconds'],6*3600)
        self.assertEqual([p['hp'] for p in result['patients']],[-7,-3]);self.assertEqual(len(result['rolls']),12)

    def test_awakened_npc_does_not_force_unnecessary_rest_or_player_decisions(self):
        start=self.start(npc_help=True)
        result=shared.simulate(start,lambda role:20 if role==1 else 1)
        self.assertEqual(result['status'],'dead');self.assertEqual(result['seconds'],13*3600)
        self.assertEqual(sum(role==1 for role,raw in result['rolls']),1)
        self.assertTrue(result['patients'][1]['recoveryState']['conscious']);self.assertEqual(result['patients'][1]['hp'],-3)

    def test_unknown_assistance_other_combats_and_long_encounters_reject_before_dice(self):
        bads=[]
        start=self.start();start['patients'][0]['care']=None;bads.append(start)
        start=self.start();start['patients'][0]['care']['assisted']=True;bads.append(start)
        start=self.start();start['round']=600;bads.append(start)
        start=self.start();start['patients'][1]['care']['epoch']=2;bads.append(start)
        for start in bads:
            before=copy.deepcopy(start)
            with self.assertRaises(ValueError):shared.simulate(start,lambda role:self.fail('Unsupported clock rolled'))
            self.assertEqual(start,before)
