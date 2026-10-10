import json
import tempfile
import unittest
from pathlib import Path
from cbengine.preview import generate

class PreviewTest(unittest.TestCase):
    def test_reproducible_teaching_result_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'preview'
            bundle=generate(Path('examples/demo.json'),out)
            self.assertAlmostEqual(bundle['diagnosis']['bond_floor'],95.10939701857427)
            self.assertTrue(all(v=='unknown' for v in bundle['event_chain']['current_state'].values()))
            before=(out/'result.json').read_bytes()
            with self.assertRaises(ValueError):generate(Path('examples/demo.json'),out)
            self.assertEqual(before,(out/'result.json').read_bytes())
    def test_analysis_attachment_gets_specific_guidance(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/"preview"
            with self.assertRaisesRegex(ValueError,"--analysis-input"):
                generate(Path("examples/analysis-demo.json"),out)
            self.assertFalse(out.exists())

    def test_real_data_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'input.json';path.write_text(json.dumps({'is_demo':False}),encoding='utf-8')
            with self.assertRaises(ValueError):generate(path,Path(d)/'preview')
            self.assertFalse((Path(d)/'preview').exists())

    def test_interactive_frozen_payload_preserves_inputs_and_escapes_source(self):
        import re
        from cbengine.validation import digest
        with tempfile.TemporaryDirectory() as d:
            spec=json.loads(Path('examples/demo.json').read_text(encoding='utf-8'))
            spec['cashflow_source']='教学来源 </script><script>unexpected()</script>'
            source=Path(d)/'input.json';source.write_text(json.dumps(spec),encoding='utf-8')
            bundle=generate(source,Path(d)/'report',True)
            page=(Path(d)/'report/report.html').read_text(encoding='utf-8')
            payload=re.search(r'<script id="frozen-report" type="application/json">(.*?)</script>',page,re.S).group(1)
            frozen=json.loads(payload)
            self.assertEqual(frozen['inputs'],spec)
            self.assertEqual(frozen['result_sha256'],digest(bundle))
            self.assertEqual(frozen['result']['interaction_method_version'],'frozen-selection-1')
            self.assertNotIn('<script>',payload)
            self.assertTrue(all(v=='unknown' for v in bundle['event_chain']['current_state'].values()))
