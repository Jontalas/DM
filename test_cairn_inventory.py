import copy
import unittest
from systems import cairn_1e as cairn,cairn_inventory as inventory
from test_cairn_1e import rolls


def loadout(*names,state='carried'):
    return [{'id':str(i),'item':name,'state':state} for i,name in enumerate(names)]


class CairnInventoryTests(unittest.TestCase):
    def test_original_starting_ranges_and_spellbook_columns_are_preserved(self):
        for raw,expected in [(1,'None'),(3,'None'),(4,'Brigandine'),(14,'Brigandine'),(15,'Chainmail'),(19,'Chainmail'),(20,'Plate')]:
            self.assertEqual(cairn.table_result('armor',raw),expected)
        for raw,expected in [(13,'None'),(14,'Helmet'),(16,'Helmet'),(17,'Shield'),(19,'Shield'),(20,'Helmet & Shield')]:
            self.assertEqual(cairn.table_result('helmets--shields',raw),expected)
        self.assertEqual(cairn.table_result('bonus-item-roll-on-table-indicated',5),'Tool or Trinket')
        self.assertEqual(cairn.table_result('bonus-item-roll-on-table-indicated',6),'Expeditionary Gear')
        self.assertEqual(cairn.table_result('bonus-item-roll-on-table-indicated',14),'Armor or Weapon')
        self.assertEqual(cairn.table_result('bonus-item-roll-on-table-indicated',18),'Spellbook')
        for raw,expected in [(1,'Adhere'),(25,'Displace'),(26,'Earthquake'),(50,'Marble Craze'),(100,'X-Ray Vision')]:
            self.assertEqual(cairn.table_result('spellbooks-d100',raw),expected)

    def test_full_inventory_removes_protection_without_scars_and_unloading_does_not_heal(self):
        core=cairn.core_from_rolls(rolls());before=copy.deepcopy(core)
        full=inventory.apply_inventory(core,loadout(*(['Torch']*10)))
        self.assertEqual(full['inventorySlots'],10);self.assertEqual(full['hitProtection'],0)
        self.assertEqual(core,before);self.assertNotIn('scars',full)
        lighter=inventory.apply_inventory(full,loadout('Torch'))
        self.assertEqual(lighter['hitProtection'],0)
        with self.assertRaises(ValueError):inventory.apply_inventory(core,loadout(*(['Torch']*11)))
        self.assertEqual(core,before)

    def test_armor_only_from_equipped_protections_and_caps_at_three(self):
        core=cairn.core_from_rolls(rolls())
        self.assertEqual(inventory.apply_inventory(core,loadout('Plate'))['armor'],0)
        equipped=inventory.apply_inventory(core,loadout('Plate','Helmet','Shield',state='equipped'))
        self.assertEqual(equipped['armor'],3);self.assertEqual(equipped['inventorySlots'],4)
        self.assertEqual(inventory.item('Brigandine')['slots'],2)
        self.assertEqual(inventory.item('Sling')['damageDie'],4)
        self.assertEqual(inventory.item('Crossbow')['damageDie'],8)
        with self.assertRaises(ValueError):inventory.apply_inventory(core,loadout('Bow','Shield',state='equipped'))

    def test_invalid_or_unverified_items_and_client_statistics_do_not_change_state(self):
        core=cairn.core_from_rolls(rolls());before=copy.deepcopy(core)
        for entries in [loadout('Unknown'),loadout('Cart (+4 slots, bulky)'),
                [{'id':'1','item':'Torch','state':'carried','slots':0}],
                [{'id':'1','item':'Torch','state':'carried'}]*2,
                loadout('Helmet','Helmet',state='equipped')]:
            with self.assertRaises(ValueError):inventory.apply_inventory(core,entries)
            self.assertEqual(core,before)
        cart=inventory.apply_inventory(core,loadout('Cart (+4 slots, bulky)',state='stored'))
        self.assertEqual(cart['inventorySlots'],0)
        with self.assertRaises(ValueError):inventory.apply_inventory({'ruleset':'pathfinder-1e','hitProtection':4},[])

    def test_item_catalog_is_not_mutable_by_callers_and_books_are_not_cast(self):
        value=inventory.item('Shield');value['armor']=100
        self.assertEqual(inventory.item('Shield')['armor'],1)
        core=inventory.apply_inventory(cairn.core_from_rolls(rolls()),loadout('Spellbook: X-Ray Vision'))
        self.assertEqual(core['inventorySlots'],1)
        self.assertNotIn('fatigue',core)
