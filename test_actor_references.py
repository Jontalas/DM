import copy
import unittest
from unittest.mock import patch
import actor_references
import rule_pack_campaign as campaign
from rule_pack_runtime import RulePackError
import test_rule_pack_actors as fixture


class ActorReferenceTests(unittest.TestCase):
    def setUp(self):
        f=fixture.ActorCampaignTests();f.setUp();self.me=f.me
        self.state=campaign.execute_action(f.state,f.action,f.me)
        self.state=campaign.execute_action(self.state,f.action|{'actor':'b'*24,'npc':'sombra'},f.me)
        self.pack=campaign.runtime(self.state,f.me['campaign']);self.character=self.state['characters'][0]['id']

    def test_reference_does_not_expose_stats_or_imply_legality(self):
        before=copy.deepcopy(self.state)
        with patch('rule_pack_runtime.secrets.randbelow',side_effect=AssertionError('Selection rolled')):
            binding=actor_references.select(self.state,self.character,'a'*24,self.me,self.pack)
            private=actor_references.validate(binding,self.state,self.me,self.pack)
        self.assertNotIn('sheet',binding);self.assertNotIn('profile',binding);self.assertNotIn('fields',binding)
        self.assertEqual(private,self.state['actors'][0]['sheet']);self.assertEqual(self.state,before)
        private['fields']['energy']=99;self.assertEqual(self.state,before)

    def test_unknown_actor_player_target_owner_and_stale_revisions_rejected(self):
        for target in ['b'*24,'c'*24,self.character]:
            with self.assertRaises(RulePackError):actor_references.select(self.state,self.character,target,self.me,self.pack)
        with self.assertRaises(PermissionError):actor_references.select(self.state,self.character,'a'*24,self.me|{'id':'eva'},self.pack)
        binding=actor_references.select(self.state,self.character,'a'*24,self.me,self.pack)
        for transform in [lambda s:s['actors'][0]['sheet'].update(revision=2),lambda s:s['characters'][0]['sheet'].update(revision=3)]:
            stale=copy.deepcopy(self.state);transform(stale)
            with self.assertRaises(RulePackError):actor_references.validate(binding,stale,self.me,self.pack)
        for change in [{'packageSha256':'0'*64},{'targetRevision':True},{'fields':{}},{'target':'b'*24},{'npc':'sombra'}]:
            with self.assertRaises(RulePackError):actor_references.validate(binding|change,self.state,self.me,self.pack)
