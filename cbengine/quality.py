"""Snapshot quality separates availability, freshness, consistency and eligibility."""
from datetime import datetime, timezone, timedelta, date
from .engine import iso_date
from .market import number
from .archive import bindings


def assess(snapshot,as_of=None,max_lag_days=3):
    if not isinstance(snapshot,dict) or snapshot.get('kind')!='market_snapshot':
        raise ValueError('质量检查需要市场快照')
    bindings(snapshot)
    if type(max_lag_days) is not int or max_lag_days<0 or max_lag_days>366:
        raise ValueError('最大行情滞后须为0至366日整数')
    cutoff=iso_date(as_of or datetime.now(timezone(timedelta(hours=8))).date().isoformat())
    issues=[]
    price=number(snapshot.get('quote_price'),True)
    parity=number(snapshot.get('conversion_value'),True)
    availability='available' if price is not None and parity is not None and snapshot.get('status')!='failed' else 'missing'
    if availability=='missing': issues.append('报价或平价缺失，不能进行行情指标展示。')
    freshness='unknown'; lag=None
    if snapshot.get('quote_time'):
        day=iso_date(snapshot['quote_time'])
        lag=(date.fromisoformat(cutoff)-date.fromisoformat(day)).days
        freshness='future' if lag<0 else 'stale' if lag>max_lag_days else 'within-limit'
        if freshness in ('future','stale'): issues.append('行情日期晚于截止日或超过允许滞后。')
    else: issues.append('行情时间未知，不能认证数据新鲜度。')
    fetched=datetime.fromisoformat(snapshot['fetched_at'])
    if fetched.tzinfo is None: raise ValueError('获取时间需要时区偏移')
    if fetched.astimezone(timezone(timedelta(hours=8))).date().isoformat()>cutoff:
        issues.append('快照取得时间晚于评估截止日，不能作为当时可得证据。')
        freshness='future-acquisition'
    consistency='not-checkable'
    if availability=='available':
        supplied=number(snapshot.get('conversion_premium'))
        consistency='matched' if supplied is not None and abs(supplied-(price/parity-1))<=1e-8 else 'mismatch'
        if consistency=='mismatch': issues.append('转股溢价率与报价/平价复算不一致。')
    cashflow_status='not-assessed'
    level=snapshot.get('issue_term_evidence',{}).get('pdf_verification',{}).get('status','not-verified')
    display=availability=='available' and consistency=='matched' and freshness=='within-limit'
    return {'as_of':cutoff,'max_lag_calendar_days':max_lag_days,'quote_age_calendar_days':lag,
            'availability':availability,'freshness':freshness,'consistency':consistency,
            'within_dated_display_policy':display,'issue_pdf_check':level,
            'cashflow_pricing_eligibility':cashflow_status,'issues':issues,
            'limitations':['质量状态仅检查保存快照，不重新联网，不保证实时、日历完整或源数据真实。',
                           '通过展示检查不代表可用于含权定价、现金流估值或回测。']}
