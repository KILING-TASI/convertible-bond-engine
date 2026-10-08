import unittest
import subprocess
import sys
import tempfile
import json
from pathlib import Path
from cbengine.market import normalize, fetch_snapshot, number, code_string, normalize_history
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
        self.assertIn('unavailable',r['errors'])

    def test_history_uses_latest_complete_not_future_or_missing(self):
        rows=[{'日期':'2026-10-08','收盘价':117.925,'转股价值':117.485,'纯债价值':111.5},
              {'日期':'2026-10-09','收盘价':None,'转股价值':120},
              {'日期':'2026-10-10','收盘价':130,'转股价值':120}]
        r=normalize_history('113042',rows,'2026-10-09T04:00:00+08:00')
        self.assertEqual(r['quote_time'],'2026-10-08')
        self.assertEqual(r['quote_age_calendar_days'],1)
        self.assertEqual(r['quote_mode'],'historical_close')
        self.assertIsNone(r['stock_price'])
        self.assertAlmostEqual(r['conversion_premium'],117.925/117.485-1)

    def test_history_rejects_duplicate_latest(self):
        row={'日期':'2026-10-08','收盘价':117,'转股价值':116}
        with self.assertRaises(ValueError): normalize_history('113042',[row,row],'2026-10-09T04:00:00+08:00')

    def test_fallback_never_merges_current_details_prices(self):
        def fetch(endpoint):
            if endpoint=='quote': raise ValueError('closed')
            if endpoint.startswith('history:'): return [{'日期':'2026-10-08','收盘价':117,'转股价值':116}]
            if endpoint.startswith('info:'): return [{'SECURITY_CODE':'113042','SECURITY_NAME_ABBR':'上银转债','CONVERT_STOCK_PRICE':999,'TRANSFER_PRICE':1}]
            return []
        r=fetch_snapshot('113042',fetch)
        self.assertEqual(r['status'],'partial')
        self.assertEqual(r['name'],'上银转债')
        self.assertEqual(r['conversion_value'],116)
        self.assertIsNone(r['stock_price'])
        self.assertIsNone(r['conversion_price'])
        self.assertIn('2026-10-08',render(r))

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
