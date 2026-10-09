import copy,unittest
from pathlib import Path
from cbengine.bridge import calculate
from cbengine.validation import load

class BridgeTests(unittest.TestCase):
    def setUp(self):self.spec=load(Path(__file__).parents[1]/'examples/bridge-fixed-demo.json')
    def test_clean_dirty_split_and_explicit_tax(self):
        r=calculate(self.spec);s=copy.deepcopy(self.spec);s['price_basis']='dirty';s['price']=118.5
        other=calculate(s)
        self.assertEqual(r['dirty_price'],118.5);self.assertEqual(r['clean_price'],116.5)
        self.assertAlmostEqual(r['yield_net'],other['yield_net'])
        self.assertLess(r['yield_net'],r['yield_gross'])
        self.assertAlmostEqual(r['bond_present_value'],95.10939701857427)
        self.assertTrue(all(v=='unknown' for v in r['current_rights'].values()))
        s.pop('accrued_interest');s.pop('accrued_interest_source')
        self.assertIsNone(calculate(s)['clean_price'])
    def test_missing_or_conflicting_conventions_rejected(self):
        changes=[('currency','USD'),('face_value',1000),('compounding','continuous'),('curve_kind','yield_to_maturity'),('settlement_date','2026-10-10')]
        for k,v in changes:
            s=copy.deepcopy(self.spec);s[k]=v
            with self.assertRaises(ValueError):calculate(s)
        for k in ['accrued_interest','maturity_payment']:
            s=copy.deepcopy(self.spec);s.pop(k)
            with self.assertRaises(ValueError):calculate(s)
        s=copy.deepcopy(self.spec);s['exit_scenarios']={}
        with self.assertRaises(ValueError):calculate(s)
    def test_double_coupon_tax_missing_or_curve_extrapolation_rejected(self):
        for mutate in [lambda s:s['cashflows'][-1].update(redemption=111.5),lambda s:s['cashflows'][0].pop('coupon_tax'),lambda s:s.update(discount_curve=[[.01,.045],[1,.045]]),lambda s:s['cashflows'][0].update(date=s['as_of']),lambda s:s['cashflows'][0].update(coupon_tax=1)]:
            s=copy.deepcopy(self.spec);mutate(s)
            with self.assertRaises(ValueError):calculate(s)
    def test_excludes_final_coupon_and_nonflat(self):
        s=copy.deepcopy(self.spec);s['maturity_payment'].update(includes_final_coupon=False,quoted_amount=110)
        self.assertEqual(calculate(s)['cashflows'][-1]['gross'],111.5)
        s['discount_curve']=[[.01,.02],[10,.05]]
        self.assertNotAlmostEqual(calculate(s)['bond_present_value'],95.10939701857427)
