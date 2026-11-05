import copy
import unittest
from unittest.mock import Mock
import rule_pack_world as world
import rule_pack_campaign as campaign
import rule_pack_director as director
from rule_pack_runtime import RulePackError
import test_rule_pack_narrative as narrative_fixture

reply=narrative_fixture.reply


def npc(identifier='arda',**changes):
    return {'id':identifier,'name':'Arda','known':True,'public':'Archivera junto al farol.','private':'PRIVATE-NPC: oculta una carta.',**changes}


class WorldTests(unittest.TestCase):
    def test_merge_preserves_other_npcs_and_never_exposes_secrets(self):
        original=[npc(),npc('sombra',known=False,public='',name='Nombre secreto')];before=copy.deepcopy(original)
        changed=world.merge(original,[npc(public='Arda ha mostrado la marca.')])
        self.assertEqual(original,before);self.assertEqual(changed[1],original[1])
        self.assertEqual(world.public_view(changed),[{'id':'arda','name':'Arda','public':'Arda ha mostrado la marca.'}])
        with self.assertRaises(RulePackError):world.merge(changed,[npc(known=False,public='')])

    def test_bounds_unknown_fields_and_duplicate_ids(self):
        for updates in [[npc(),npc()],[npc(stats={'energy':5})],[npc(known=1)],[npc('BAD')],[npc(known=False)],
                        [npc(private='x'*701)],[npc(str(i)) for i in range(4)]]:
            with self.assertRaises(RulePackError):world.merge([],updates)
        full=[npc('npc-'+str(i)) for i in range(16)]
        with self.assertRaises(RulePackError):world.merge(full,[npc('extra')])
        self.assertEqual(len(world.merge(full,[npc('npc-1')])),16)


class WorldNarrativeTests(unittest.TestCase):
    def setUp(self):
        fixture=narrative_fixture.RulePackNarrativeTests();fixture.setUp()
        self.state=fixture.state;self.me=fixture.me;self.character=fixture.character

    def test_npcs_persist_in_context_copy_and_public_projection_without_sheet_effects(self):
        initial=copy.deepcopy(self.state['characters'])
        started=campaign.execute_action(self.state,{'type':'start_pack_adventure','character':self.character},self.me,
            narrative_call=Mock(return_value=reply(npcUpdates=[npc(),npc('sombra',name='PRIVATE-NAME',known=False,public='')])))
        self.assertEqual(started['characters'],initial)
        view=campaign.public_view(started,self.me)
        self.assertEqual(view['narrativeView']['npcs'],world.public_view(started['narrative']['npcs']))
        self.assertNotIn('PRIVATE-NPC',str(view));self.assertNotIn('PRIVATE-NAME',str(view))
        prepared=director.prepare(started,'talk',started['characters'][0],'Hola','dialogue',campaign.runtime(started,self.me['campaign']))
        self.assertEqual(prepared['request']['directorKnowledge']['npcs'],started['narrative']['npcs'])
        continued=campaign.execute_action(started,{'type':'talk_pack_adventure','character':self.character,'text':'Hola','mode':'dialogue'},self.me,
            narrative_call=Mock(return_value=reply()))
        self.assertEqual(continued['narrative']['npcs'],started['narrative']['npcs'])
        restored=campaign.import_campaign(continued,self.me|{'id':'new-owner'})
        self.assertEqual(restored['narrative']['npcs'],started['narrative']['npcs']);campaign.validate_restored(restored)
        bad=copy.deepcopy(restored);bad['narrative']['npcs'][0]['stats']={'energy':10}
        with self.assertRaises(RulePackError):campaign.validate_restored(bad)

    def test_legacy_context_hash_remains_unchanged_without_npcs(self):
        prepared=director.prepare(self.state,'start',self.state['characters'][0],'','action',campaign.runtime(self.state,self.me['campaign']))
        self.assertEqual(prepared['request']['directorKnowledge'],{'preparation':''})

    def test_hidden_npcs_are_not_even_advertised_in_public_view(self):
        started=campaign.execute_action(self.state,{'type':'start_pack_adventure','character':self.character},self.me,
            narrative_call=Mock(return_value=reply(npcUpdates=[npc('sombra',known=False,public='')])))
        self.assertNotIn('npcs',campaign.public_view(started,self.me)['narrativeView'])
