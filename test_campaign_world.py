import copy
import unittest
import campaign_world as memory
from test_rule_pack_world import npc,place,relationship


class CampaignWorldTests(unittest.TestCase):
    def updates(self,**fields):return {'npcs':[],'places':[],'relationships':[],**fields}

    def test_people_places_and_links_use_existing_privacy_and_identity_contract(self):
        original=memory.empty();before=copy.deepcopy(original)
        result=memory.apply(original,self.updates(npcs=[npc()],places=[place()],relationships=[relationship()]))
        self.assertEqual(original,before);self.assertEqual(result['revision'],1)
        public=memory.public_view(result);self.assertEqual(public['relationships'][0]['toName'],'Archivo')
        self.assertNotIn('private',str(public));self.assertEqual(len(public['npcs']),1)
        result=memory.apply(result,self.updates(npcs=[npc('oculta',name='SECRET-NAME',known=False,public='',private='SECRET-NOTE')]))
        self.assertNotIn('SECRET',str(memory.public_view(result)))

    def test_empty_and_identical_updates_do_not_invent_revision_or_mutate_input(self):
        original=memory.apply(memory.empty(),self.updates(npcs=[npc()]))
        for updates in (self.updates(),self.updates(npcs=[npc()])):
            result=memory.apply(original,updates);self.assertEqual(result,original);self.assertIsNot(result,original)

    def test_invalid_late_link_never_partially_changes_memory_or_records_mechanics(self):
        original=memory.empty();before=copy.deepcopy(original)
        for updates in (self.updates(npcs=[npc()],relationships=[relationship(to='place:missing')]),
                        self.updates(npcs=[npc(hp=10)]),self.updates(npcs=[npc()],hp=10),
                        self.updates(npcs=[npc('a'),npc('b')],places=[place('a'),place('b')])):
            with self.assertRaises(ValueError):memory.apply(original,updates)
            self.assertEqual(original,before)

    def test_known_people_cannot_be_hidden_or_links_reassigned_on_return(self):
        original=memory.apply(memory.empty(),self.updates(npcs=[npc()],places=[place()],relationships=[relationship()]))
        for updates in (self.updates(npcs=[npc(known=False,public='')]),
                        self.updates(places=[place('otro')],relationships=[relationship(to='place:otro')])):
            with self.assertRaises(ValueError):memory.apply(original,updates)

    def test_import_revision_and_shape_are_strict_and_bounded(self):
        for altered in ({**memory.empty(),'revision':True},{**memory.empty(),'revision':-1},
                        {**memory.empty(),'revision':1000001},{**memory.empty(),'format':'unknown'},
                        {**memory.empty(),'private':'unvalidated'}):
            with self.assertRaises(ValueError):memory.validate(altered)
