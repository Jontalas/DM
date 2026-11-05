import copy
import unittest
from unittest.mock import patch
from rule_pack_runtime import RulePack,RulePackError
from rule_pack_composition import compose
from test_rule_pack_runtime import document
import rule_pack_campaign as campaign
import rule_pack_director as director
from test_rule_pack_narrative import reply
from unittest.mock import Mock


def profile_document():
    data=document('original-staged-results-example');data['requires'].append('creation-profiles')
    data['id']='original-creation-profiles-example';data['version']='1.2.0';data['edition']='Ejemplo propio 3'
    data['sources'][0]['locator']='Ejemplo propio CC0: preparación de apoyo sin dados, aptitud 2, oficio cronista y energía 2; recorrido normal de dos etapas conservado. No representa reglas de Pathfinder.'
    data['creationProfiles']={'support':{'label':'Preparación de apoyo propia','sources':['staged-source'],'steps':['prepare-support']}}
    data['actions']['prepare-support']={'label':'Preparar apoyo','sources':['staged-source'],'inputs':{},'requires':[],'rolls':[],
        'effects':[{'field':'talent','value':2},{'field':'role','value':'cronista'},{'field':'energy','value':2}]}
    return data


class CreationProfileTests(unittest.TestCase):
    def test_independent_profile_progress_without_changing_default_creator(self):
        pack=RulePack(profile_document())
        default,_=pack.create_character('ana',physical={'aptitude':[1]})
        self.assertFalse(pack.ready(default));self.assertNotIn('profile',default)
        support,trace=pack.create_character('director',profile='support')
        self.assertTrue(pack.ready(support));self.assertEqual(support['profile'],'support')
        self.assertEqual(pack.view(support)['fields']['energy'],2);self.assertEqual(trace['action'],'prepare-support')
        self.assertEqual(pack.creation_progress(default)['next'],'training')
        for sheet,action in [(default,'prepare-support'),(support,'prepare-support'),(support,'training')]:
            with patch('rule_pack_runtime.secrets.randbelow',side_effect=AssertionError('Invalid profile rolled')):
                with self.assertRaises(RulePackError):pack.execute(sheet,action,{},sheet['owner'])
        support,_=pack.execute(support,'explore',{},'director',physical={'pool':[3,4]})
        self.assertEqual(support['fields']['energy'],1);self.assertEqual(support['profile'],'support')

    def test_multistage_profile_uses_its_own_bounds_and_order(self):
        data=profile_document();data['creationProfiles']['support']['steps']=['aptitude','training']
        pack=RulePack(data);sheet,_=pack.create_character('director',profile='support',physical={'aptitude':[1]})
        self.assertFalse(pack.ready(sheet));self.assertEqual(pack.creation_inputs(sheet)['focus']['max'],1)
        with self.assertRaises(RulePackError):pack.advance_character(sheet,'training',{'role':'cronista','focus':2},'director')
        sheet,_=pack.advance_character(sheet,'training',{'role':'cronista','focus':1},'director')
        self.assertTrue(pack.ready(sheet));self.assertEqual(sheet['profile'],'support')

    def test_profiles_require_declared_capability_sources_and_legal_steps(self):
        changes=[lambda d:d['requires'].remove('creation-profiles'),lambda d:d['creationProfiles']['support'].update(sources=['missing']),
            lambda d:d['creationProfiles']['support'].update(steps=['missing']),lambda d:d['creationProfiles']['support'].update(steps=['training','training']),
            lambda d:d['actions']['prepare-support'].update(permission='host'),lambda d:d.update(creationProfiles={})]
        for change in changes:
            data=profile_document();change(data)
            with self.assertRaises(RulePackError):RulePack(data)
        pack=RulePack(profile_document())
        with self.assertRaises(RulePackError):pack.new_sheet('ana',profile='missing')
        bad=pack.new_sheet('ana');bad['profile']='missing'
        with self.assertRaises(RulePackError):pack.view(bad)

    def test_composition_merges_profiles_but_rejects_conflicts(self):
        first=profile_document();second=copy.deepcopy(first);second['creationProfiles']={'other':second['creationProfiles'].pop('support')}
        combined=compose([first,second],'2.0.0')['document'];self.assertEqual(set(combined['creationProfiles']),{'support','other'})
        bad=copy.deepcopy(first);bad['creationProfiles']['support']['steps']=['aptitude','training']
        with self.assertRaises(RulePackError):compose([first,bad],'2.0.0')

    def test_default_campaign_cannot_invoke_or_import_profile_creation_as_play(self):
        me={'id':'ana','name':'Ana','host':True,'campaign':'profiles-test'}
        state=campaign.execute_action(campaign.initial_state({}),{'type':'install_rule_pack','package':profile_document(),'policy':'provided-rules'},me)
        state=campaign.execute_action(state,{'type':'create_pack_sheet','name':'Aria','physical':{'aptitude':[1]}},me);cid=state['characters'][0]['id']
        state=campaign.execute_action(state,{'type':'advance_pack_creation','character':cid,'step':'training','inputs':{'role':'cronista','focus':1}},me)
        with self.assertRaises(RulePackError):campaign.execute_action(state,{'type':'create_pack_sheet','name':'Atajo','profile':'support'},me)
        with self.assertRaises(RulePackError):campaign.execute_action(state,{'type':'run_pack_action','character':cid,'action':'prepare-support'},me)
        bad=copy.deepcopy(state);bad['characters'][0]['sheet']['profile']='support'
        with self.assertRaises(RulePackError):campaign.validate_restored(bad)
        started=campaign.execute_action(state,{'type':'start_pack_adventure','character':cid},me,narrative_call=Mock(return_value=reply()))
        request=director.prepare(started,'talk',started['characters'][0],'Exploro.','action',campaign.runtime(started,me['campaign']))['request']
        self.assertNotIn('prepare-support',request['allowedActions']);self.assertNotIn('prepare-support',request['rules']['actions'])
