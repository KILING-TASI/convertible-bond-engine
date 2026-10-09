import copy
import unittest
from cbengine.analysis import enrich
from cbengine.market import classify_error,DataSourceError,fetch_snapshot


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        self.snapshot={'code':'113042','quote_time':'2026-10-09','quote_price':100,'gaps':[]}
        self.spec={'code':'113042','as_of':'2026-10-09','cashflow_source':'教学','price_basis_source':'教学',
                   'price_basis':'confirmed_dirty','cashflows':[{'date':'2027-10-09','date_status':'confirmed','coupon':5,'redemption':100}]}

    def test_curve_free_gross_yield_and_missing_tax(self):
        r=enrich(self.snapshot,self.spec)['independent_analysis']['yield']
        self.assertAlmostEqual(r['gross'],.05)
        self.assertIsNone(r['net'])
        self.assertEqual(r['status'],'calculated_from_declared_inputs')

    def test_assumptions_stay_scenario_and_clean_price_adjusts(self):
        self.spec['cashflows'][0]['date_status']='assumed'
        self.assertEqual(enrich(self.snapshot,self.spec)['independent_analysis']['yield']['status'],'scenario')
        self.spec.update(price_basis='confirmed_clean',accrued_interest=5,accrued_interest_source='教学')
        self.assertAlmostEqual(enrich(self.snapshot,self.spec)['independent_analysis']['yield']['gross'],0)

    def test_tax_and_date_conflicts(self):
        self.spec['cashflows'][0].update(net_payment=104,tax_source='教学税务')
        self.assertAlmostEqual(enrich(self.snapshot,self.spec)['independent_analysis']['yield']['net'],.04)
        self.spec['as_of']='2026-10-08'
        with self.assertRaises(ValueError): enrich(self.snapshot,self.spec)

    def count_spec(self):
        return {'code':'113042','as_of':'2026-10-09','stock_price_basis':'unadjusted','observation_source':'教学未复权行情','calendar_source':'教学日历',
                'conversion_history_source':'教学调价记录','conversion_history_complete':True,
                'trading_days':['2026-10-08','2026-10-09'],
                'observations':[{'date':'2026-10-08','stock_price':12},{'date':'2026-10-09','stock_price':12}],
                'conversion_history':[{'effective_on':'2026-01-01','price':10,'source':'教学'},
                                      {'effective_on':'2026-10-09','price':8,'source':'教学'}],
                'clauses':{'call':{'source':'教学','window':2,'count':1,'ratio':1.3,'direction':'above','inclusive':True,
                                  'rolling':True,'active_from':'2026-01-01','active_until':'2027-01-01','reset_on':[]}}}

    def test_counts_use_each_days_effective_conversion_price(self):
        spec=self.count_spec(); r=enrich(self.snapshot,spec)['independent_analysis']['clauses']
        self.assertEqual(r['states']['call']['count'],1)
        self.assertEqual([o['conversion_price'] for o in r['observations']],[10,8])
        spec['conversion_history_complete']=False
        state=enrich(self.snapshot,spec)['independent_analysis']['clauses']['states']['call']
        self.assertIsNone(state['trigger_condition_met'])
        self.assertTrue(state['conditional_observed_result'])

    def test_missing_day_and_missing_conversion_history_rejected(self):
        spec=self.count_spec(); spec['observations'].pop()
        with self.assertRaises(ValueError): enrich(self.snapshot,spec)
        spec=self.count_spec(); spec['conversion_history'][0]['effective_on']='2026-10-09'
        with self.assertRaises(ValueError): enrich(self.snapshot,spec)

    def test_error_categories(self):
        self.assertEqual(classify_error(ModuleNotFoundError())[0],'missing_dependency')
        self.assertEqual(classify_error(ConnectionError())[0],'connection_failure')
        self.assertEqual(classify_error(KeyError())[0],'schema_failure')
        error=DataSourceError('quote','connection_failure','断连')
        self.assertIsInstance(error,ValueError)
        self.assertEqual(error.category,'connection_failure')

    def test_dated_analysis_does_not_use_undated_comparison(self):
        def fetch(endpoint):
            if endpoint=='quote': return [{'转债代码':'113042','转债最新价':120,'正股最新价':12,'转股价':10}]
            if endpoint.startswith('history:'): return [{'日期':'2026-10-09','收盘价':100,'转股价值':100}]
            if endpoint.startswith('info:'): return [{'SECURITY_CODE':'113042'}]
            return []
        r=fetch_snapshot('113042',fetch,require_dated=True)
        self.assertEqual(r['quote_price'],100)
        self.assertEqual(r['quote_mode'],'historical_close')
        self.assertEqual(r['source_failures'][0]['category'],'undated_quote')
