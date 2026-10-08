import json
import unittest
from pathlib import Path
from cbengine.evidence import attach_terms


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        root=Path(__file__).parents[1]/'examples'
        self.snapshot=json.loads((root/'market-demo.json').read_text(encoding='utf-8'))
        self.evidence=json.loads((root/'terms-113042.json').read_text(encoding='utf-8'))

    def test_included_coupon_not_duplicated(self):
        r=attach_terms(self.snapshot,self.evidence)
        e=r['issue_term_evidence']
        self.assertEqual(e['maturity_redemption_component'],108)
        self.assertEqual(e['maturity_coupon_component'],4)
        self.assertEqual(e['maturity_total_payment'],112)
        self.assertNotIn('issue_term_evidence',self.snapshot)
        self.assertNotIn('yields',r)

    def test_excluded_coupon_added_once(self):
        self.evidence['maturity_includes_final_coupon']=False
        self.assertEqual(attach_terms(self.snapshot,self.evidence)['issue_term_evidence']['maturity_total_payment'],116)

    def test_mismatch_failed_and_missing_pages_rejected(self):
        self.evidence['code']='123456'
        with self.assertRaises(ValueError): attach_terms(self.snapshot,self.evidence)
        self.evidence['code']='113042'
        self.evidence['pdf_pages']=[]
        with self.assertRaises(ValueError): attach_terms(self.snapshot,self.evidence)
        self.snapshot['status']='failed'
        with self.assertRaises(ValueError): attach_terms(self.snapshot,self.evidence)
