import copy
import hashlib
import json
import unittest
from unittest.mock import Mock
import rule_pack_director as director
import rule_pack_campaign as campaign
from rule_pack_runtime import RulePackError
import test_rule_pack_narrative as fixture
from test_rule_pack_world import npc,place,relationship
from test_rule_pack_objectives import goal


class WorldIdentifierNormalizationTests(unittest.TestCase):
    def setUp(self):
        test=fixture.RulePackNarrativeTests();test.setUp()
        self.state=test.state;self.me=test.me;self.character=test.character
        self.pack=campaign.runtime(self.state,self.me['campaign'])
        self.prepared=director.prepare(self.state,'start',self.state['characters'][0],'','action',self.pack)
        self.reply=fixture.reply(npcUpdates=[npc('npc:arda')],placeUpdates=[place('place:archivo')],
            relationshipUpdates=[relationship('rel:arda-archivo')],objectiveUpdates=[goal('obj:marca')])

    def raw(self,reply=None,stop='end_turn'):
        return json.dumps({'stop_reason':stop,'content':[{'type':'text','text':json.dumps(reply or self.reply)}],
                           'usage':{'input_tokens':4025,'output_tokens':662}}).encode()

    def test_observed_typed_ids_recover_exactly_without_changing_fiction_or_rules(self):
        before=copy.deepcopy(self.reply);raw=self.raw();parsed=director.parse_response(self.prepared,raw)
        self.assertEqual(self.reply,before);self.assertEqual(parsed['narration'],before['narration'])
        self.assertEqual(parsed['normalization'],{'kind':'typed-world-identifiers-v1','sourceReplySha256':hashlib.sha256(raw).hexdigest(),'changedIdentifiers':4})
        self.assertEqual(parsed['npcUpdates'][0],before['npcUpdates'][0]|{'id':'arda'})
        self.assertEqual(parsed['relationshipUpdates'][0]['from'],'npc:arda');self.assertEqual(parsed['objectiveUpdates'][0]['id'],'marca')
        state=campaign.execute_action(self.state,{'type':'start_pack_adventure','character':self.character},self.me,narrative_call=Mock(return_value=parsed))
        self.assertEqual(state['characters'],self.state['characters']);self.assertEqual(state['narrative']['objectives'][0]['status'],'open')
        campaign.validate_restored(state);self.assertIn('normalization',state['messages'][-1])

    def test_collisions_wrong_kinds_unknown_references_and_claimed_provenance_are_rejected(self):
        for mutate in ('collision','kind','suffix','reference','provenance','unknown'):
            bad=copy.deepcopy(self.reply)
            if mutate=='collision':bad['npcUpdates'].append(npc('arda'))
            elif mutate=='kind':bad['npcUpdates'][0]['id']='place:arda'
            elif mutate=='suffix':bad['npcUpdates'][0]['id']='npc:bad_id'
            elif mutate=='reference':bad['relationshipUpdates'][0]['to']='place:missing'
            elif mutate=='provenance':bad['normalization']={'kind':'typed-world-identifiers-v1'}
            else:bad['unknown']='data'
            with self.assertRaises(RulePackError):director.parse_response(self.prepared,self.raw(bad))
        for operation in ('talk','continue'):
            altered=copy.deepcopy(self.prepared);altered['request']['operation']=operation
            with self.assertRaises(RulePackError):director.parse_response(altered,self.raw())
        with self.assertRaises(RulePackError):director.parse_response(self.prepared,self.raw(stop='max_tokens'))

    def test_future_schema_ids_are_simple_enums_and_endpoints_keep_only_their_namespace(self):
        props=director.schema(self.prepared)['properties']
        for key in ('npcUpdates','placeUpdates','relationshipUpdates','objectiveUpdates'):
            self.assertTrue(all(':' not in identifier for identifier in props[key]['items']['properties']['id']['enum']))
        self.assertIn('npc:npc-1',props['relationshipUpdates']['items']['properties']['from']['enum'])
