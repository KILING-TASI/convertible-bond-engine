import unittest
from cbengine.rules import evaluate,catalog
from cbengine.engine import clause_state


class RuleTests(unittest.TestCase):
    def setUp(self):
        self.context={'as_of':'2026-10-09','market':'SZSE','board':'chinext','phase':'ordinary'}

    def get(self,id,context=None):
        return next(r for r in evaluate(context or self.context)['checks'] if r['rule_id']==id)

    def test_catalog_scopes_and_no_universal_clause_threshold(self):
        data=catalog(); self.assertEqual(len(data['rules']),14)
        for r in data['rules']:
            if r['category']=='issuer_specific': self.assertEqual(r['parameters'],{})
            if r['category']=='official_reference': self.assertTrue(r['sources'])

    def test_ipo_gate_distinct_from_unit(self):
        self.context['ipo_market_value']=5000
        r=self.get('SZSE-IPO-QUOTA')['result']
        self.assertFalse(r['market_value_gate_met']); self.assertEqual(r['market_value_quota_shares'],0)
        self.context['ipo_market_value']=10000
        self.assertEqual(self.get('SZSE-IPO-QUOTA')['result']['market_value_quota_shares'],1000)
        self.context['ipo_market_value']=14999
        self.assertEqual(self.get('SZSE-IPO-QUOTA')['result']['market_value_quota_shares'],1000)

    def test_sse_units_and_declared_upper_limit(self):
        c=dict(self.context,market='SSE',board='main',ipo_market_value=20000,
               online_subscription_limit=1500,online_limit_source='教学发行上限')
        r=self.get('SSE-IPO-QUOTA',c)['result']
        self.assertEqual(r['market_value_quota_shares'],2000)
        self.assertEqual(r['quantity_under_provided_limit'],1500)
        c['online_subscription_limit']=1001
        with self.assertRaises(ValueError): evaluate(c)

    def test_stamp_tax(self):
        self.context['stock_sale_amount']=100000
        self.assertEqual(self.get('STOCK-SELL-STAMP')['result']['tax_before_broker_rounding'],50)

    def test_ordinary_permission_and_delisting_exception(self):
        self.context['stock_permission']=False
        self.assertEqual(self.get('CHINEXT-CONVERSION')['status'],'permission_condition_not_met')
        self.context['phase']='delisting_period'
        self.assertEqual(self.get('CHINEXT-CONVERSION')['status'],'exception_reference')
        self.assertEqual(self.get('CHINEXT-DELISTING-EXCEPTION')['status'],'exception_reference')

    def test_missing_permission_is_not_false(self):
        self.assertEqual(self.get('CHINEXT-CONVERSION')['status'],'missing_input')

    def test_date_and_scope_are_not_guessed(self):
        self.context['as_of']='2026-10-10'
        self.assertEqual(self.get('STOCK-SELL-STAMP')['status'],'date_unverified')
        self.context['as_of']='2025-01-01'
        self.assertEqual(self.get('SZSE-IPO-QUOTA')['status'],'date_unverified')
        self.context.update(market='SSE',board='chinext')
        with self.assertRaises(ValueError): evaluate(self.context)

    def test_issuer_thresholds_never_activate_from_examples(self):
        self.context['remaining_balance']=1000
        self.assertEqual(self.get('CB-BALANCE-CALL')['status'],'issuer_evidence_required')
        self.assertIsNone(self.get('CB-BALANCE-CALL')['result'])

    def test_strict_comparison_at_exact_boundary(self):
        clause={'source':'教学条款','window':1,'count':1,'ratio':.85,'direction':'below',
                'rolling':True,'active_from':'2026-10-09','active_until':'2026-10-09','reset_on':[], 'inclusive':False}
        obs=[{'date':'2026-10-09','stock_price':17,'conversion_price':20}]
        self.assertEqual(clause_state(clause,obs,'2026-10-09')['count'],0)
        clause['inclusive']=True
        self.assertEqual(clause_state(clause,obs,'2026-10-09')['count'],1)
        clause['direction']='above'; clause['inclusive']=False
        self.assertEqual(clause_state(clause,obs,'2026-10-09')['count'],0)

    def test_legacy_equality_explicitly_marked(self):
        clause={'source':'教学条款','window':1,'count':1,'ratio':1,'direction':'above','rolling':True,
                'active_from':'2026-10-09','active_until':'2026-10-09','reset_on':[]}
        obs=[{'date':'2026-10-09','stock_price':20,'conversion_price':20}]
        self.assertEqual(clause_state(clause,obs,'2026-10-09')['comparison_basis'],'legacy-inclusive-assumption')
        clause['inclusive']='false'
        with self.assertRaises(ValueError): clause_state(clause,obs,'2026-10-09')

    def test_decimal_barrier_does_not_create_false_strict_hit(self):
        clause={'source':'教学条款','window':1,'count':1,'ratio':.29,'direction':'above','rolling':True,
                'active_from':'2026-10-09','active_until':'2026-10-09','reset_on':[],'inclusive':False}
        obs=[{'date':'2026-10-09','stock_price':29,'conversion_price':100}]
        self.assertEqual(clause_state(clause,obs,'2026-10-09')['count'],0)
        clause['inclusive']=True
        self.assertEqual(clause_state(clause,obs,'2026-10-09')['count'],1)
