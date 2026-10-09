"""Optional external check of fixed gross cashflows on a flat annual zero curve."""
from .engine import iso_date,finite,source,year_fraction,diagnose
from .validation import digest
import math,re


def compare(spec,quantlib=False):
    if not isinstance(spec,dict): raise ValueError('对照输入须为对象')
    as_of=iso_date(spec['as_of'])
    if spec.get('settlement_date')!=as_of: raise ValueError('首批只支持结算日等于估值日')
    if spec.get('day_count')!='ACT/365F' or spec.get('compounding')!='annual_effective':
        raise ValueError('首批须对齐ACT/365F和年有效复利')
    if spec.get('curve_kind')!='flat_zero_spot': raise ValueError('首批仅平坦零息曲线，不接受到期收益率/票面收益率曲线')
    if spec.get('credit_basis') not in ('included_in_rate','risk_free_only'):
        raise ValueError('须明确信用因素包含于利率或只用无风险曲线')
    if spec.get('face_value')!=100: raise ValueError('首批金额均按100面值归一')
    if not isinstance(spec.get('currency'),str) or not re.fullmatch('[A-Z]{3}',spec['currency']):
        raise ValueError('须明确统一三字母币种；不执行汇率换算')
    source(spec.get('source')); rate=finite(spec['rate'],'zero rate')
    if rate<=-.98: raise ValueError('首批使用已有±200bp重估，利率须大于-0.98')
    accrued=finite(spec['accrued_interest'],'accrued interest')
    if accrued<0: raise ValueError('应计利息不可为负')
    source(spec.get('accrued_interest_basis'))
    previous=as_of; flows=[]; dated=[]
    for cf in spec['cashflows']:
        day=iso_date(cf['date']); amount=finite(cf['gross_payment'],'gross payment',True)
        if day<=previous: raise ValueError('现金流须为未来且日期严格递增')
        previous=day;flows.append((year_fraction(as_of,day),amount));dated.append((day,amount))
    if not flows: raise ValueError('现金流不得为空')
    # Reuse the existing valuation and risk implementation, not a new DV01 engine.
    local=diagnose({'code':'FIXED-CASHFLOW-CHECK','as_of':as_of,'dirty_price':100,
                   'stock_price':1,'conversion_price':1,'coupon_tax_rate':0,
                   'cashflow_source':spec['source'],'curve_source':spec['source'],
                   'discount_curve_kind':'zero_spot','discount_compounding':'annual_effective',
                   'discount_curve':[[.000001,rate],[max(t for t,a in flows)+1,rate]],
                   'cashflows':[{'date':day,'coupon':0,'redemption':amount,'redemption_tax':0} for day,amount in dated],
                   'clauses':{'call':None,'put':None,'reset':None}})
    pv=local['bond_floor']; modified=local['modified_duration_parallel']
    engine={'dirty_price':pv,'clean_price':pv-accrued,'macaulay_duration':local['duration'],
            'modified_duration':modified,'dv01':local['dv01']}
    controls={'same_numeric_rate_as_continuous':sum(a*math.exp(-rate*t) for t,a in flows),
              'integer_year_instead_of_actual_dates':sum(a/(1+rate)**(i+1) for i,(t,a) in enumerate(flows)),
              'note':'刻意不对齐的教学反例，不是可替代估值；整数年反例只对应此年度示例。'}
    external={'status':'not-run','reason':'未请求可选QuantLib对照；不构成外部验证通过。'}
    if quantlib:
        try: import QuantLib as ql
        except ImportError: raise ValueError('QuantLib未安装；只在独立验证环境按需安装，不是运行依赖') from None
        def qdate(text):
            y,m,d=map(int,text.split('-'));return ql.Date(d,m,y)
        ref=qdate(as_of); dc=ql.Actual365Fixed()
        curve=ql.FlatForward(ref,rate,dc,ql.Compounded,ql.Annual)
        leg=[ql.SimpleCashFlow(amount,qdate(day)) for day,amount in dated]
        external_pv=ql.CashFlows.npv(leg,ql.YieldTermStructureHandle(curve),False,ref,ref)
        interest=ql.InterestRate(rate,dc,ql.Compounded,ql.Annual)
        external_duration=ql.CashFlows.duration(leg,interest,ql.Duration.Modified,False,ref)
        external={'status':'matched' if abs(external_pv-pv)<1e-8 and abs(external_duration-modified)<1e-8 else 'mismatch',
                  'library':'QuantLib','version':ql.__version__,'dirty_price':external_pv,
                  'clean_price':external_pv-accrued,'modified_duration':external_duration,
                  'dv01':external_pv*external_duration*.0001,
                  'price_difference':external_pv-pv,'duration_difference':external_duration-modified,
                  'tolerance':1e-8,'adapter':'SimpleCashFlow + FlatForward + CashFlows.npv/duration'}
    return {'type':'fixed-cashflow-crosscheck','input_sha256':digest(spec),'inputs':spec,'engine':engine,
            'external':external,'misaligned_controls':controls,'alignment':{'gross_cashflows':'explicit-dates-and-amounts','settlement_date':as_of,
                'currency':spec['currency'],'face_value':100,
                'day_count':'ACT/365F','compounding':'annual_effective','curve_kind':'flat_zero_spot',
                'credit_basis':spec['credit_basis'],'clean_price':'dirty-minus-declared-accrued-interest'},
            'limitations':['固定税前现金流算例，不覆盖转股、滚动强赎、下修、回售或发行人自由裁量。',
                           '应计息由输入声明，未验证真实票息起止；贴现率为教学假设，不是市场曲线。',
                           '价格与修正久期口径已对齐；相符不证明源数据真实或含权价格正确。',
                           '首批不构建曲线、不覆盖非平坦插值、到期收益率曲线转换或违约模型。']}


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
