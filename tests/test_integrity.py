import copy
import json
import tempfile
import unittest
from pathlib import Path
from cbengine.validation import loads,file_digest
from cbengine.archive import append,verify_store
from cbengine.quality import assess


class IntegrityTests(unittest.TestCase):
    def setUp(self):
        self.snapshot=json.loads((Path(__file__).parents[1]/'examples/market-demo.json').read_text(encoding='utf-8'))
        self.snapshot.update(quote_time='2026-10-08',fetched_at='2026-10-09T12:00:00+08:00')

    def test_strict_json(self):
        for value in ['{"x":1,"x":2}','{"x":NaN}','{"x":1e999}','{"x":Infinity}']:
            with self.assertRaises(ValueError): loads(value)
        self.assertEqual(loads('{"x":1}'),{'x':1})

    def test_quality_fresh_stale_unknown_and_mismatch(self):
        q=assess(self.snapshot,'2026-10-09',3)
        self.assertTrue(q['within_dated_display_policy'])
        self.assertEqual(q['quote_age_calendar_days'],1)
        self.assertEqual(assess(self.snapshot,'2026-10-20',3)['freshness'],'stale')
        self.snapshot['quote_time']=None
        self.assertEqual(assess(self.snapshot,'2026-10-09')['freshness'],'unknown')
        self.snapshot['conversion_premium']=9
        self.assertEqual(assess(self.snapshot,'2026-10-09')['consistency'],'mismatch')

    def test_acquisition_after_cutoff(self):
        self.assertEqual(assess(self.snapshot,'2026-10-08')['freshness'],'future-acquisition')
        self.snapshot['fetched_at']='2026-10-09T12:00:00'
        with self.assertRaises(ValueError): assess(self.snapshot)

    def test_append_unchanged_and_versions(self):
        with tempfile.TemporaryDirectory() as store:
            self.assertEqual(append(store,self.snapshot)['version'],1)
            self.assertEqual(append(store,self.snapshot)['status'],'unchanged')
            self.snapshot['name']='changed'
            self.assertEqual(append(store,self.snapshot)['version'],2)
            r=verify_store(store,'113042')
            self.assertEqual(r[1]['previous_hash'],r[0]['version_hash'])

    def test_snapshot_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as store:
            append(store,self.snapshot)
            p=next((Path(store)/'113042/versions').glob('*.json'))
            data=json.loads(p.read_text(encoding='utf-8')); data['snapshot']['quote_price']=1
            p.write_text(json.dumps(data),encoding='utf-8')
            with self.assertRaises(ValueError): verify_store(store,'113042')
            with self.assertRaises(ValueError): append(store,self.snapshot)

    def test_document_tampering_and_writer_lock(self):
        with tempfile.TemporaryDirectory() as store, tempfile.TemporaryDirectory() as temp:
            pdf=Path(temp)/'file.pdf'; pdf.write_bytes(b'%PDF-test')
            sig=file_digest(pdf)
            append(store,self.snapshot,[{'path':pdf,'sha256':sig}])
            root=Path(store)/'113042'
            (root/'blobs'/f'{sig}.pdf').write_bytes(b'changed')
            with self.assertRaises(ValueError): verify_store(store,'113042')
            (root/'write.lock').write_text('locked')
            with self.assertRaises(ValueError): append(store,self.snapshot)

    def test_forged_binding_and_missing_original_rejected(self):
        with tempfile.TemporaryDirectory() as store:
            self.snapshot['issue_term_evidence']={'x':1,'pdf_verification':{
                'document_sha256':'../bad','evidence_sha256':'0'*64}}
            with self.assertRaises(ValueError): append(store,self.snapshot)


try:
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject,NameObject,DecodedStreamObject
except ImportError: PdfWriter=None


@unittest.skipUnless(PdfWriter,'optional pypdf dependency')
class PdfVerificationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.pdf=Path(self.temp.name)/'source.pdf'
        writer=PdfWriter(); page=writer.add_blank_page(width=600,height=800)
        font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
        page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
        stream=DecodedStreamObject(); stream.set_data(b'BT /F1 12 Tf 40 700 Td (Example Issuer Example Prospectus Amount 112) Tj ET')
        page[NameObject('/Contents')]=writer._add_object(stream)
        writer.write(self.pdf)
        self.evidence={'document_url':'https://static.cninfo.com.cn/source.PDF','document_sha256':file_digest(self.pdf),
                       'document_identity':{'issuer':'Example Issuer','title':'Example Prospectus'},'amount':112,
                       'verification_checks':[{'field':'amount','page':1,'excerpt':'Amount 112','mode':'number','number_token':'112'}]}

    def test_actual_pdf_and_bound_field(self):
        from cbengine.pdfverify import verify_pdf
        r=verify_pdf(self.evidence,self.pdf)
        self.assertEqual(r['status'],'matched')
        self.assertEqual(r['fields'][0]['value'],112)

    def test_hash_identity_number_and_page_mismatch(self):
        from cbengine.pdfverify import verify_pdf
        cases=[]
        a=copy.deepcopy(self.evidence);a['document_sha256']='0'*64;cases.append(a)
        a=copy.deepcopy(self.evidence);a['document_identity']['issuer']='Wrong';cases.append(a)
        a=copy.deepcopy(self.evidence);a['amount']=113;cases.append(a)
        a=copy.deepcopy(self.evidence);a['verification_checks'][0]['page']=2;cases.append(a)
        for evidence in cases:
            with self.assertRaises(ValueError): verify_pdf(evidence,self.pdf)

    def test_archive_binds_checked_fields_to_document(self):
        from cbengine.pdfverify import verify_pdf
        with tempfile.TemporaryDirectory() as store:
            evidence=copy.deepcopy(self.evidence)
            evidence['pdf_verification']=verify_pdf(evidence,self.pdf)
            snapshot={'kind':'market_snapshot','code':'113042','issue_term_evidence':evidence}
            docs=[{'path':self.pdf,'sha256':file_digest(self.pdf)}]
            append(store,snapshot,docs)
            self.assertEqual(len(verify_store(store,'113042')),1)
            evidence['amount']=113
            with self.assertRaises(ValueError): append(store,snapshot,docs)
            snapshot.update(fetched_at='2026-10-09T12:00:00+08:00')
            with self.assertRaises(ValueError): assess(snapshot,'2026-10-09')
