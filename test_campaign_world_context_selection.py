import copy
import unittest
import campaign_world as world
import campaign_world_context as context
from test_rule_pack_world import npc,place,relationship


def full_world():
    record=world.empty();record['revision']=12
    record['npcs']=[npc('person-'+str(i),name='Persona '+str(i),public='Nota pública '+str(i)+'x'*350,private='PRIVATE '+str(i)+'y'*600) for i in range(16)]
    record['places']=[place('place-'+str(i),name='Lugar '+str(i),public='Lugar '+str(i)+'x'*350,private='PRIVATE-PLACE '+str(i)+'y'*600) for i in range(8)]
    record['relationships']=[relationship('link-'+str(i),**{'from':'npc:person-'+str(i),'to':'place:place-'+str(i%8)},public='Vínculo '+str(i)+'x'*250,private='PRIVATE-LINK '+str(i)+'y'*450) for i in range(16)]
    return world.validate(record)


class WorldContextSelectionTests(unittest.TestCase):
    def test_small_records_keep_full_contract_without_payload_inflation(self):
        record=world.apply(world.empty(),{'npcs':[npc()],'places':[place()],'relationships':[]})
        view,selection=context.select(record,'Saludo a Arda','Archivo');self.assertEqual(view,record);self.assertIsNone(selection)

    def test_named_people_current_place_and_neighbors_keep_complete_notes_with_all_identities(self):
        record=full_world();before=copy.deepcopy(record);view,selection=context.select(record,'Pregunto a Persona 3','Lugar 4')
        self.assertEqual(record,before);self.assertEqual(view['format'],context.FORMAT)
        self.assertIn('person-3',selection['npcs']);self.assertIn('place-4',selection['places']);self.assertIn('place-3',selection['places'])
        self.assertEqual(len(view['identities']['npcs']),16);self.assertEqual(len(view['identities']['places']),8)
        self.assertNotIn('PRIVATE',str(view['identities']))
        self.assertEqual(next(item for item in view['npcs'] if item['id']=='person-3'),record['npcs'][3])
        self.assertLess(context.size({'notes':view,'selection':selection}),context.size(record)//2)
        self.assertEqual(context.select(record,'Pregunto a Persona 3','Lugar 4'),(view,selection))

    def test_unloaded_existing_notes_cannot_be_replaced_but_new_identity_is_allowed(self):
        record=full_world();_,selection=context.select(record,'Persona 3','Lugar 4')
        omitted=next(item for item in record['npcs'] if item['id'] not in selection['npcs'])
        with self.assertRaises(ValueError):context.validate_updates(record,{'npcs':[omitted],'places':[],'relationships':[]},selection)
        context.validate_updates(record,{'npcs':[npc('new-person')],'places':[],'relationships':[]},selection)
        context.validate_updates(record,{'npcs':[omitted],'places':[],'relationships':[]},None)

    def test_utf8_limit_never_truncates_a_note_or_mutates_full_record(self):
        record=full_world()
        for kind in context.KINDS:
            for item in record[kind]:item['public']='🦉'*(350 if kind=='relationships' else 500);item['private']='🦉'*(500 if kind=='relationships' else 700)
        view,selection=context.select(record,'Persona 0','Lugar 0')
        self.assertLessEqual(context.size({'notes':view,'selection':selection}),context.MAX_BYTES)
        self.assertIn('person-0',selection['npcs'])
        for kind in context.KINDS:
            for item in view[kind]:self.assertEqual(item,next(original for original in record[kind] if original['id']==item['id']))

    def test_bad_selection_or_duplicate_ids_are_rejected(self):
        record=full_world();_,selection=context.select(record,'Persona 3','Lugar 4')
        for bad in ({**selection,'format':'unknown'},{**selection,'npcs':['missing']},{**selection,'npcs':['person-3','person-3']},
                    {**selection,'places':True},{**selection,'npcs':['person-'+str(i) for i in range(7)]}):
            with self.assertRaises(ValueError):context.validate_selection(record,bad)

    def test_maximum_utf8_names_and_ids_leave_room_for_a_named_complete_note(self):
        record=full_world();identifiers={}
        for kind,prefix in (('npcs','npc:'),('places','place:')):
            for index,item in enumerate(record[kind]):
                old=item['id'];identifier=(kind+str(index)+'a'*48)[:48]
                identifiers[prefix+old]=prefix+identifier;item.update(id=identifier,name='🦉'*80,public='🦉'*500,private='🦉'*700)
        for index,link in enumerate(record['relationships']):
            link.update(id=('link'+str(index)+'a'*48)[:48],public='🦉'*350,private='🦉'*500)
            for key in ('from','to'):link[key]=identifiers[link[key]]
        identifier=record['npcs'][0]['id'];view,selection=context.select(record,identifier,'')
        self.assertIn(identifier,selection['npcs']);self.assertLessEqual(context.size({'notes':view,'selection':selection}),context.MAX_BYTES)
