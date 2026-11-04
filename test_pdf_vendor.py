import hashlib
import json
from pathlib import Path
import unittest
from scripts.make_rule_pdf_fixture import fixture


class PdfDistributionTests(unittest.TestCase):
    def test_pinned_local_assets_match_manifest_and_retain_resource_licenses(self):
        root=Path(__file__).parent/'static'/'vendor'/'pdfjs-6.5.438'
        manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['version'],'6.5.438')
        for relative,spec in manifest['files'].items():
            data=(root/relative).read_bytes()
            self.assertEqual(len(data),spec['bytes']);self.assertEqual(hashlib.sha256(data).hexdigest(),spec['sha256'])
        for license in ('LICENSE','cmaps/LICENSE','standard_fonts/LICENSE_FOXIT','standard_fonts/LICENSE_LIBERATION','wasm/LICENSE_JBIG2','wasm/LICENSE_OPENJPEG','wasm/LICENSE_QCMS'):
            self.assertTrue((root/license).is_file())
        self.assertFalse(any('quickjs' in name.lower() or 'sandbox' in name.lower() for name in manifest['files']))

    def test_pdf_example_is_the_original_dependency_free_fixture(self):
        self.assertEqual((Path(__file__).parent/'test_fixtures'/'rule-source-example.pdf').read_bytes(),fixture())


if __name__=='__main__':unittest.main()
