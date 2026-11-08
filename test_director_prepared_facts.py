import copy
import json
import unittest
from unittest.mock import patch
import engine
import claude_dm
import director_prepared_facts as facts
import director_prompt
import legacy_director_attempt as legacy
from test_character_builder import choices


class PreparedSceneFactsTests(unittest.TestCase):
    def setUp(self):
        self.me={'id':'player','name':'Ana','host':True};self.state=engine.initial_state({})
        self.act('create_character',choices=choices());self.actor=self.state['characters'][0]['id']
        self.act('enter_pf_encounter',encounter='patio-del-peaje',encounterVersion='1.13.0',character=self.actor)
        self.act('choose_pf_encounter',choice='parley')
        self.state['messages'].append({'speaker':'Aria','owner':'player','kind':'dialogue','text':'¿Me dejas revisar el registro?'})

    def act(self,kind,**body):engine.apply_action(self.state,{'type':kind,**body},self.me)

    def test_dialogue_receives_existing_permission_without_actions_clues_or_mutation(self):
        before=copy.deepcopy(self.state);context=claude_dm.build_context(self.state,'Pregunta',[])
        self.assertEqual(context['preparedSceneFacts']['publicDocumentsAccess'],'already-permitted')
        self.assertEqual(context['preparedSceneFacts']['npc'],self.state['characters'][1]['id'])
        self.assertNotIn('preparedDecisions',context);self.assertNotIn('preparedDecision',claude_dm.response_schema(self.state)['properties'])
        self.assertNotIn('preparedSceneFacts',claude_dm.build_context(self.state,'Regla',[],rules=True))
        self.assertEqual(self.state,before)
        self.assertIn('No niegues ni dejes pendiente ese permiso',director_prompt.system_prompt())

    def test_other_definitions_changed_policy_combat_and_unconscious_npc_get_no_fact(self):
        baseline=copy.deepcopy(self.state)
        for case in ('old','forged','offered','combat','unconscious','dead','condition'):
            self.state=copy.deepcopy(baseline);record=self.state['pfEncounter'];npc=self.state['characters'][1]
            if case=='old':record['definition']['version']='1.11.0'
            elif case=='forged':record['definition']['explorationPolicy']='Exige dinero.'
            elif case=='offered':record['phase']='offered'
            elif case=='combat':self.state['board']['active']=True
            elif case=='unconscious':npc.update(hp=-1,stable=True)
            elif case=='dead':npc['hp']=-10
            else:npc['conditions']='Inconsciente'
            before=copy.deepcopy(self.state)
            with self.subTest(case=case):self.assertIsNone(facts.public_facts(self.state));self.assertEqual(self.state,before)

    def test_derived_fact_keeps_old_capture_key_and_never_masks_changed_game_facts(self):
        prepared=legacy.prepare(self.state,'Pregunta',[]);old=copy.deepcopy(prepared['captureRequest']);old['context'].pop('preparedSceneFacts')
        self.assertEqual(legacy.request_sha(old),prepared['sha256']);self.assertTrue(legacy.compatible_input(old,prepared['captureRequest']))
        changed=copy.deepcopy(prepared['captureRequest']);changed['context']['state']['characters'][1]['hp']-=1
        self.assertFalse(legacy.compatible_input(old,changed))

    def test_captured_narration_is_preserved_without_silent_semantic_repair(self):
        prepared=legacy.prepare(self.state,'Pregunta',[])
        text='La guardiana todavía pide una justificación.'
        with patch('claude_dm.ai_reply',side_effect=AssertionError('Restore called provider')):
            result=legacy.restore(prepared,{'kind':'report','value':{'narration':text,'proposals':[]},'latencyMs':0},legacy.SCHEME)
        self.assertEqual(result['narration'],text);self.assertNotIn('preparedDecision',result)

    def test_negative_awake_guard_requires_current_clinical_proof(self):
        import test_pf_awake_party as clinical_fixture
        fixture=clinical_fixture.AwakePartyProofTests();fixture.encounter_version='1.13.0';fixture.setUp()
        self.assertEqual(facts.public_facts(fixture.state)['publicDocumentsAccess'],'already-permitted')
        fixture.state['characters'][1]['hp']+=1
        self.assertIsNone(facts.public_facts(fixture.state))
