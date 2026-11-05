import copy
import unittest
from unittest.mock import patch
import rule_pack_actors as actors
from rule_pack_runtime import RulePack,RulePackError
from test_creation_profiles import profile_document
from test_rule_pack_world import npc
import rule_pack_campaign as campaign
from test_rule_pack_narrative import reply
from unittest.mock import Mock


class PreparedActorTests(unittest.TestCase):
    def setUp(self):
        self.pack=RulePack(profile_document());self.npcs=[npc(),npc('sombra',known=False,public='')]

    def create(self,identifier='a'*24,npc_id='arda',public_fields=None):
        return actors.create(self.pack,identifier,npc_id,'support',[{'inputs':{},'physical':{}}],
            ['energy'] if public_fields is None else public_fields,self.npcs,'provided-profile')

    def test_explicit_profile_private_stats_and_known_projection(self):
        visible=self.create();hidden=self.create('b'*24,'sombra')
        registry=actors.validate_registry([visible,hidden],self.pack,self.npcs)
        public=actors.public_view(registry,self.pack,self.npcs)
        self.assertEqual(len(public),1);self.assertEqual(public[0]['fields'],{'energy':{'label':'Energía','value':2}})
        self.assertNotIn('sheet',public[0]);self.assertNotIn('profile',public[0]);self.assertNotIn('owner',str(public))
        self.assertEqual(visible['sheet']['owner'],'director:'+'a'*24)
        self.assertEqual(visible['sheet']['profile'],'support');self.assertTrue(self.pack.ready(visible['sheet']))

    def test_replay_no_randomness_and_reject_changed_stats_or_evidence(self):
        actor=self.create()
        with patch('rule_pack_runtime.secrets.randbelow',side_effect=AssertionError('Actor replay rolled')):
            self.assertEqual(actors.validate(actor,self.pack,self.npcs),actor)
        for transform in [lambda a:a['sheet']['fields'].update(energy=3),lambda a:a.update(profile='missing'),
            lambda a:a['sheet'].pop('profile'),lambda a:a['creation']['steps'][0]['trace'].update(changes={}),
            lambda a:a['sheet'].update(owner='ana'),lambda a:a.update(policy='verified-npc')]:
            bad=copy.deepcopy(actor);transform(bad)
            with self.assertRaises(RulePackError):actors.validate(bad,self.pack,self.npcs)

    def test_duplicate_npc_player_collision_and_public_fields_rejected(self):
        first=self.create();second=self.create('b'*24)
        for registry,player_ids in [([first,second],()),([first,first],()),([first],['a'*24])]:
            with self.assertRaises(RulePackError):actors.validate_registry(registry,self.pack,self.npcs,player_ids)
        for fields in [['missing'],['energy','energy']]:
            with self.assertRaises(RulePackError):self.create(public_fields=fields)

    def test_missing_dice_or_illegal_later_choices_do_not_invent_actor(self):
        data=profile_document();data['creationProfiles']['support']['steps']=['aptitude','training'];pack=RulePack(data)
        stages=[{'inputs':{},'physical':{}},{'inputs':{'role':'cronista','focus':1},'physical':{}}]
        with patch('rule_pack_runtime.secrets.randbelow',side_effect=AssertionError('Actor silently rolled')):
            with self.assertRaises(RulePackError):actors.create(pack,'a'*24,'arda','support',stages,[],self.npcs,'provided-profile')
        stages[0]['physical']={'aptitude':[1]};stages[1]['inputs']['focus']=2
        with self.assertRaises(RulePackError):actors.create(pack,'a'*24,'arda','support',stages,[],self.npcs,'provided-profile')
        stages[1]['inputs']['focus']=1
        actor=actors.create(pack,'a'*24,'arda','support',stages,[],self.npcs,'provided-profile')
        self.assertEqual(actors.validate(actor,pack,self.npcs),actor)


class ActorCampaignTests(unittest.TestCase):
    def setUp(self):
        self.me={'id':'ana','name':'Ana','host':True,'campaign':'private-actors'}
        state=campaign.execute_action(campaign.initial_state({}),{'type':'install_rule_pack','package':profile_document(),'policy':'provided-rules'},self.me)
        state=campaign.execute_action(state,{'type':'create_pack_sheet','name':'Aria','physical':{'aptitude':[1]}},self.me);cid=state['characters'][0]['id']
        state=campaign.execute_action(state,{'type':'advance_pack_creation','character':cid,'step':'training','inputs':{'role':'cronista','focus':1}},self.me)
        self.state=campaign.execute_action(state,{'type':'start_pack_adventure','character':cid},self.me,
            narrative_call=Mock(return_value=reply(npcUpdates=[npc(),npc('sombra',name='PRIVATE-ACTOR-NAME',known=False,public='')])))
        self.action={'type':'create_pack_actor','actor':'a'*24,'npc':'arda','profile':'support','stages':[{'inputs':{},'physical':{}}],
            'publicFields':['energy'],'policy':'provided-profile'}

    def test_actor_state_copy_and_visibility_do_not_reassign_director_to_player(self):
        state=campaign.execute_action(self.state,self.action,self.me)
        hidden=self.action|{'actor':'b'*24,'npc':'sombra'};state=campaign.execute_action(state,hidden,self.me)
        campaign.validate_restored(state)
        for me in [self.me,self.me|{'id':'eva','host':False}]:
            public=campaign.public_view(state,me);self.assertNotIn('actors',public)
            self.assertEqual(len(public['actorViews']),1);self.assertNotIn('PRIVATE-ACTOR-NAME',str(public))
            self.assertEqual(public['actorViews'][0]['fields'],{'energy':{'label':'Energía','value':2}})
        with patch('rule_pack_runtime.secrets.randbelow',side_effect=AssertionError('Actor copy rolled')):
            copied=campaign.import_campaign(state,self.me|{'id':'eva'})
        self.assertEqual(copied['actors'],state['actors']);self.assertEqual(copied['characters'][0]['owner'],'eva')
        provider=Mock(side_effect=AssertionError('Player spoke for NPC'))
        with self.assertRaises(RulePackError):campaign.execute_action(state,{'type':'talk_pack_adventure','character':'a'*24,'mode':'action','text':'Actúo por el PNJ.'},self.me,narrative_call=provider)
        provider.assert_not_called()
        bad=copy.deepcopy(state);bad['actors'][0]['sheet']['fields']['energy']=3
        with self.assertRaises(RulePackError):campaign.validate_restored(bad)

    def test_permissions_duplicates_and_player_identity_checked_before_creation(self):
        empty=campaign.initial_state({});empty['actors']=[]
        with self.assertRaises(RulePackError):campaign.validate_restored(empty)
        with self.assertRaises(PermissionError):campaign.execute_action(self.state,self.action,self.me|{'host':False})
        with self.assertRaises(RulePackError):campaign.execute_action(self.state,self.action|{'actor':self.state['characters'][0]['id']},self.me)
        state=campaign.execute_action(self.state,self.action,self.me)
        with patch('rule_pack_runtime.secrets.randbelow',side_effect=AssertionError('Duplicate actor rolled')):
            with self.assertRaises(RulePackError):campaign.execute_action(state,self.action,self.me)
