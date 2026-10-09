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

    def test_payment_date_inclusion_is_explicit(self):
        s=copy.deepcopy(self.spec);s['cashflows'].insert(0,{'date':s['as_of'],'gross_payment':2})
        s['include_settlement_date_flows']=False;a=compare(s)['engine']
        s['include_settlement_date_flows']=True;b=compare(s)['engine']
        self.assertAlmostEqual(b['dirty_price']-a['dirty_price'],2)
        self.assertAlmostEqual(a['dv01'],b['dv01'])

    def test_nonflat_missing_cashflow_node_rejected(self):
        s=load(Path(__file__).parents[1]/'examples/crosscheck-nonflat.json');s['curve_nodes'].pop()
        with self.assertRaises(ValueError): compare(s)

    @unittest.skipUnless(importlib.util.find_spec('QuantLib'),'optional external comparison')
    def test_nonflat_parallel_risk_and_payment_boundary_match(self):
        for name in ('crosscheck-nonflat.json','crosscheck-payment-boundary.json'):
            r=compare(load(Path(__file__).parents[1]/'examples'/name),True)
            self.assertEqual(r['external']['status'],'matched')
            self.assertEqual(r['external']['risk_basis'],'annual-zero-curve-parallel-shift')
        s=copy.deepcopy(self.spec);s['cashflows'][0]['date']=s['as_of']
        with self.assertRaises(ValueError):compare(s)

    @unittest.skipUnless(importlib.util.find_spec('QuantLib'),'optional external comparison')
    def test_quantlib_price_and_modified_duration(self):
        r=compare(self.spec,True)
        self.assertEqual(r['external']['status'],'matched')
        self.assertLess(abs(r['external']['price_difference']),1e-8)

    def test_nonflat_yield_duration_is_not_curve_parallel_duration(self):
        from cbengine.engine import year_fraction,yield_rate
        s=load(Path(__file__).parents[1]/'examples/crosscheck-nonflat.json');r=compare(s);e=r['engine']
        flows=[(year_fraction(s['as_of'],c['date']),c['gross_payment']) for c in s['cashflows']]
        y=yield_rate(e['dirty_price'],flows)
        dy=sum(t*a/(1+y)**(t+1) for t,a in flows)/e['dirty_price']
        self.assertGreater(abs(dy-e['zero_curve_parallel_duration']),0.0008)
        self.assertEqual(e['modified_duration'],e['zero_curve_parallel_duration'])
        self.assertEqual(e['macaulay_duration'],e['discount_weighted_average_time'])
        self.assertEqual(r['risk_conventions']['single_ytm_modified_duration']['status'],'not-calculated')
        # Independent curve bump, not a comparison of aliases.
        bump=1e-6
        shifted=[]
        for delta in (-bump,bump):
            spec=copy.deepcopy(s)
            for n in spec['curve_nodes']:n['rate']+=delta
            shifted.append(compare(spec)['engine']['dirty_price'])
        self.assertAlmostEqual((shifted[0]-shifted[1])/(2*bump*e['dirty_price']),e['zero_curve_parallel_duration'],places=7)

    @unittest.skipUnless(importlib.util.find_spec('QuantLib'),'optional external comparison')
    def test_payment_before_on_after_matches_external_and_roll_identity(self):
        s=copy.deepcopy(self.spec);s['cashflows'].insert(0,{'date':s['as_of'],'gross_payment':2})
        values={}
        for label,day,include in [('before','2026-10-08',False),('include','2026-10-09',True),('exclude','2026-10-09',False),('after','2026-10-10',False)]:
            spec=copy.deepcopy(s);spec['as_of']=spec['settlement_date']=day;spec['include_settlement_date_flows']=include
            if label=='after':spec['cashflows']=spec['cashflows'][1:]
            r=compare(spec,True);self.assertEqual(r['external']['status'],'matched');values[label]=r['engine']
        self.assertAlmostEqual(values['include']['dirty_price']-values['exclude']['dirty_price'],2)
        self.assertAlmostEqual(values['include']['dv01'],values['exclude']['dv01'])
        factor=(1+s['rate'])**(1/365)
        self.assertAlmostEqual(values['before']['dirty_price'],values['include']['dirty_price']/factor)
        self.assertAlmostEqual(values['after']['dirty_price'],values['exclude']['dirty_price']*factor)
