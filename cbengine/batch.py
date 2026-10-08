"""Deterministic screens and long-only portfolio summaries; no trade instructions."""
from collections import Counter
from .engine import diagnose, finite


def validated_batch(data):
    if not isinstance(data, list) or not data:
        raise ValueError('batch must be a nonempty list')
    results = [diagnose(d) for d in data]
    if len({r['code'] for r in results}) != len(results):
        raise ValueError('duplicate security codes')
    if len({r['as_of'] for r in results}) != 1:
        raise ValueError('all securities must share an as_of date')
    return results


def screen(data, max_price=None, max_premium=None, min_ytm=None, exclude_call_risk=False):
    results = validated_batch(data)
    if max_price is not None: max_price = finite(max_price, 'max_price', True)
    if max_premium is not None: max_premium = finite(max_premium, 'max_premium')
    if min_ytm is not None: min_ytm = finite(min_ytm, 'min_ytm')
    accepted, rejected = [], []
    for r in results:
        reasons = []
        if max_price is not None and r['dirty_price'] > max_price: reasons.append('price')
        if max_premium is not None and r['conversion_premium'] > max_premium: reasons.append('conversion_premium')
        if min_ytm is not None and r['yields']['maturity']['net'] < min_ytm: reasons.append('net_ytm')
        if exclude_call_risk:
            call = r['clauses']['call']
            protected = r['no_call_until'] and r['as_of'] <= r['no_call_until']
            if call.get('status') == 'unknown': reasons.append('call_status_unknown')
            if call.get('trigger_condition_met') and not protected: reasons.append('call_condition_met')
        (rejected if reasons else accepted).append({'code':r['code'], 'reasons':reasons} if reasons else r)
    return {'as_of':results[0]['as_of'], 'filters':dict(max_price=max_price,max_premium=max_premium,min_net_ytm=min_ytm,exclude_call_risk=exclude_call_risk),
            'accepted':accepted, 'rejected':rejected,
            'note':'按输入快照筛选，不代表全市场覆盖；强赎过滤不构成完整风险排除。'}


def portfolio(data):
    results = validated_batch(data)
    quantities = [finite(d['quantity'], 'quantity in 100-face bonds', True) for d in data]
    market = sum(q*r['dirty_price'] for q,r in zip(quantities,results))
    floor = sum(q*r['bond_floor'] for q,r in zip(quantities,results))
    parity = sum(q*r['conversion_value'] for q,r in zip(quantities,results))
    weights = [q*r['dirty_price']/market for q,r in zip(quantities,results)]
    holdings = [dict(code=r['code'],quantity=q,market_value=q*r['dirty_price'],weight=w,
                     clauses=r['clauses'],warnings=r['warnings']) for q,r,w in zip(quantities,results,weights)]
    return {'as_of':results[0]['as_of'], 'market_value':market, 'bond_floor_value':floor,
            'conversion_value':parity,'distance_to_floor':(market-floor)/market,
            'conversion_premium':market/parity-1,'bond_premium':market/floor-1,
            'dv01':sum(q*r['dv01'] for q,r in zip(quantities,results)),
            'effective_holdings':1/sum(w*w for w in weights), 'holdings':holdings,
            'warning_counts':dict(Counter(w for r in results for w in r['warnings'])),
            'note':'数量按每张面值100元；组合溢价按总价值之比；DV01仅为纯债部分。'}
