import copy
import importlib.util
import unittest
from pathlib import Path
from cbengine.validation import load
from cbengine.crosscheck import compare


class CrosscheckTests(unittest.TestCase):
    def setUp(self): self.spec=load(Path(__file__).parents[1]/'examples/crosscheck-flat.json')

    def test_missing_external_library_is_not_a_pass(self):
        r=compare(self.spec)
        self.assertEqual(r['external']['status'],'not-run')
        self.assertGreater(r['engine']['dirty_price'],90)
        self.assertGreater(r['engine']['dv01'],0)

    def test_clean_full_conversion_uses_declared_accrued(self):
        self.spec['accrued_interest']=2
        r=compare(self.spec)
        self.assertAlmostEqual(r['engine']['dirty_price']-r['engine']['clean_price'],2)

    def test_incompatible_conventions_are_rejected(self):
        for key,value in [('curve_kind','yield_to_maturity'),('compounding','continuous'),
                          ('day_count','ACT/ACT'),('settlement_date','2026-10-10'),('credit_basis','')]:
            with self.assertRaises(ValueError): compare(dict(self.spec,**{key:value}))

    def test_duplicate_or_past_cashflows_rejected(self):
        s=copy.deepcopy(self.spec);s['cashflows'][1]['date']=s['cashflows'][0]['date']
        with self.assertRaises(ValueError):compare(s)

    def test_misaligned_conventions_do_change_price(self):
        r=compare(self.spec)
        self.assertGreater(abs(r['engine']['dirty_price']-r['misaligned_controls']['same_numeric_rate_as_continuous']),.1)
        self.assertGreater(abs(r['engine']['dirty_price']-r['misaligned_controls']['integer_year_instead_of_actual_dates']),.01)

    def test_core_engine_refuses_explicit_wrong_curve_basis(self):
        from cbengine.engine import diagnose
        d=load(Path(__file__).parents[1]/'examples/demo.json')
        with self.assertRaises(ValueError): diagnose(dict(d,discount_curve_kind='yield_to_maturity'))
        with self.assertRaises(ValueError): diagnose(dict(d,discount_compounding='continuous'))
        s=copy.deepcopy(self.spec);s['cashflows'][0]['date']=s['as_of']
        with self.assertRaises(ValueError):compare(s)

    @unittest.skipUnless(importlib.util.find_spec('QuantLib'),'optional external comparison')
    def test_quantlib_price_and_modified_duration(self):
        r=compare(self.spec,True)
        self.assertEqual(r['external']['status'],'matched')
        self.assertLess(abs(r['external']['price_difference']),1e-8)
