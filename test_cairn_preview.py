import json
import subprocess
import unittest
from systems import cairn_creator as creator,cairn_engine
from test_cairn_creator import draft_with_bonus


class CairnPreviewParityTests(unittest.TestCase):
    def test_browser_calculation_matches_authoritative_server_for_supported_gear_and_choices(self):
        examples=[];expected=[];resources=cairn_engine.resources()
        for bonus in (1,6,14,18):
            for weapon in (1,6,15,20):
                draft=draft_with_bonus(bonus)
                draft['core']['STR']=[2,3,4];draft['core']['WIL']=[4,4,5]
                draft['gear']['weapons']=weapon
                draft['gear']=dict(sorted(draft['gear'].items())) # Wire ordering must not change the sheet.
                if draft['bonus'] is None:
                    draft=creator.choose_bonus(draft,'tools' if bonus==1 else 'armor','player',lambda sides:20)
                chosen=next(g['options'][0] for g in creator.equipment_options(draft) if g['id']=='weapons')
                choices={'weapons':{'weapons':chosen},'swap':['STR','WIL'],
                    'identity':{'name':20,'background':19},'disposition':{'torch':'stored'}}
                if bonus==14:choices['disposition']['bonus:0']='equipped'
                sheet=creator.preview(draft,choices,'player')
                fields=('abilities','name','background','inventory','inventorySlots','armor','hitProtection','age','gold')
                expected.append({key:sheet[key] for key in fields})
                examples.append({'draft':draft,'choices':choices})
        script="const fs=require('node:fs'),rules=require('./static/cairn-creation-rules.js');const data=JSON.parse(fs.readFileSync(0,'utf8'));process.stdout.write(JSON.stringify(data.examples.map(e=>{const value=rules.calculate(e.draft,e.choices,data.resources);delete value.pending;return value})));"
        result=subprocess.run(['node','-e',script],input=json.dumps({'resources':resources,'examples':examples}),capture_output=True,text=True,encoding='utf-8',check=True)
        self.assertEqual(json.loads(result.stdout),expected)
