import copy
import unittest
from datetime import datetime,timezone
from cbengine.coverage import collect,attach


class CoverageTests(unittest.TestCase):
    def setUp(self):
        self.spec={'issuer_code':'601229','bond_code':'113042','bond_name':'上银转债','org_id':'9900010207',
                   'identity_source':'教学映射','start':'2026-01-01','end':'2026-10-09'}
        self.rows=[{'secCode':'601229','announcementId':str(i),'announcementTime':datetime(2026,6,2,tzinfo=timezone.utc).timestamp()*1000,
                    'announcementTitle':'上银转债转股价格调整'} for i in (1,2)]

    def requester(self,p): return {'totalAnnouncement':2,'announcements':[self.rows[p['pageNum']-1]]}

    def test_pages_are_recorded_not_legal_coverage(self):
        r=collect(self.spec,self.requester)
        self.assertEqual(r['status'],'pagination_observed');self.assertEqual(len(r['pages']),2)
        self.assertEqual(r['legal_event_coverage'],'unknown')
        self.assertFalse(r['conversion_history_complete'])

    def test_page_failure_is_partial_not_an_empty_safe_result(self):
        def request(p):
            if p['pageNum']==2: raise TimeoutError()
            return self.requester(p)
        r=collect(self.spec,request)
        self.assertEqual(r['status'],'partial');self.assertEqual(r['errors'][0]['page'],2)

    def test_drifting_total_and_duplicate_ids_are_not_complete(self):
        r=collect(self.spec,lambda p:dict(self.requester(p),totalAnnouncement=2 if p['pageNum']==1 else 3))
        self.assertEqual(r['status'],'partial')
        r=collect(self.spec,lambda p:{'totalAnnouncement':2,'announcements':[self.rows[0],self.rows[0]]})
        self.assertEqual(r['status'],'partial')

    def test_attachment_checks_actual_saved_payload(self):
        r=collect(self.spec,self.requester)
        snapshot={'code':'113042','underlying_code':'601229','gaps':[]}
        self.assertIn('directory_coverage',attach(snapshot,r))
        broken=copy.deepcopy(r);broken['pages'][0]['response']['announcements'][0]['announcementTitle']='changed'
        with self.assertRaises(ValueError):attach(snapshot,broken)
