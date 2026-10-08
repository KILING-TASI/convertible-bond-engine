"""Attach explicitly reviewed issue-term evidence; never infer current actions."""
from .engine import finite, iso_date, source


def attach_terms(snapshot, evidence):
    if snapshot.get('kind') != 'market_snapshot' or snapshot.get('status') == 'failed':
        raise ValueError('条款证据只能附加到成功取得的市场快照')
    if not isinstance(evidence,dict) or evidence.get('code') != snapshot['code']:
        raise ValueError('条款证据代码必须与快照一致')
    if evidence.get('scope') != 'original_issue_terms':
        raise ValueError('仅支持原始发行条款证据，不能冒充当前条款状态')
    source(evidence.get('document_url'))
    source(evidence.get('review_method'))
    iso_date(evidence['reviewed_on'])
    pages=evidence.get('pdf_pages')
    if not isinstance(pages,list) or not pages or any(type(p) is not int or p<1 for p in pages):
        raise ValueError('证据需要明确PDF页码')
    maturity=finite(evidence['maturity_gross_payment'],'maturity payment',True)
    coupon=finite(evidence['final_coupon'],'final coupon')
    if coupon<0 or coupon>maturity or type(evidence['maturity_includes_final_coupon']) is not bool:
        raise ValueError('末期利息及是否含息字段无效')
    result=dict(snapshot)
    checked=dict(evidence)
    checked['maturity_coupon_component']=coupon
    checked['maturity_redemption_component']=maturity-coupon if evidence['maturity_includes_final_coupon'] else maturity
    checked['maturity_total_payment']=maturity if evidence['maturity_includes_final_coupon'] else maturity+coupon
    result['issue_term_evidence']=checked
    result['sources']=dict(snapshot['sources'],prospectus=evidence['document_url'])
    result['gaps']=snapshot['gaps']+['附加证据仅覆盖原始发行条款；后续变更、兑付日、税务及公告执行状态仍需核实，不自动生成YTM或当前触发状态。']
    return result
