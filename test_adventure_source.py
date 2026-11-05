import copy
import unittest
import zlib
from unittest.mock import patch
import adventure_source as source
from rule_pack_authoring import canonical
from rule_pack_runtime import RulePackError


class AdventureSourceTests(unittest.TestCase):
    def test_source_does_not_consume_the_independent_gameplay_state_budget(self):
        import rule_pack_campaign as campaign
        state=campaign.initial_state({'goal':'g'*2000})
        state['adventureSource']=source.create('Aventura','x'*12000,'provided-adventure')
        game={key:value for key,value in state.items() if key not in ('authoring','authoringWorkspace','adventureSource')}
        with patch.object(campaign,'MAX_BYTES',len(canonical(game).encode())+1):campaign._size(state)
    def test_original_unicode_text_and_private_asset_roundtrip(self):
        original='  Una aventura propia.\r\n\nArda guarda una carta. 🕯️\n'
        record=source.create('Aventura propia',original,'provided-adventure')
        state={'ruleset':'rule-pack','adventureSource':record};before=copy.deepcopy(state)
        light,asset=source.detach(state)
        self.assertEqual(state,before);self.assertIsNone(light['adventureSource'])
        self.assertEqual(source.decode(light['adventureSourceRef'],asset['packed'])['text'],original)
        self.assertEqual(source.detach(light),(light,None))

    def test_tampering_limits_policy_and_compressed_trailing_data_are_rejected(self):
        record=source.create('Aventura','Texto original','provided-adventure');ref=source.reference(record)
        for changes in [{'text':'otro'},{'sha256':'0'*64},{'format':'other'}]:
            with self.assertRaises(RulePackError):source.validate(record|changes)
        for text,policy in [('', 'provided-adventure'),('x'*12001,'provided-adventure'),('x\x00','provided-adventure'),('Texto','unknown')]:
            with self.assertRaises(RulePackError):source.create('Aventura',text,policy)
        packed=zlib.compress(canonical(record).encode())
        for bad in [packed+b'extra',b'broken',zlib.compress(b'x'*51000)]:
            with self.assertRaises(RulePackError):source.decode(ref,bad)

    def test_retrieval_is_bounded_deterministic_and_relevant_without_changing_original(self):
        text='Introducción. '+'a'*1600+'\n'+'Bosque de robles: una torre y un secreto. '+'b'*1600+'\n'+'Archivo: Arda guarda las cartas. '+'c'*1600
        record=source.create('Aventura',text,'provided-adventure')
        result=source.fragments(record,'Arda archivo cartas')
        self.assertEqual(result,source.fragments(record,'Arda archivo cartas'))
        self.assertLessEqual(sum(len(f['text'].encode()) for f in result['fragments']),8000)
        self.assertTrue(any('Arda' in f['text'] for f in result['fragments']))
        self.assertEqual(source.fragments(record,opening=True)['fragments'][0]['text'],text)
        self.assertEqual(record['text'],text)
