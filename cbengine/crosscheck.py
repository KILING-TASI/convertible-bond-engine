"""Optional external check of fixed gross cashflows on aligned annual zero curves."""
from .engine import iso_date,finite,source,year_fraction,diagnose
from .validation import digest
import math,re


def compare(spec,quantlib=False):
    if not isinstance(spec,dict): raise ValueError('对照输入须为对象')
    as_of=iso_date(spec['as_of'])
    if spec.get('settlement_date')!=as_of: raise ValueError('首批只支持结算日等于估值日')
    if spec.get('day_count')!='ACT/365F' or spec.get('compounding')!='annual_effective':
        raise ValueError('首批须对齐ACT/365F和年有效复利')
    kind=spec.get('curve_kind')
    if kind not in ('flat_zero_spot','dated_zero_spot'): raise ValueError('只接受平坦或日期节点零息曲线，不接受到期收益率曲线')
    if spec.get('credit_basis') not in ('included_in_rate','risk_free_only'):
        raise ValueError('须明确信用因素包含于利率或只用无风险曲线')
    if spec.get('face_value')!=100: raise ValueError('首批金额均按100面值归一')
    if not isinstance(spec.get('currency'),str) or not re.fullmatch('[A-Z]{3}',spec['currency']):
        raise ValueError('须明确统一三字母币种；不执行汇率换算')
    source(spec.get('source'))
    rate=finite(spec['rate'],'zero rate') if kind=='flat_zero_spot' else None
    nodes=[]
    if kind=='dated_zero_spot':
        for node in spec['curve_nodes']:
            day=iso_date(node['date']);z=finite(node['rate'],'node zero rate')
            if day<=as_of or (nodes and day<=nodes[-1][0]): raise ValueError('零息节点日期須未来且递增')
            nodes.append((day,z))
        if not nodes: raise ValueError('零息节点不得为空')
    if any(z<=-.98 for z in ([rate] if rate is not None else [z for d,z in nodes])):
        raise ValueError('已有±200bp重估要求零息率大于-0.98')
    accrued=finite(spec['accrued_interest'],'accrued interest')
    if accrued<0: raise ValueError('应计利息不可为负')
    source(spec.get('accrued_interest_basis'))
    include=spec.get('include_settlement_date_flows',False)
    if type(include) is not bool: raise ValueError('付息日边界声明须为布尔值')
    previous=None; flows=[]; dated=[]; future=[]; immediate=0
    for cf in spec['cashflows']:
        day=iso_date(cf['date']); amount=finite(cf['gross_payment'],'gross payment',True)
        if day<as_of or (previous is not None and day<=previous): raise ValueError('现金流须不早于估值日且日期严格递增')
        if day==as_of and 'include_settlement_date_flows' not in spec: raise ValueError('同日付息必须显式声明是否包含')
        previous=day;dated.append((day,amount))
        if day==as_of:
            if include: immediate+=amount
        else:
            flows.append((year_fraction(as_of,day),amount));future.append((day,amount))
    if not flows: raise ValueError('首批须至少一笔未来现金流')
    if nodes and any(day not in dict(nodes) for day,amount in future):
        raise ValueError('非平坦首批须现金流日期与零息节点重合，不认证跨节点插值一致')
    points=[[.000001,rate],[max(t for t,a in flows)+1,rate]] if rate is not None else [[year_fraction(as_of,d),z] for d,z in nodes]
    if len(points)==1: points.append([points[0][0]+1,points[0][1]])
    # Reuse the existing valuation and risk implementation, not a new DV01 engine.
    local=diagnose({'code':'FIXED-CASHFLOW-CHECK','as_of':as_of,'dirty_price':100,
                   'stock_price':1,'conversion_price':1,'coupon_tax_rate':0,
                   'cashflow_source':spec['source'],'curve_source':spec['source'],
                   'discount_curve_kind':'zero_spot','discount_compounding':'annual_effective',
                   'discount_curve':points,
                   'cashflows':[{'date':day,'coupon':0,'redemption':amount,'redemption_tax':0} for day,amount in future],
                   'clauses':{'call':None,'put':None,'reset':None}})
    pv=local['bond_floor']+immediate; modified=local['modified_duration_parallel']*local['bond_floor']/pv
    engine={'dirty_price':pv,'clean_price':pv-accrued,'macaulay_duration':local['duration']*local['bond_floor']/pv,
            'modified_duration':modified,'dv01':local['dv01']}
    controls={'same_numeric_rate_as_continuous':immediate+sum(a*math.exp(-rate*t) for t,a in flows),
              'integer_year_instead_of_actual_dates':immediate+sum(a/(1+rate)**(i+1) for i,(t,a) in enumerate(flows)),
              'note':'刻意不对齐的教学反例，不是可替代估值；整数年反例只对应此年度示例。'} if rate is not None else {'note':'非平坦节点对照，不以单一YTM久期比较曲线平移风险。'}
    external={'status':'not-run','reason':'未请求可选QuantLib对照；不构成外部验证通过。'}
    if quantlib:
        try: import QuantLib as ql
        except ImportError: raise ValueError('QuantLib未安装；只在独立验证环境按需安装，不是运行依赖') from None
        def qdate(text):
            y,m,d=map(int,text.split('-'));return ql.Date(d,m,y)
        ref=qdate(as_of); dc=ql.Actual365Fixed()
        def make_curve(bump=0):
            if rate is not None: return ql.FlatForward(ref,rate+bump,dc,ql.Compounded,ql.Annual)
            return ql.ZeroCurve([ref]+[qdate(d) for d,z in nodes],[nodes[0][1]+bump]+[z+bump for d,z in nodes],
                               dc,ql.NullCalendar(),ql.Linear(),ql.Compounded,ql.Annual)
        curve=make_curve()
        leg=[ql.SimpleCashFlow(amount,qdate(day)) for day,amount in dated]
        def npv(c): return ql.CashFlows.npv(leg,ql.YieldTermStructureHandle(c),include,ref,ref)
        external_pv=npv(curve)
        if rate is not None:
            interest=ql.InterestRate(rate,dc,ql.Compounded,ql.Annual)
            external_duration=ql.CashFlows.duration(leg,interest,ql.Duration.Modified,include,ref)
        else:
            bump=.000001
            external_duration=(npv(make_curve(-bump))-npv(make_curve(bump)))/(2*bump*external_pv)
        tolerance=1e-8 if rate is not None else 1e-7
        external={'status':'matched' if abs(external_pv-pv)<1e-8 and abs(external_duration-modified)<tolerance else 'mismatch',
                  'library':'QuantLib','version':ql.__version__,'dirty_price':external_pv,
                  'clean_price':external_pv-accrued,'modified_duration':external_duration,
                  'dv01':external_pv*external_duration*.0001,
                  'price_difference':external_pv-pv,'duration_difference':external_duration-modified,
                  'tolerance':1e-8,'duration_tolerance':tolerance,
                  'risk_basis':'flat-modified-yield-duration' if rate is not None else 'annual-zero-curve-parallel-shift',
                  'adapter':'SimpleCashFlow + FlatForward/ZeroCurve + CashFlows.npv; duration or curve bump'}
    return {'type':'fixed-cashflow-crosscheck','input_sha256':digest(spec),'inputs':spec,'engine':engine,
            'external':external,'misaligned_controls':controls,'alignment':{'gross_cashflows':'explicit-dates-and-amounts','settlement_date':as_of,
                'currency':spec['currency'],'face_value':100,
                'day_count':'ACT/365F','compounding':'annual_effective','curve_kind':kind,'include_settlement_date_flows':include,
                'credit_basis':spec['credit_basis'],'clean_price':'dirty-minus-declared-accrued-interest'},
            'limitations':['固定税前现金流算例，不覆盖转股、滚动强赎、下修、回售或发行人自由裁量。',
                           '应计息由输入声明，未验证真实票息起止；贴现率为教学假设，不是市场曲线。',
                           '价格与修正久期口径已对齐；相符不证明源数据真实或含权价格正确。',
                           '不构建市场曲线、不覆盖跨节点非平坦插值、到期收益率曲线转换或违约模型。']}


if __name__=='__main__':
    import argparse,json
    from pathlib import Path
    from .validation import load
    p=argparse.ArgumentParser();p.add_argument('input',type=Path);p.add_argument('--quantlib',action='store_true');p.add_argument('--out',type=Path)
    a=p.parse_args()
    try:
        r=compare(load(a.input),a.quantlib);text=json.dumps(r,ensure_ascii=False,indent=2,allow_nan=False)
        if a.out:
            a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(text+'\n',encoding='utf-8')
        else:print(text)
        if r['external']['status']=='mismatch':p.exit(3)
    except (ValueError,KeyError,TypeError,OSError) as e:p.exit(2,str(e)+'\n')
