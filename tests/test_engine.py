import copy
import json
import unittest
from pathlib import Path
from cbengine.engine import diagnose, yield_rate, present_value, clause_state, spot


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((Path(__file__).parents[1]/'examples/demo.json').read_text(encoding='utf-8'))

    def test_cashflow_pv(self):
        flows = [(1,.3),(2,.5),(3,1),(4,111.5)]
        self.assertAlmostEqual(present_value(flows,.045),95.12083273003,places=9)

    def test_irr_reprices_cashflows(self):
        flows = [(1,.3),(2,.5),(3,1),(4,111.5)]
        y = yield_rate(118.5,flows)
        self.assertAlmostEqual(present_value(flows,y),118.5,places=9)
        self.assertTrue(-.02 < y < 0)

    def test_irregular_dates_tax_and_dv01(self):
        r = diagnose(self.data)
        self.assertAlmostEqual(r['conversion_value'],105.2)
        self.assertLess(r['yields']['maturity']['net'],r['yields']['maturity']['gross'])
        up, down = copy.deepcopy(self.data), copy.deepcopy(self.data)
        for p in up['discount_curve']: p[1] += .0001
        for p in down['discount_curve']: p[1] -= .0001
        actual = (diagnose(down)['bond_floor']-diagnose(up)['bond_floor'])/2
        self.assertAlmostEqual(actual,r['dv01'],places=7)

    def test_coupon_not_double_counted(self):
        d=copy.deepcopy(self.data)
        d['cashflows'][-1].update(redemption=108.5)
        diff=diagnose(self.data)['bond_floor']-diagnose(d)['bond_floor']
        self.assertAlmostEqual(diff,1.5/(1.045)**(1461/365))

    def test_rollout_and_equality(self):
        c=self.data['clauses']['call']
        observations=self.data['observations']
        for i,o in enumerate(observations): o['stock_price']=26 if i<15 else 20
        r=clause_state(c,observations,self.data['as_of'])
        self.assertEqual(r['count'],15)
        self.assertTrue(r['trigger_condition_met'])
        observations.append(dict(date='2026-10-10',stock_price=20,conversion_price=20))
        r=clause_state(c,observations,'2026-10-10')
        self.assertEqual(r['count'],14)
        self.assertFalse(r['trigger_condition_met'])

    def test_historical_conversion_prices(self):
        c=self.data['clauses']['call']
        obs=[dict(date='2026-10-09',stock_price=26,conversion_price=40)]
        self.assertEqual(clause_state(c,obs,'2026-10-09')['count'],0)

    def test_reset_and_inactive(self):
        c=dict(self.data['clauses']['call'],reset_on=['2026-10-09'])
        self.assertEqual(clause_state(c,self.data['observations'],'2026-10-09')['observations'],1)
        c['active_until']='2026-01-02'
        self.assertFalse(clause_state(c,self.data['observations'],'2026-10-09')['active'])

    def test_curve_interpolation_and_no_extrapolation(self):
        self.assertAlmostEqual(spot([[1,.02],[3,.04]],2),.03)
        with self.assertRaises(ValueError): spot([[1,.02],[3,.04]],4)

    def test_invalid_inputs_rejected(self):
        for mutation in [lambda d:d.update(dirty_price=float('nan')),
                         lambda d:d.update(cashflow_source=''),
                         lambda d:d['clauses']['call'].update(source=''),
                         lambda d:d['observations'].append(d['observations'][-1]),
                         lambda d:d['cashflows'][0].update(coupon=-1)]:
            d=copy.deepcopy(self.data); mutation(d)
            with self.assertRaises(ValueError): diagnose(d)

    def test_scenario_yield_not_forecast(self):
        self.data['exit_scenarios']={'put':dict(date='2029-10-09',gross_payment=100.8,net_payment=100.64,source='教学条件场景')}
        r=diagnose(self.data)
        self.assertTrue(r['yields']['put']['conditional'])
        self.assertEqual(r['minimum_provided_yield']['net'],min(v['net'] for v in r['yields'].values()))


if __name__ == '__main__': unittest.main()
