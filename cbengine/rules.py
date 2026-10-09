"""Versioned rule references and scoped checks. No issuer defaults or trade orders."""
from importlib.resources import files
from decimal import Decimal, ROUND_FLOOR
from .validation import loads, digest
from .engine import iso_date, finite, source


def catalog():
    data=loads(files('cbengine').joinpath('data/market_rules.json').read_text(encoding='utf-8'))
    ids=[r['id'] for r in data['rules']]
    if len(ids)!=len(set(ids)): raise ValueError('规则ID重复')
    for r in data['rules']:
        iso_date(r['verified_on'])
        if r['effective_from']: iso_date(r['effective_from'])
    return data


def evaluate(context):
    if not isinstance(context,dict): raise ValueError('规则上下文须为对象')
    cutoff=iso_date(context['as_of'])
    market=context.get('market'); board=context.get('board'); phase=context.get('phase')
    if market not in ('SSE','SZSE','BSE'): raise ValueError('市场须明确SSE/SZSE/BSE，不由代码前缀猜测')
    if board not in ('main','star','chinext','bse'): raise ValueError('板块须明确main/star/chinext/bse')
    if (market,board) not in {('SSE','main'),('SSE','star'),('SZSE','main'),('SZSE','chinext'),('BSE','bse')}:
        raise ValueError('市场与板块冲突')
    if phase not in ('ordinary','delisting_period'): raise ValueError('阶段须明确ordinary/delisting_period')
    permission=context.get('stock_permission')
    if permission is not None and type(permission) is not bool: raise ValueError('stock_permission须为布尔值或省略')
    data=catalog(); checks=[]
    for r in data['rules']:
        applies=market in r['scope']['markets'] and board in r['scope']['boards']
        row={'rule_id':r['id'],'title':r['title'],'category':r['category'],
             'scope':r['scope'],'sources':r['sources'],'verified_on':r['verified_on'],
             'effective_from':r['effective_from'],'status':'not_applicable','result':None}
        if not applies:
            checks.append(row); continue
        time_valid=cutoff<=r['verified_on'] and (cutoff>=r['effective_from'] if r['effective_from'] else cutoff==r['verified_on'])
        if not time_valid:
            row.update(status='date_unverified',note='截止日不在本条已核对时间范围，不能套用当前参考。')
        elif r['category']=='pending_review':
            row.update(status='pending_review',note=r['statement'])
        elif r['category']=='issuer_specific':
            row.update(status='issuer_evidence_required',note=r['statement'])
        elif r['category']=='research_policy':
            row.update(status='policy_reference',note=r['statement'])
        elif r['id']=='STOCK-SELL-STAMP':
            amount=context.get('stock_sale_amount')
            if amount is None: row.update(status='reference_only',note=r['statement'])
            else:
                amount=finite(amount,'stock_sale_amount')
                if amount<0: raise ValueError('股票卖出金额不可为负')
                row.update(status='calculated',result={'rate':r['parameters']['rate'],
                           'tax_before_broker_rounding':float(Decimal(str(amount))*Decimal(str(r['parameters']['rate'])))})
        elif r['id'] in ('SSE-IPO-QUOTA','SZSE-IPO-QUOTA'):
            amount=context.get('ipo_market_value')
            if amount is None: row.update(status='missing_input',note='未提供该市场T-2日前20交易日日均合资格市值。')
            else:
                amount=finite(amount,'ipo_market_value')
                if amount<0: raise ValueError('日均市值不可为负')
                p=r['parameters']; eligible=amount>=p['entry_market_value']
                units=int((Decimal(str(amount))/Decimal(p['unit_market_value'])).to_integral_value(rounding=ROUND_FLOOR))
                quota=units*p['shares_per_unit'] if eligible else 0
                upper=context.get('online_subscription_limit')
                if upper is not None:
                    if type(upper) is not int or upper<0 or upper%p['shares_per_unit']:
                        raise ValueError('网上申购上限须为非负整数且符合申购单位')
                    source(context.get('online_limit_source'))
                row.update(status='calculated',result={'market_value_gate_met':eligible,
                           'market_value_quota_shares':quota,'provided_limit':upper,
                           'quantity_under_provided_limit':min(quota,upper) if upper is not None else None},
                           note='只计算输入市值与上限；账户资格、真实发行公告及资金情况未由本检查核实。')
        elif r['id']=='CHINEXT-CONVERSION':
            if phase=='delisting_period':
                row.update(status='exception_reference',note='退市整理阶段须核对专门例外规则，不套普通转股权限结论。')
            elif permission is None: row.update(status='missing_input',note='转股环节权限未提供，不能确认可转股。')
            else: row.update(status='permission_condition_met' if permission else 'permission_condition_not_met',
                             note='普通阶段转股参照创业板适当性要求；还需核对其他转股条件。')
        elif r['id']=='CHINEXT-DELISTING-EXCEPTION':
            row.update(status='exception_reference' if phase=='delisting_period' else 'not_applicable',
                       note=r['statement'])
        else: row.update(status='reference_only',note=r['statement'])
        checks.append(row)
    return {'catalog_version':data['version'],'catalog_sha256':digest(data),'as_of':cutoff,
            'declared_context':context,'checks':checks,
            'limitations':['市场、板块、阶段和权限来自所提供上下文，未自动核验账户或证券身份。',
                           '参考规则检查不等于所有条件均满足，不输出交易指令，不认证未来规则继续有效。',
                           '公司条款与研究风控阈值不作为统一交易所规则；缺证据保留未知。']}


if __name__=='__main__':
    import argparse,json
    from pathlib import Path
    from .validation import load
    parser=argparse.ArgumentParser(description='离线结构化规则参考检查')
    parser.add_argument('context',type=Path); parser.add_argument('--out',type=Path)
    args=parser.parse_args()
    try:
        result=evaluate(load(args.context)); text=json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)
        if args.out:
            args.out.parent.mkdir(parents=True,exist_ok=True); args.out.write_text(text+'\n',encoding='utf-8')
        else: print(text)
    except (ValueError,KeyError,TypeError,OSError) as exc: parser.exit(2,str(exc)+'\n')
