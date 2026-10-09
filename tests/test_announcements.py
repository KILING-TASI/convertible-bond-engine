import unittest
from cbengine.announcements import normalize_notices, discover, title_categories, attach_reviews
from cbengine.report import render


class AnnouncementTests(unittest.TestCase):
    def setUp(self):
        self.snapshot={'kind':'market_snapshot','status':'partial','code':'113042','name':'上银转债',
                       'fetched_at':'2026-10-09T12:00:00+08:00','underlying_code':'601229',
                       'sources':{},'gaps':[]}
        self.row={'代码':'601229','公告标题':'上海银行关于上银转债转股价格调整的公告',
                  '公告时间':'2026-06-02','公告链接':'http://www.cninfo.com.cn/new/disclosure/detail?announcementId=1'}

    def normalized(self,rows):
        return normalize_notices(rows,'601229','113042','上银转债','2026-01-01','2026-10-09')

    def test_title_is_candidate_not_effective_action(self):
        n=self.normalized([self.row])['entries'][0]
        self.assertEqual(n['categories'],['conversion_price_candidate'])
        self.assertFalse(n['body_reviewed'])
        self.assertFalse(n['changes_applied'])
        self.assertIsNone(n['effective_date'])
        self.assertEqual(n['bond_identity'],'title_match')

    def test_no_call_negation_precedes_redemption(self):
        self.assertEqual(title_categories('关于不提前赎回可转债的公告'),['no_call_candidate'])
        self.assertEqual(title_categories('关于停止转股的公告'),['conversion_suspension_candidate'])
        self.assertEqual(title_categories('关于不向下修正转股价格的公告'),['no_reset_candidate'])

    def test_wrong_issuer_future_date_and_unsafe_link_filtered(self):
        a=dict(self.row,代码='123456')
        b=dict(self.row,公告时间='2026-10-10')
        c=dict(self.row,公告链接='javascript:alert(1)')
        r=self.normalized([a,b,c,self.row,self.row])
        self.assertEqual(len(r['entries']),1)
        self.assertEqual(r['discarded_rows'],3)

    def test_conflicting_duplicates_rejected(self):
        b=dict(self.row,公告标题='关于上银转债付息的公告')
        with self.assertRaises(ValueError): self.normalized([self.row,b])

    def test_generic_title_not_confirmed_identity(self):
        r=self.normalized([dict(self.row,公告标题='关于可转债转股结果的公告')])
        self.assertEqual(r['entries'][0]['bond_identity'],'issuer_candidate')

    def test_interval_and_issuer_validation(self):
        for start,end,issuer in [('2020-01-01','2026-10-09',None),
                                 ('2026-10-09','2026-10-10',None),
                                 ('2026-10-10','2026-10-09',None),
                                 ('2026-01-01','2026-10-09','123456')]:
            with self.assertRaises(ValueError): discover(self.snapshot,start,end,issuer,lambda endpoint:[])

    def test_fetch_failure_preserves_quote(self):
        def failure(endpoint): raise ValueError('timeout')
        r=discover(self.snapshot,fetcher=failure)
        self.assertEqual(r['status'],'partial')
        self.assertEqual(r['announcements']['status'],'failed')
        self.assertNotIn('announcements',self.snapshot)

    def test_report_links_and_no_mutation(self):
        r=discover(self.snapshot,'2026-01-01','2026-10-09',fetcher=lambda endpoint:[self.row])
        before=list(r['gaps'])
        text=render(r,'html')
        self.assertIn('后续公告候选',text)
        self.assertIn('href="https://www.cninfo.com.cn/',text)
        self.assertIn('未核对',text)
        self.assertEqual(r['gaps'],before)

    def review(self,url):
        return {'bond_code':'113042','announcement_url':url,
                'document_url':'https://static.cninfo.com.cn/finalpage/example.PDF',
                'review_method':'教学核对','reviewed_on':'2026-10-09','published_on':'2026-06-02',
                'effective_on':'2026-06-08','event_type':'conversion_price_adjustment',
                'facts':{'old_conversion_price':8.57,'new_conversion_price':8.35}}

    def test_review_preserves_announcement_and_effective_dates(self):
        s=discover(self.snapshot,'2026-01-01','2026-10-09',fetcher=lambda endpoint:[self.row])
        n=s['announcements']['entries'][0]
        reviewed=attach_reviews(s,[self.review(n['source_url'])])
        r=reviewed['announcements']['entries'][0]
        self.assertEqual(r['published_on'],'2026-06-02')
        self.assertEqual(r['effective_date'],'2026-06-08')
        self.assertTrue(r['body_reviewed'])
        self.assertFalse(r['changes_applied'])
        self.assertFalse(n['body_reviewed'])
        self.assertNotIn('conversion_price',reviewed)

    def test_review_mismatch_and_conflict_rejected(self):
        s=discover(self.snapshot,'2026-01-01','2026-10-09',fetcher=lambda endpoint:[self.row])
        review=self.review(s['announcements']['entries'][0]['source_url'])
        for key,value in [('bond_code','123456'),('published_on','2026-06-01'),
                          ('announcement_url','https://www.cninfo.com.cn/unknown'),('effective_on',None)]:
            with self.assertRaises(ValueError): attach_reviews(s,[dict(review,**{key:value})])
        with self.assertRaises(ValueError): attach_reviews(s,[review,review])
        with self.assertRaises(ValueError): attach_reviews([], [review])
