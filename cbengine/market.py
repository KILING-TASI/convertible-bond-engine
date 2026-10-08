"""Optional public data snapshots; third-party estimates are never engine valuations."""
import json
import math
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta

SOURCES = {
    'quote': 'https://quote.eastmoney.com/center/fullscreenlist.html#convertible_comparison',
    'redemption': 'https://www.jisilu.cn/data/cbnew/#redeem',
}


def code_string(value):
    text = str(value).strip()
    if not re.fullmatch(r'[0-9]{6}', text):
        raise ValueError('转债代码必须为六位数字')
    return text


def number(value, positive=False):
    if value is None or isinstance(value, bool): return None
    try: result = float(str(value).replace(',', '').strip())
    except (TypeError, ValueError): return None
    if not math.isfinite(result) or (positive and result <= 0): return None
    return result


def worker(endpoint):
    import akshare as ak
    frame = ak.bond_cov_comparison() if endpoint == 'quote' else ak.bond_cb_redeem_jsl()
    # Pandas serialization replaces NaN with null and preserves unicode.
    return json.loads(frame.to_json(orient='records', force_ascii=False, date_format='iso'))


def fetch_rows(endpoint, timeout=30):
    try:
        process = subprocess.run([sys.executable, '-X', 'utf8', '-m', 'cbengine.market', endpoint],
                                 capture_output=True, text=True, encoding='utf-8', timeout=timeout)
    except subprocess.TimeoutExpired:
        raise ValueError(f'{endpoint} 接口超时（{timeout}秒）') from None
    if process.returncode:
        raise ValueError(f'{endpoint} 接口失败，请检查网络或安装可选依赖：pip install ".[market]"')
    try: rows = json.loads(process.stdout)
    except ValueError: raise ValueError(f'{endpoint} 返回非JSON数据') from None
    if not isinstance(rows, list): raise ValueError(f'{endpoint} 返回结构异常')
    return rows


def normalize(code, quote_rows, redemption_rows, fetched_at, errors=None):
    code = code_string(code)
    matches = [r for r in quote_rows if str(r.get('转债代码', '')).strip() == code]
    if len(matches) != 1:
        raise ValueError('未找到唯一转债行情；可能已摘牌、接口缺漏或代码有误')
    row = matches[0]
    price = number(row.get('转债最新价'), True)
    stock = number(row.get('正股最新价'), True)
    conversion = number(row.get('转股价'), True)
    parity = 100*stock/conversion if stock and conversion else None
    premium = price/parity-1 if price and parity else None
    redemption = [r for r in redemption_rows if str(r.get('代码', '')).strip() == code]
    gaps = ['现金流与到期兑付含息口径未从募集说明书核实：不计算债底与YTM。',
            '零息信用曲线缺失：不输出引擎债底、久期或DV01。',
            '逐只条款原文、历史有效转股价及交易日记录缺失：不计算条款触发状态。',
            '报价时间未由接口提供；获取时间不代表行情时间，可能是休市或延迟报价。',
            '报价净全价口径未核实：展示行情报价，不送入现金流定价引擎。']
    if price is None: gaps.append('转债报价缺失或无效。')
    if parity is None: gaps.append('正股价或转股价缺失：无法计算转股价值。')
    if len(redemption) > 1: gaps.append('强赎记录不唯一：不展示冲突记录。')
    return {'schema_version':1, 'kind':'market_snapshot', 'status':'partial', 'code':code,
            'name':str(row.get('转债名称') or code), 'fetched_at':fetched_at,
            'quote_time':None, 'sources':SOURCES, 'quote_price':price,
            'stock_price':stock, 'conversion_price':conversion,
            'conversion_value':parity, 'conversion_premium':premium,
            'provider_estimates':{'bond_floor':number(row.get('纯债价值'), True),
                                  'note':'东方财富第三方估值；方法和曲线未核实，不是本引擎计算。'},
            'provider_redemption':redemption[0] if len(redemption) == 1 else None,
            'gaps':gaps, 'errors':errors or [], 'raw_quote':row}


def fetch_snapshot(code, fetcher=fetch_rows):
    code = code_string(code)
    timestamp = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds')
    errors = []
    try: quotes = fetcher('quote')
    except ValueError as exc:
        return {'schema_version':1,'kind':'market_snapshot','status':'failed','code':code,
                'name':code,'fetched_at':timestamp,'quote_time':None,'sources':SOURCES,
                'errors':[str(exc)],'gaps':['行情获取失败，未生成任何估值结果。']}
    try: redemption = fetcher('redemption')
    except ValueError as exc:
        redemption=[]; errors.append(str(exc))
    try: return normalize(code,quotes,redemption,timestamp,errors)
    except ValueError as exc:
        return {'schema_version':1,'kind':'market_snapshot','status':'failed','code':code,
                'name':code,'fetched_at':timestamp,'quote_time':None,'sources':SOURCES,
                'errors':errors+[str(exc)],'gaps':['行情无法唯一匹配，未生成估值结果。']}


if __name__ == '__main__':
    try:
        print(json.dumps(worker(sys.argv[1]), ensure_ascii=False, allow_nan=False))
    except Exception:
        sys.exit(1)
