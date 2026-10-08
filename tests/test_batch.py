import copy
import json
import unittest
from pathlib import Path
from cbengine.batch import portfolio, screen, validated_batch
from cbengine.engine import diagnose, clause_state, yield_rate


class BatchTests(unittest.TestCase):
    def setUp(self):
        self.a=json.loads((Path(__file__).parents[1]/'examples/demo.json').read_text(encoding='utf-8'))
        self.b=copy.deepcopy(self.a)
        self.b.update(code='DEMO2',dirty_price=105,quantity=20)
        self.a['quantity']=10

    def test_portfolio_aggregate_ratios(self):
        r=portfolio([self.a,self.b])
        self.assertEqual(r['market_value'],3285)
        floor=diagnose(self.a)['bond_floor']*30
        self.assertAlmostEqual(r['bond_floor_value'],floor)
        self.assertAlmostEqual(r['bond_premium'],3285/floor-1)
        self.assertAlmostEqual(sum(h['weight'] for h in r['holdings']),1)
        self.assertTrue(1 < r['effective_holdings'] <= 2)

    def test_screen_boundary_and_explanations(self):
        r=screen([self.a,self.b],max_price=105)
        self.assertEqual([x['code'] for x in r['accepted']],['DEMO2'])
        self.assertEqual(r['rejected'][0]['reasons'],['price'])

    def test_incomplete_and_stale_history_unknown(self):
        c=self.a['clauses']['call']
        obs=self.a['observations'][-1:]
        self.assertIsNone(clause_state(c,obs,self.a['as_of'])['trigger_condition_met'])
        self.assertIsNone(clause_state(c,self.a['observations'],'2026-10-10')['trigger_condition_met'])
        self.a['observations']=obs
        self.assertEqual(screen([self.a],exclude_call_risk=True)['rejected'][0]['reasons'],['call_status_unknown'])

    def test_call_promise_does_not_change_observed_count(self):
        for o in self.a['observations']: o['stock_price']=27
        self.assertEqual(screen([self.a],exclude_call_risk=True)['rejected'][0]['reasons'],['call_condition_met'])
        self.a.update(no_call_until='2026-12-31',no_call_source='教学公告')
        r=screen([self.a],exclude_call_risk=True)
        self.assertEqual(len(r['accepted']),1)
        self.assertTrue(r['accepted'][0]['clauses']['call']['trigger_condition_met'])

    def test_duplicate_and_mixed_dates_rejected(self):
        with self.assertRaises(ValueError): validated_batch([self.a,self.a])
        self.b['as_of']='2026-10-10'
        with self.assertRaises(ValueError): validated_batch([self.a,self.b])
        with self.assertRaises(ValueError): validated_batch([])

    def test_invalid_quantities_and_finite_irr(self):
        self.a['quantity']=-1
        with self.assertRaises(ValueError): portfolio([self.a])
        with self.assertRaises(ValueError): yield_rate(100,[(1,float('nan'))])
        self.assertAlmostEqual(yield_rate('100',[(1,105)]),.05)

    def test_sources_and_canonical_dates(self):
        self.a['clauses']['call']['source']=None
        with self.assertRaises(ValueError): diagnose(self.a)
        self.b['as_of']='20261009'
        with self.assertRaises(ValueError): diagnose(self.b)

    def test_absent_clause_conflicts_with_scenario(self):
        self.a['clauses']['put']=None
        self.a['exit_scenarios']={'put':dict(date='2029-10-09',gross_payment=100,net_payment=100,source='test')}
        with self.assertRaises(ValueError): diagnose(self.a)
