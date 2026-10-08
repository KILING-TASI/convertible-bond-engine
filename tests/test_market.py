import unittest
import subprocess
import sys
import tempfile
import json
from pathlib import Path
from cbengine.market import normalize, fetch_snapshot, number, code_string
from cbengine.report import render


class MarketTests(unittest.TestCase):
    def setUp(self):
        self.rows=[{'转债代码':'113042','转债名称':'教学债','转债最新价':'118.5',
                    '正股最新价':21.04,'转股价':20,'纯债价值':95}]

    def test_metrics_and_provenance(self):
        r=normalize('113042',self.rows,[],'2026-10-09T12:00:00+08:00')
        self.assertAlmostEqual(r['conversion_value'],105.2)
        self.assertAlmostEqual(r['conversion_premium'],118.5/105.2-1)
        self.assertNotIn('bond_floor',r)
        self.assertIsNone(r['quote_time'])
        self.assertTrue(r['gaps'])

    def test_missing_values_never_zero(self):
        self.rows[0]['转债最新价']='-'
        self.rows[0]['转股价']=0
        r=normalize('113042',self.rows,[],'test')
        self.assertIsNone(r['quote_price'])
        self.assertIsNone(r['conversion_value'])
        self.assertIsNone(number(float('nan')))

    def test_failure_record(self):
        def fail(endpoint): raise ValueError('timeout')
        r=fetch_snapshot('113042',fail)
        self.assertEqual(r['status'],'failed')
        self.assertNotIn('quote_price',r)

    def test_redemption_failure_keeps_quote(self):
        def fetch(endpoint):
            if endpoint == 'redemption': raise ValueError('unavailable')
            return self.rows
        r=fetch_snapshot('113042',fetch)
        self.assertEqual(r['status'],'partial')
        self.assertEqual(r['errors'],['unavailable'])

    def test_duplicate_and_unknown_code(self):
        for rows in ([],self.rows*2):
            with self.assertRaises(ValueError): normalize('113042',rows,[],'test')
        with self.assertRaises(ValueError): code_string('113042;test')

    def test_renderer_escapes_external_content(self):
        self.rows[0]['转债名称']='<script>alert(1)</script>|test'
        r=normalize('113042',self.rows,[],'test')
        self.assertNotIn('<script>',render(r,'html'))
        self.assertIn('&lt;script&gt;',render(r,'html'))
        self.assertIn('&#124;',render(r))

    def test_saved_failure_returns_nonzero_and_report(self):
        r=fetch_snapshot('113042',lambda endpoint: (_ for _ in ()).throw(ValueError('unavailable')))
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)
            (p/'input.json').write_text(json.dumps(r),encoding='utf-8')
            result=subprocess.run([sys.executable,'-m','cbengine.cli',str(p/'input.json'),
                                   '--format','html','--out',str(p/'report.html')],capture_output=True)
            self.assertEqual(result.returncode,3)
            self.assertIn('获取失败',(p/'report.html').read_text(encoding='utf-8'))

    def test_offline_card_requires_no_optional_dependency(self):
        fixture=Path(__file__).parents[1]/'examples/market-demo.json'
        result=subprocess.run([sys.executable,'-X','utf8','-m','cbengine.cli',str(fixture),'--format','html'],capture_output=True)
        self.assertEqual(result.returncode,0)
        self.assertIn('教学快照',result.stdout.decode('utf-8'))


if __name__ == '__main__': unittest.main()
