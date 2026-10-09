"""As-of evidence chain. Discovery and listed PDF matches never certify all rights."""
from .engine import iso_date
from .archive import bindings


def build(snapshot,as_of):
    cutoff=iso_date(as_of); bindings(snapshot)
    original=snapshot.get('issue_term_evidence')
    chain=[]; conversions=[]; excluded=[]; gaps=[]
    for entry in snapshot.get('announcements',{}).get('entries',[]):
        published=iso_date(entry['published_on'])
        if published>cutoff:
            excluded.append({'source_url':entry['source_url'],'reason':'published-after-cutoff'}); continue
        review=entry.get('reviewed_evidence') if entry.get('body_reviewed') else None
        effective=entry.get('effective_date')
        if effective is not None: iso_date(effective)
        checked=entry.get('pdf_verification',{}).get('fields',[])
        node={'published_on':published,'effective_on':effective,'source_url':entry['source_url'],
              'title':entry['title'],'type':review['event_type'] if review else 'unreviewed_candidate',
              'review_level':'listed-pdf-fields-matched' if checked else 'caller-reviewed' if review else 'metadata-only',
              'matched_fields':[f['field'] for f in checked],
              'effective_at_cutoff':effective<=cutoff if effective else None}
        chain.append(node)
        if review and review['event_type']=='conversion_price_adjustment' and effective and effective<=cutoff:
            conversions.append({'effective_on':effective,'old_price':review['facts']['old_conversion_price'],
                                'price':review['facts']['new_conversion_price'],'source_url':entry['source_url'],
                                'matched_fields':node['matched_fields'],'status':'candidate-not-complete-history'})
    conversions.sort(key=lambda r:(r['effective_on'],r['source_url']))
    grouped={}
    for c in conversions: grouped.setdefault(c['effective_on'],set()).add(c['price'])
    if any(len(v)>1 for v in grouped.values()):
        gaps.append('同一生效日存在冲突转股价，不能选取当前值。')
    for a,b in zip(conversions,conversions[1:]):
        if a['price']!=b['old_price']: gaps.append('相邻调价候选不能衔接，可能缺公告或存在更正。')
    gaps += ['公告目录和指定字段匹配不能证明所有后续变更、承诺与计数重置已覆盖。',
             '当前权利状态仍未知；未发现公告不代表不强赎、不下修或无回售风险。']
    return {'as_of':cutoff,'status':'partial','original_terms':{
                'available':bool(original),'scope':original.get('scope') if original else None,
                'source_url':original.get('document_url') if original else None,
                'matched_fields':[f['field'] for f in original.get('pdf_verification',{}).get('fields',[])] if original else []},
            'events':sorted(chain,key=lambda n:(n['published_on'],n['source_url'])),
            'conversion_history_candidates':conversions,'excluded_events':excluded,
            'current_state':{name:'unknown' for name in ('conversion_price','call','no_call','reset','put')},
            'gaps':list(dict.fromkeys(gaps)),
            'note':'保留原始条款与当前状态的区别；只提供证据链，不自动改写价格历史或激活权利。'}
