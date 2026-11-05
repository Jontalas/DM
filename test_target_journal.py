import copy
import unittest
from unittest.mock import Mock,patch
import actor_references
import target_journal
import rule_pack_campaign as campaign
import rule_pack_director as director
from rule_pack_runtime import RulePackError
from test_target_sheets import target_document
from test_rule_pack_world import npc
from test_rule_pack_narrative import reply


class TargetJournalTests(unittest.TestCase):
    def setUp(self):
        self.me={'id':'ana','name':'Ana','host':True,'campaign':'target-journal'}
        state=campaign.execute_action(campaign.initial_state({}),{'type':'install_rule_pack','package':target_document(),'policy':'provided-rules'},self.me)
        state=campaign.execute_action(state,{'type':'create_pack_sheet','name':'Aria','physical':{'aptitude':[1]}},self.me);cid=state['characters'][0]['id']
        state=campaign.execute_action(state,{'type':'advance_pack_creation','character':cid,'step':'training','inputs':{'role':'cronista','focus':1}},self.me)
        state=campaign.execute_action(state,{'type':'start_pack_adventure','character':cid},self.me,narrative_call=Mock(return_value=reply(npcUpdates=[npc(),npc('sombra',known=False,public='')])))
        self.state=campaign.execute_action(state,{'type':'create_pack_actor','actor':'a'*24,'npc':'arda','profile':'support',
            'stages':[{'inputs':{},'physical':{}}],'publicFields':[],'policy':'provided-profile'},self.me)
        self.cid=cid;self.pack=campaign.runtime(self.state,self.me['campaign'])
        self.initial={cid:copy.deepcopy(self.state['characters'][0]['sheet'])}

    def resolve(self,state,values):
        result=copy.deepcopy(state);binding=actor_references.select(result,self.cid,'a'*24,self.me,self.pack)
        player,other,trace=self.pack.execute_targeted(result['characters'][0]['sheet'],result['actors'][0]['sheet'],'contest',{},self.me['id'],physical={'pool':values})
        position=len(result['messages']);public=copy.deepcopy(trace);public.pop('target')
        result['messages'].append({'kind':'pack-action','character':self.cid,'actor':'ana','speaker':'Ana','host':True,'time':1,
            'action':'contest','inputs':{},'trace':public,'targetRef':{'id':binding['target'],'npc':binding['npc']}})
        result.setdefault('targetResolutions',[]).append({'message':position,'binding':binding,'inputs':{},'trace':trace})
        result['characters'][0]['sheet']=player;result['actors'][0]['sheet']=other;return result

    def test_replays_two_sheets_across_miss_and_hit_with_no_new_dice(self):
        state=self.resolve(self.resolve(self.state,[1,1]),[3,4]);original=copy.deepcopy(state)
        with patch('rule_pack_runtime.secrets.randbelow',side_effect=AssertionError('Journal rolled')):
            result=target_journal.replay(state,self.pack,self.initial)
        self.assertEqual(result['players'][self.cid],state['characters'][0]['sheet'])
        self.assertEqual(result['actors']['a'*24],state['actors'][0]['sheet']);self.assertEqual(state,original)
        self.assertNotIn('target',state['messages'][-1]['trace'])
        campaign.validate_restored(state)
        with patch('rule_pack_runtime.secrets.randbelow',side_effect=AssertionError('Copy rerolled target')):
            copied=campaign.import_campaign(state,self.me|{'id':'eva'})
        self.assertEqual(copied['actors'],state['actors']);self.assertEqual(copied['characters'][0]['owner'],'eva')
        public=campaign.public_view(copied,self.me|{'id':'eva','host':False})
        self.assertNotIn('targetResolutions',public);self.assertNotIn('actors',public)
        self.assertEqual(public['messages'][-1]['targetRef']['npc'],'arda')

    def test_tampering_missing_proof_wrong_target_and_future_actor_rejected(self):
        state=self.resolve(self.state,[3,4])
        changes=[lambda s:s['targetResolutions'].clear(),lambda s:s['actors'][0]['sheet']['fields'].update(energy=2),
            lambda s:s['targetResolutions'][0]['trace']['target']['changes']['energy'].update(after=0),
            lambda s:s['messages'][-1]['targetRef'].update(npc='other'),
            lambda s:s['actors'][0].update(introducedAt=len(s['messages'])),
            lambda s:s['actors'][0].pop('introducedAt'),
            lambda s:s['targetResolutions'][0]['binding'].update(targetRevision=99),
            lambda s:s['messages'][-1]['trace'].update(target=s['targetResolutions'][0]['trace']['target'])]
        for change in changes:
            bad=copy.deepcopy(state);change(bad)
            with self.assertRaises(RulePackError):target_journal.replay(bad,self.pack,self.initial)
            with self.assertRaises(RulePackError):campaign.validate_restored(bad)

    def test_duplicate_out_of_order_and_unrelated_public_event_rejected(self):
        state=self.resolve(self.resolve(self.state,[1,1]),[3,4])
        for records in [list(reversed(state['targetResolutions'])),[state['targetResolutions'][0]]*2]:
            bad=copy.deepcopy(state);bad['targetResolutions']=records
            with self.assertRaises(RulePackError):target_journal.replay(bad,self.pack,self.initial)
        bad=copy.deepcopy(state);bad['targetResolutions'][0]['message']=0
        with self.assertRaises(RulePackError):target_journal.replay(bad,self.pack,self.initial)

    def test_private_target_statistics_cannot_define_public_dice_shape(self):
        action=copy.deepcopy(self.pack.document()['actions']['contest'])
        action['rolls'][0]['count']={'ref':['target','talent']}
        with self.assertRaisesRegex(RulePackError,'dato privado'):target_journal.public_roll_shape(action,[])
        target_journal.public_roll_shape(action,['talent'])
        action['rolls'][0]['count']=2;action['rolls'][0]['when']={'op':'gt','args':[{'ref':['target','energy']},0]}
        with self.assertRaises(RulePackError):target_journal.public_roll_shape(action,['talent'])

    def test_individual_action_and_later_private_preparation_keep_chronology(self):
        state=copy.deepcopy(self.state);sheet,trace=self.pack.execute(state['characters'][0]['sheet'],'explore',{},self.me['id'],physical={'pool':[1,1]})
        state['characters'][0]['sheet']=sheet
        state['messages'].append({'kind':'pack-action','character':self.cid,'actor':'ana','speaker':'Ana','host':True,'time':1,'action':'explore','inputs':{},'trace':trace})
        state=self.resolve(state,[3,4]);campaign.validate_restored(state)
        state=campaign.execute_action(state,{'type':'create_pack_actor','actor':'b'*24,'npc':'sombra','profile':'support',
            'stages':[{'inputs':{},'physical':{}}],'publicFields':[],'policy':'provided-profile'},self.me)
        campaign.validate_restored(state)
        self.assertGreater(state['actors'][1]['introducedAt'],state['targetResolutions'][0]['message'])
        self.assertEqual(state['actors'][0]['sheet']['fields']['energy'],1)
        self.assertEqual(len(campaign.public_view(state,self.me)['actorViews']),1)

    def test_target_continuation_receives_only_known_shared_fields(self):
        state=self.resolve(self.state,[3,4]);state['narrative']['continuation']={'character':self.cid,'message':len(state['messages'])-1}
        campaign.validate_restored(state)
        request=director.prepare(state,'continue',state['characters'][0],'','action',self.pack)['request']
        self.assertEqual(request['contract'],director.TARGET_CONTRACT)
        self.assertEqual(request['verifiedResolution']['target'],{'id':'a'*24,'npc':'arda','name':'Arda','fields':{},'changes':{}})
        self.assertNotIn('targetResolutions',request);self.assertNotIn('confirmedResult',request)
        self.assertNotIn('sheet',request['verifiedResolution']['target'])
        state['actors'][0]['publicFields']=['energy']
        request=director.prepare(state,'continue',state['characters'][0],'','action',self.pack)['request']
        self.assertEqual(request['verifiedResolution']['target']['fields']['energy'],{'label':'Energía','value':1})
        later=self.resolve(state,[1,1])
        with self.assertRaises(RulePackError):campaign.validate_restored(later)
