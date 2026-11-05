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


def place(identifier='archivo',**changes):
    return npc(identifier,**{'name':'Archivo','public':'Un edificio junto a la plaza.','private':'PRIVATE-PLACE: una cámara sellada.',**changes})


def relationship(identifier='arda-archivo',**changes):
    return {'id':identifier,'from':'npc:arda','to':'place:archivo','known':True,'public':'Arda custodia este archivo.','private':'PRIVATE-LINK: otra entrada.',**changes}


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

    def test_places_and_relationships_are_bounded_referential_and_private(self):
        people=[npc()];places=[place(),place('oculto',name='PRIVATE-NAME',known=False,public='')]
        links=[relationship(),relationship('secreto',to='place:oculto',known=False,public='')]
        public=world.public_relationships(links,people,places)
        self.assertEqual(len(public),1);self.assertEqual(public[0]['toName'],'Archivo')
        self.assertNotIn('PRIVATE',str(public))
        for bad in [relationship(to='place:missing'),relationship(to='npc:arda'),relationship(to='place:oculto'),relationship(to='character:player'),relationship(known=False)]:
            with self.assertRaises(RulePackError):world.validate_relationships([bad],people,places)
        with self.assertRaises(RulePackError):world.merge_relationships(links,[relationship(to='place:oculto',known=False,public='')],people,places)
        with self.assertRaises(RulePackError):world.merge_places([place('place-'+str(i)) for i in range(8)],[place('extra')])


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

    def test_player_identity_cannot_be_overwritten_by_an_npc(self):
        state=copy.deepcopy(self.state);state['characters'][0]['id']='arda'
        with self.assertRaises(RulePackError):
            campaign.execute_action(state,{'type':'start_pack_adventure','character':'arda'},self.me,
                narrative_call=Mock(return_value=reply(npcUpdates=[npc()])))
        self.assertIsNone(state['narrative'])

    def test_truncated_npc_update_preserves_the_previous_registry(self):
        import json
        def call(state,kind,answer=None,**data):
            return campaign.execute_action(state,{'type':kind,**data},self.me,narrative_call=Mock(return_value=answer or reply()))
        state=call(self.state,'start_pack_adventure',reply(npcUpdates=[npc()]),character=self.character)
        state=call(state,'talk_pack_adventure',reply('intentar'),character=self.character,text='Intento investigar.',mode='action')
        state=call(state,'resolve_pack_request',request=state['narrative']['pending']['id'],physical={'dice':[3,4]})
        prepared=director.prepare(state,'continue',state['characters'][0],'','action',campaign.runtime(state,self.me['campaign']))
        partial=json.dumps(reply())[:-1]+',"npcUpdates":[{"id":"incompleto'
        raw=json.dumps({'stop_reason':'max_tokens','content':[{'type':'text','text':partial}]}).encode()
        recovered=director.parse_response(prepared,raw)
        after=call(state,'continue_pack_adventure',recovered)
        self.assertEqual(after['narrative']['npcs'],state['narrative']['npcs'])
        self.assertEqual(after['characters'],state['characters'])
        self.assertIsNone(after['narrative']['continuation'])

    def test_places_relationships_context_copy_and_no_automatic_travel(self):
        started=campaign.execute_action(self.state,{'type':'start_pack_adventure','character':self.character},self.me,
            narrative_call=Mock(return_value=reply(npcUpdates=[npc()],placeUpdates=[place(),place('oculto',name='PRIVATE-PLACE-NAME',known=False,public='')],
                relationshipUpdates=[relationship(),relationship('secreto',to='place:oculto',known=False,public='')])))
        self.assertEqual(started['characters'],self.state['characters']);self.assertEqual(started['goal'],self.state['goal'])
        view=campaign.public_view(started,self.me);self.assertEqual(len(view['narrativeView']['places']),1)
        self.assertEqual(len(view['narrativeView']['relationships']),1);self.assertNotIn('PRIVATE',str(view))
        prepared=director.prepare(started,'talk',started['characters'][0],'Hola','dialogue',campaign.runtime(started,self.me['campaign']))
        self.assertEqual(len(prepared['request']['directorKnowledge']['places']),2)
        self.assertEqual(len(prepared['request']['directorKnowledge']['relationships']),2)
        continued=campaign.execute_action(started,{'type':'talk_pack_adventure','character':self.character,'text':'Hola','mode':'dialogue'},self.me,narrative_call=Mock(return_value=reply()))
        for key in ('places','relationships'):self.assertEqual(continued['narrative'][key],started['narrative'][key])
        copied=campaign.import_campaign(continued,self.me|{'id':'new-owner'});campaign.validate_restored(copied)
        bad=copy.deepcopy(copied);bad['narrative']['relationships'][0]['to']='place:missing'
        with self.assertRaises(RulePackError):campaign.validate_restored(bad)
        with self.assertRaises(RulePackError):
            campaign.execute_action(self.state,{'type':'start_pack_adventure','character':self.character},self.me,
                narrative_call=Mock(return_value=reply(placeUpdates=[place(location='move-player')])) )
