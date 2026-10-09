"""Opt-in fixed cashflow contract; no clause or execution equivalence."""
from decimal import Decimal
from importlib.metadata import version,PackageNotFoundError
from .engine import diagnose,finite,iso_date,source,yield_rate
from .validation import digest

SCHEMA='cb-fixed-cashflow-1'


def number(value,name,positive=False):
    if type(value) not in (int,float):raise ValueError(name+': explicit numeric value required')
    return finite(value,name,positive)


def calculate(spec):
    if not isinstance(spec,dict):raise ValueError('fixed cashflow bridge requires object')
    required={'schema_version','code','as_of','settlement_date','currency','face_value','source','price_basis','price',
              'day_count','compounding','curve_kind','credit_basis','curve_source','discount_curve','cashflows','maturity_payment'}
    allowed=required|{'accrued_interest','accrued_interest_source','is_demo'}
    if not required<=set(spec) or set(spec)-allowed:raise ValueError('missing or unsupported bridge fields')
    if spec['schema_version']!=SCHEMA:raise ValueError('unsupported fixed cashflow schema')
    as_of=iso_date(spec['as_of'])
    if spec['settlement_date']!=as_of:raise ValueError('settlement date must equal as_of')
    if spec['currency']!='CNY' or type(spec['face_value']) not in (int,float) or spec['face_value']!=100:
        raise ValueError('bridge only supports CNY per 100 face value')
    if (spec['day_count'],spec['compounding'],spec['curve_kind'],spec['credit_basis'])!=('ACT/365F','annual_effective','zero_spot','included_in_rate'):
        raise ValueError('explicit annual effective credit-inclusive zero curve and ACT/365F required')
    source(spec['source']);source(spec['curve_source']);source(spec['code'])
    if 'is_demo' in spec and type(spec['is_demo']) is not bool:raise ValueError('is_demo must be boolean')
    price=number(spec['price'],'price',True)
    accrued=None
    if 'accrued_interest' in spec:
        accrued=number(spec['accrued_interest'],'accrued interest')
        if accrued<0:raise ValueError('negative accrued interest')
        source(spec.get('accrued_interest_source'))
    elif 'accrued_interest_source' in spec:raise ValueError('accrued source without amount')
    if spec['price_basis']=='clean':
        if accrued is None:raise ValueError('clean price requires explicit accrued interest')
        dirty=price+accrued;clean=price
    elif spec['price_basis']=='dirty':
        dirty=price;clean=price-accrued if accrued is not None else None
        if clean is not None and clean<=0:raise ValueError('nonpositive clean price')
    else:raise ValueError('price basis must be clean or dirty')
    curve=spec['discount_curve']
    if not isinstance(curve,list) or not curve or len(curve)>1000:raise ValueError('explicit curve nodes required')
    for node in curve:
        if not isinstance(node,list) or len(node)!=2:raise ValueError('curve node must be tenor/rate pair')
        number(node[0],'tenor',True);number(node[1],'zero rate')
    cfs=spec['cashflows']
    if not isinstance(cfs,list) or not 1<=len(cfs)<=1000:raise ValueError('explicit future cashflows required')
    core_flows=[];nets=[];previous=as_of
    for cf in cfs:
        if not isinstance(cf,dict) or set(cf)!={'date','coupon','redemption','coupon_tax','redemption_tax','source'}:
            raise ValueError('cashflow requires date, split components, explicit taxes and source')
        day=iso_date(cf['date']);source(cf['source'])
        if day<=previous:raise ValueError('cashflows must be strictly ordered and future; same-day rights not bridged')
        previous=day
        c=number(cf['coupon'],'coupon');r=number(cf['redemption'],'redemption')
        ct=number(cf['coupon_tax'],'coupon tax');rt=number(cf['redemption_tax'],'redemption tax')
        if min(c,r,ct,rt)<0 or ct>c or rt>r or c+r<=0 or c+r-ct-rt<=0:raise ValueError('invalid explicit cashflow/tax components')
        core_flows.append({'date':day,'coupon':c,'redemption':r,'redemption_tax':0})
        nets.append(c+r-ct-rt)
    maturity=spec['maturity_payment']
    if not isinstance(maturity,dict) or set(maturity)!={'includes_final_coupon','quoted_amount','source'}:
        raise ValueError('explicit maturity payment convention required')
    if type(maturity['includes_final_coupon']) is not bool:raise ValueError('maturity inclusion must be boolean')
    number(maturity['quoted_amount'],'quoted maturity amount',True);source(maturity['source'])
    last=cfs[-1]
    expected=Decimal(str(last['redemption']))+(Decimal(str(last['coupon'])) if maturity['includes_final_coupon'] else Decimal(0))
    if expected!=Decimal(str(maturity['quoted_amount'])):raise ValueError('maturity amount conflicts with split; final coupon must not be counted twice')
    # Internal placeholders satisfy the legacy full-L1 contract; conversion and clauses are never exported as equivalent.
    core=diagnose({'code':spec['code'],'as_of':as_of,'dirty_price':dirty,'stock_price':1,'conversion_price':1,
        'coupon_tax_rate':0,'cashflow_source':spec['source'],'curve_source':spec['curve_source'],
        'discount_curve_kind':'zero_spot','discount_compounding':'annual_effective','discount_curve':curve,
        'cashflows':core_flows,'clauses':{'call':None,'put':None,'reset':None},'is_demo':spec.get('is_demo',False)})
    if core['cashflows'][-1]['years']>100:raise ValueError('bridge horizon exceeds 100 years')
    rows=[]
    for cf,row,net in zip(cfs,core['cashflows'],nets):
        rows.append(dict(row,net=net,coupon_tax=cf['coupon_tax'],redemption_tax=cf['redemption_tax'],source=cf['source']))
    try:engine_version=version('convertible-bond-engine')
    except PackageNotFoundError:engine_version='0.11.0'
    return {'type':'fixed-cashflow-bridge','schema_version':SCHEMA,'method_version':'fixed-cashflow-bridge-1.0',
      'engine_version':engine_version,'input_sha256':digest(spec),'as_of':as_of,'currency':'CNY','face_value':100,
      'is_demo':spec.get('is_demo',False),'dirty_price':dirty,'clean_price':clean,'accrued_interest':accrued,
      'price_basis':spec['price_basis'],'source':spec['source'],'curve_source':spec['curve_source'],'cashflows':rows,
      'bond_present_value':core['bond_floor'],'yield_gross':core['yields']['maturity']['gross'],
      'yield_net':yield_rate(dirty,[(row['years'],net) for row,net in zip(rows,nets)]),
      'zero_curve_parallel_duration':core['modified_duration_parallel'],'discount_weighted_average_time':core['duration'],
      'convexity_parallel':core['convexity_parallel'],'dv01':core['dv01'],'sensitivity_bps':core['sensitivity_bps'],
      'risk_method_version':'zero-parallel-1','risk_basis':'annual-effective-zero-curve-parallel-shift',
      'yield_basis':'annual-effective-positive-fixed-cashflow-irr',
      'current_rights':{k:'unknown' for k in ('call','put','reset','conversion_price')},'actual_exit':'unknown',
      'limitations':['Only explicit fixed cashflow mathematics; sources are caller declarations, not authenticated.',
                     'No equivalence for clause rights, issuer discretion, actual exits, conversion value or complete YTW.',
                     'Clean price/accrual remains unknown when not supplied; no tax inference or real credit calibration.']}


def main():
    import argparse,json
    from pathlib import Path
    from .validation import load
    parser=argparse.ArgumentParser(description='Explicit optional fixed cashflow bridge')
    parser.add_argument('input',type=Path);parser.add_argument('--out-dir',type=Path,required=True)
    args=parser.parse_args()
    try:
        if args.out_dir.exists():raise ValueError('output directory exists; choose a new path')
        spec=load(args.input);result=calculate(spec)
        args.out_dir.mkdir(parents=True,exist_ok=False)
        for name,obj in [('input.json',spec),('result.json',result)]:
            (args.out_dir/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    except (ValueError,KeyError,TypeError,OSError) as exc:parser.exit(2,str(exc)+'\n')

if __name__=='__main__':main()
