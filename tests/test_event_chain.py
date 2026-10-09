import unittest
from cbengine.event_chain import build


class EventChainTests(unittest.TestCase):
    def event(self,published='2026-06-02',effective='2026-06-08',old=8.57,new=8.35,url='https://example.org/1'):
        return {'published_on':published,'effective_date':effective,'source_url':url,'title':'教学调价',
                'body_reviewed':True,'reviewed_evidence':{'event_type':'conversion_price_adjustment',
                                                       'facts':{'old_conversion_price':old,'new_conversion_price':new}}}

    def test_original_and_current_are_separate(self):
        snapshot={'issue_term_evidence':{'scope':'original_issue_terms','document_url':'https://example.org/original'},
                  'announcements':{'entries':[self.event()]}}
        r=build(snapshot,'2026-10-09')
        self.assertEqual(r['original_terms']['scope'],'original_issue_terms')
        self.assertEqual(r['conversion_history_candidates'][0]['effective_on'],'2026-06-08')
        self.assertEqual(r['current_state']['conversion_price'],'unknown')
        self.assertNotIn('event_chain',snapshot)

    def test_publication_and_effective_dates_cannot_be_backfilled(self):
        r=build({'announcements':{'entries':[self.event()]}},'2026-06-01')
        self.assertEqual(r['events'],[]);self.assertEqual(len(r['excluded_events']),1)
        r=build({'announcements':{'entries':[self.event()]}},'2026-06-05')
        self.assertFalse(r['events'][0]['effective_at_cutoff'])
        self.assertEqual(r['conversion_history_candidates'],[])

    def test_title_candidate_cannot_change_history(self):
        n=self.event();n['body_reviewed']=False
        r=build({'announcements':{'entries':[n]}},'2026-10-09')
        self.assertEqual(r['conversion_history_candidates'],[])
        self.assertEqual(r['events'][0]['review_level'],'metadata-only')
        self.assertTrue(all(v=='unknown' for v in r['current_state'].values()))

    def test_conflicting_changes_are_gaps_not_selected_prices(self):
        a=self.event();b=self.event(new=8,url='https://example.org/2')
        r=build({'announcements':{'entries':[a,b]}},'2026-10-09')
        self.assertTrue(any('冲突' in g for g in r['gaps']))
        self.assertEqual(r['current_state']['conversion_price'],'unknown')
