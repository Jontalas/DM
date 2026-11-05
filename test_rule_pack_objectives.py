import copy
import unittest
from unittest.mock import Mock,patch
import rule_pack_campaign as campaign
import rule_pack_director as director
import rule_pack_objectives as objectives
from rule_pack_runtime import RulePackError
import test_rule_pack_narrative as fixture


def goal(identifier='farol',**changes):
    return {'id':identifier,'title':'Descifrar la marca del farol','detail':'Investigar la marca que ha señalado Arda.','known':True,'private':'PRIVATE-GOAL: la marca apunta al archivo.',**changes}


class ObjectiveTests(unittest.TestCase):
    def setUp(self):
        test=fixture.RulePackNarrativeTests();test.setUp()
        self.state=test.state;self.me=test.me;self.character=test.character
        self.state=self.apply(self.state,'start_pack_adventure',fixture.reply(objectiveUpdates=[goal(),goal('oculto',known=False,title='PRIVATE-TITLE')]),character=self.character)

    def apply(self,state,kind,answer=None,**data):
        return campaign.execute_action(state,{'type':kind,**data},self.me,narrative_call=Mock(return_value=answer or fixture.reply()))

    def pending(self,state=None):
        return self.apply(state or self.state,'talk_pack_adventure',fixture.reply('intentar',objectiveCheck={'objective':'farol','field':'success'}),
            character=self.character,text='Investigo la marca que señala Arda.',mode='action')

    def resolve(self,state,dice):
        return self.apply(state,'resolve_pack_request',request=state['narrative']['pending']['id'],physical={'dice':dice})

    def test_success_completes_only_linked_goal_before_narration_and_copy_replays_evidence(self):
        pending=self.pending();self.assertEqual(pending['narrative']['objectives'][0]['status'],'open')
        resolved=self.resolve(pending,[3,4]);goal_state=resolved['narrative']['objectives'][0]
        self.assertEqual(goal_state['status'],'completed');self.assertEqual(goal_state['evidence']['message'],len(resolved['messages'])-1)
        self.assertEqual(resolved['narrative']['objectives'][1]['status'],'open')
        self.assertIsNotNone(resolved['narrative']['continuation'])
        with patch('rule_pack_runtime.secrets.randbelow',side_effect=AssertionError('Import rolled')):
            copied=campaign.import_campaign(resolved,self.me|{'id':'new-owner'})
        self.assertEqual(copied['narrative']['objectives'],resolved['narrative']['objectives'])
        continued=self.apply(resolved,'continue_pack_adventure')
        self.assertEqual(continued['narrative']['objectives'],resolved['narrative']['objectives']);campaign.validate_restored(continued)

    def test_failure_withdrawal_or_unrelated_action_cannot_complete_goal(self):
        pending=self.pending();failed=self.resolve(pending,[1,1])
        self.assertEqual(failed['narrative']['objectives'][0]['status'],'open');self.assertFalse(failed['messages'][-1]['objectiveResolution']['met'])
        campaign.validate_restored(failed)
        cancelled=self.apply(pending,'cancel_pack_request',request=pending['narrative']['pending']['id'])
        self.assertEqual(cancelled['narrative']['objectives'],pending['narrative']['objectives'])
        unrelated=self.apply(self.state,'talk_pack_adventure',fixture.reply('intentar'),character=self.character,text='Investigo otra cosa.',mode='action')
        unrelated=self.resolve(unrelated,[6,6]);self.assertEqual(unrelated['narrative']['objectives'][0]['status'],'open')

    def test_boolean_recalculated_true_can_complete_a_later_distinct_goal(self):
        state=self.resolve(self.pending(),[6,6]);state=self.apply(state,'continue_pack_adventure')
        state=self.apply(state,'talk_pack_adventure',fixture.reply('intentar',objectiveUpdates=[goal('otra')],objectiveCheck={'objective':'otra','field':'success'}),
            character=self.character,text='Intento descifrar otra marca.',mode='action')
        state=self.resolve(state,[3,4]);self.assertNotIn('success',state['messages'][-1]['trace']['changes'])
        self.assertEqual(state['narrative']['objectives'][-1]['status'],'completed');campaign.validate_restored(state)

    def test_views_hide_unknown_goals_and_private_notes_even_from_host(self):
        public=campaign.public_view(self.state,self.me)
        self.assertEqual(len(public['narrativeView']['objectives']),1)
        self.assertNotIn('PRIVATE-GOAL',str(public));self.assertNotIn('PRIVATE-TITLE',str(public))
        pack=campaign.runtime(self.state,self.me['campaign'])
        prepared=director.prepare(self.state,'talk',self.state['characters'][0],'Hola','dialogue',pack)
        self.assertEqual(len(prepared['request']['directorKnowledge']['objectives']),2)

    def test_invalid_bindings_and_direct_model_completion_are_rejected_before_rng(self):
        pack=campaign.runtime(self.state,self.me['campaign'])
        opened=director.prepare(self.state,'talk',self.state['characters'][0],'Investigo','action',pack)
        self.assertEqual(director.schema(opened)['properties']['objectiveCheck']['properties']['field']['enum'],['success'])
        dialogue=director.prepare(self.state,'talk',self.state['characters'][0],'Hola','dialogue',pack)
        self.assertNotIn('objectiveCheck',director.schema(dialogue)['properties'])
        for check in [{'objective':'oculto','field':'success'},{'objective':'missing','field':'success'},
                      {'objective':'farol','field':'total'},{'objective':'farol','field':'exhausted'},
                      {'objective':'farol','field':'success','met':True}]:
            with self.assertRaises(RulePackError):
                self.apply(self.state,'talk_pack_adventure',fixture.reply('intentar',objectiveCheck=check),character=self.character,text='Investigo.',mode='action')
        with self.assertRaises(RulePackError):self.apply(self.state,'talk_pack_adventure',fixture.reply(objectiveCheck={'objective':'farol','field':'success'}),character=self.character,text='Hola',mode='dialogue')
        with self.assertRaises(RulePackError):self.apply(self.state,'talk_pack_adventure',fixture.reply(objectiveUpdates=[goal(status='completed')]),character=self.character,text='Hola',mode='dialogue')
        with self.assertRaises(RulePackError):self.apply(self.state,'talk_pack_adventure',fixture.reply(objectiveUpdates=[goal(title='Otro objetivo')]),character=self.character,text='Hola',mode='dialogue')

    def test_copy_rejects_forged_evidence_wrong_result_or_prior_message(self):
        resolved=self.resolve(self.pending(),[3,4])
        for key,value in [('message',0),('packageSha256','0'*64),('field','energy'),('met',False),('sheetRevision',50)]:
            bad=copy.deepcopy(resolved);bad['narrative']['objectives'][0]['evidence'][key]=value
            with self.assertRaises(RulePackError):campaign.validate_restored(bad)
        bad=copy.deepcopy(resolved);bad['messages'][-1]['objectiveResolution']['met']=False
        with self.assertRaises(RulePackError):campaign.validate_restored(bad)
        bad=copy.deepcopy(resolved);bad['narrative']['objectives'][0]['status']='open';bad['narrative']['objectives'][0]['evidence']=None
        with self.assertRaises(RulePackError):campaign.validate_restored(bad)

    def test_changed_decisions_cannot_reuse_the_original_completion_binding(self):
        package=campaign.runtime(self.state,self.me['campaign']).document()
        # At this boundary, the existing engine separately validates the inputs;
        # the objective guard must distinguish legal changes to those decisions.
        pending=self.pending()['narrative']['pending']
        event={'inputs':{'different-choice':True}}
        sheet=self.state['characters'][0]['sheet'];sheet=copy.deepcopy(sheet);sheet['revision']+=1;sheet['fields']['success']=True
        goals,proof=objectives.resolve(self.state['narrative']['objectives'],pending,event,sheet,5,package)
        self.assertFalse(proof['matchedInputs']);self.assertFalse(proof['met']);self.assertEqual(goals[0]['status'],'open')
