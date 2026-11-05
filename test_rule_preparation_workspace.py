import copy
import unittest
from unittest.mock import patch
import rule_preparation_workspace as workspace
import rule_pack_authoring as authoring
from rule_pack_runtime import RulePackError
import test_rule_pack_authoring as fixture


def record(raw=None,scheme=authoring.SOURCE_SCHEME):
    raw=raw or fixture.request();prepared=authoring.prepare_input(raw,scheme)
    return {'request':raw,'sha256':prepared['sha256'],'sourceScheme':scheme,
        'report':authoring.validate_reply(prepared,fixture.reply(prepared))}


class PreparationWorkspaceTests(unittest.TestCase):
    def test_multiple_blocks_share_source_text_and_expand_without_mutation(self):
        first=record();other=fixture.request();other['scope']='Otro bloque de la misma página';second=record(other)
        initial=workspace.empty();stored=workspace.add(initial,first);before=copy.deepcopy(stored)
        result=workspace.add(stored,second)
        self.assertEqual(initial,workspace.empty());self.assertEqual(stored,before)
        self.assertEqual(len(result['blocks']),2);self.assertEqual(len(result['sources']),1);self.assertEqual(len(result['texts']),1)
        self.assertEqual(workspace.expand(result,first['sha256']),first)
        self.assertEqual(workspace.expand(result,second['sha256']),second)
        self.assertNotIn('text',result['blocks'][first['sha256']]['request']['document']['pages'][0])
        with patch.object(authoring,'propose',side_effect=AssertionError('Workspace called provider')),patch('rule_pack_runtime.secrets.randbelow',side_effect=AssertionError('Workspace rolled')):
            workspace.validate(result)
        expanded=workspace.expand(result,first['sha256']);expanded['request']['document']['pages'][0]['text']='Changed'
        self.assertEqual(stored,before)

    def test_legacy_import_normalizes_without_renaming_its_sources(self):
        original=record(scheme=authoring.LEGACY_SOURCE_SCHEME);original.pop('sourceScheme')
        result=workspace.from_legacy(original);workspace.validate(result)
        restored=workspace.expand(result,original['sha256'])
        self.assertEqual(restored['report'],original['report'])
        self.assertEqual(restored['sourceScheme'],authoring.LEGACY_SOURCE_SCHEME)

    def test_duplicate_block_and_capacity_reservation_fail_without_data_loss(self):
        original=record();stored=workspace.add(workspace.empty(),original);before=copy.deepcopy(stored)
        with self.assertRaises(RulePackError):workspace.add(stored,original)
        raw=fixture.request();raw['scope']='New block';prepared=authoring.prepare_input(raw)
        with patch.object(workspace,'MAX_BYTES',len(authoring.canonical(stored).encode())+100):
            with self.assertRaises(RulePackError):workspace.reserve(stored,prepared)
        self.assertEqual(stored,before)

    def test_missing_altered_or_orphaned_fragments_and_reports_reject(self):
        original=record();stored=workspace.add(workspace.empty(),original);source=next(iter(stored['sources']))
        for kind in ('missing','text','metadata','report','key','latest','orphan','orphan-text'):
            bad=copy.deepcopy(stored)
            if kind=='missing':bad['sources'].clear()
            elif kind=='text':bad['texts'][bad['sources'][source]['sha256']]='Changed'
            elif kind=='metadata':bad['sources'][source]['metadata']['title']='Changed title'
            elif kind=='report':bad['blocks'][original['sha256']]['report']['checks'][0]['expected']['energy']=99
            elif kind=='key':bad['blocks'][original['sha256']]['sha256']='wrong'
            elif kind=='latest':bad['latest']='missing'
            elif kind=='orphan':bad['sources']['orphan']=copy.deepcopy(bad['sources'][source])
            else:bad['texts']['orphan']='Hidden data'
            with self.subTest(kind=kind),self.assertRaises(RulePackError):workspace.validate(bad)

    def test_legacy_and_new_references_share_text_without_renaming_metadata(self):
        first=record(scheme=authoring.LEGACY_SOURCE_SCHEME);raw=fixture.request();raw['scope']='Otro bloque'
        second=record(raw);result=workspace.add(workspace.add(workspace.empty(),first),second)
        self.assertEqual(len(result['sources']),2);self.assertEqual(len(result['texts']),1)
        workspace.validate(result)
        self.assertEqual(workspace.expand(result,first['sha256'])['report']['candidate']['sources'],first['report']['candidate']['sources'])


if __name__=='__main__':unittest.main()
