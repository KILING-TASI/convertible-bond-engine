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
    def test_real_data_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'input.json';path.write_text(json.dumps({'is_demo':False}),encoding='utf-8')
            with self.assertRaises(ValueError):generate(path,Path(d)/'preview')
            self.assertFalse((Path(d)/'preview').exists())
