"""Curve-free yields and auditable observed clause counts from explicit inputs."""
from datetime import date
from copy import deepcopy
from .engine import iso_date,finite,source,year_fraction,yield_rate,clause_state
from .validation import digest


def enrich(snapshot,spec):
    if not isinstance(spec,dict) or spec.get('code')!=snapshot.get('code'):
        raise ValueError('计算底稿代码须与市场快照一致')
    as_of=iso_date(spec['as_of'])
    if snapshot.get('quote_time')!=as_of: raise ValueError('计算截止日须与有日期的行情快照一致')
    result=deepcopy(snapshot); findings={}; notes=[]
    if spec.get('cashflows'):
        source(spec.get('cashflow_source')); source(spec.get('price_basis_source'))
        basis=spec['price_basis']
        if basis not in ('confirmed_dirty','assumed_dirty','confirmed_clean'):
            raise ValueError('价格口径须为confirmed_dirty/assumed_dirty/confirmed_clean')
        price=finite(snapshot['quote_price'],'quote price',True)
        if basis=='confirmed_clean':
            source(spec.get('accrued_interest_source'))
            accrued=finite(spec['accrued_interest'],'accrued interest')
            if accrued<0: raise ValueError('应计利息不可为负')
            price+=accrued
        gross=[]; net=[]; previous=as_of; uncertain=basis=='assumed_dirty'; rows=[]
        for cf in spec['cashflows']:
            day=iso_date(cf['date'])
            if day<=previous: raise ValueError('现金流须为未来且严格递增')
            previous=day
            if cf['date_status'] not in ('confirmed','assumed'): raise ValueError('现金流日期须明确confirmed/assumed')
            uncertain=uncertain or cf['date_status']=='assumed'
            coupon=finite(cf['coupon'],'coupon'); redemption=finite(cf['redemption'],'redemption')
            if min(coupon,redemption)<0 or coupon+redemption<=0: raise ValueError('现金流金额无效')
            amount=coupon+redemption; t=year_fraction(as_of,day); gross.append((t,amount))
            if 'net_payment' in cf:
                source(cf.get('tax_source')); payment=finite(cf['net_payment'],'net payment',True)
                if payment>amount: raise ValueError('税后现金流不得超过税前')
                net.append((t,payment))
            rows.append({'date':day,'date_status':cf['date_status'],'coupon':coupon,'redemption':redemption,'gross':amount})
        findings['yield']={'status':'scenario' if uncertain else 'calculated_from_declared_inputs',
                           'gross':yield_rate(price,gross),'net':yield_rate(price,net) if len(net)==len(gross) else None,
                           'price_basis':basis,'dirty_price_used':price,'cashflows':rows,
                           'source':spec['cashflow_source'],
                           'note':'ACT/365F年复利；不需要贴现曲线。日期或全价含假设时仅为情景收益率；税后输入缺失则不计算税后。'}
        if uncertain: notes.append('兑付日或全价口径仍含假设，收益率仅为情景，不代表已公告退出结果。')
    if spec.get('observations') is not None:
        if spec.get('stock_price_basis')!='unadjusted': raise ValueError('条款观察需明确未复权正股收盘价')
        source(spec.get('observation_source')); source(spec.get('calendar_source')); source(spec.get('conversion_history_source'))
        days=spec['trading_days']; obs=spec['observations']; changes=spec['conversion_history']
        if not days or not obs or not changes: raise ValueError('交易日、正股记录和转股价历史不得为空')
        if any(iso_date(d)>as_of for d in days) or days!=sorted(set(days)):
            raise ValueError('交易日须有序、唯一且不晚于截止日')
        if [o['date'] for o in obs]!=days: raise ValueError('正股记录与所提供交易日不完整匹配，禁止补价或跳过缺日')
        for o in obs: finite(o['stock_price'],'stock close',True)
        dates=[iso_date(c['effective_on']) for c in changes]
        if dates!=sorted(set(dates)): raise ValueError('转股价变更日期须唯一且递增')
        for c in changes:
            finite(c['price'],'conversion price',True); source(c.get('source'))
        merged=[]
        for o in obs:
            applicable=[c for c in changes if c['effective_on']<=o['date']]
            if not applicable: raise ValueError('正股观察日期没有对应有效转股价')
            merged.append(dict(o,conversion_price=applicable[-1]['price']))
        complete=spec.get('conversion_history_complete')
        if type(complete) is not bool: raise ValueError('须明确转股价历史是否完整')
        if not isinstance(spec.get('clauses'),dict) or not spec['clauses'] or set(spec['clauses'])-{'call','put','reset'}:
            raise ValueError('独立计数需明确call/put/reset中至少一种条款')
        states={}
        for name,c in spec['clauses'].items():
            if c is None: states[name]={'absent':True}; continue
            if 'inclusive' not in c: raise ValueError('独立计数必须明确是否包含等号')
            s=clause_state(c,merged,as_of)
            s['evidence_status']='declared-history-not-externally-certified' if complete else 'conditional-conversion-history'
            if not complete:
                s['conditional_observed_result']=s['trigger_condition_met']
                s['trigger_condition_met']=None; s['status']='unknown'
            states[name]=s
        findings['clauses']={'states':states,'observations':merged,
                             'calendar_status':'matched-to-supplied-calendar','source':spec['observation_source'],
                             'note':'自行按当日有效转股价逐日计算；完整性声明和交易日历来源由底稿提供，不认证未披露变化。'}
    result['independent_analysis']=findings
    result['analysis_input']=deepcopy(spec)
    result['analysis_input_sha256']=digest(spec)
    if findings.get('yield'): result['gaps']=[g for g in result['gaps'] if not g.startswith('现金流与到期兑付含息口径未')]
    if findings.get('clauses'):
        result['gaps']=[g for g in result['gaps'] if not g.startswith('逐只条款原文、历史有效转股价')]
        notes.append('自建计数只覆盖底稿所列条款；交易日来源、转股价历史及公告重置的完整性仍需核实。')
    result['gaps']+=notes
    return result
