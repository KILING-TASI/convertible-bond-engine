"""Escaped Chinese cards for saved market snapshots; no network in renderer."""
import html


def markdown_text(value):
    return html.escape(str(value)).replace('\n', ' ').replace('\r', ' ').replace('|', '&#124;').replace('`','&#96;').replace('*','&#42;').replace('[','&#91;').replace(']','&#93;')


def metric(value, percent=False):
    if value is None: return '缺失'
    return f'{value*100:.2f}%' if percent else f'{value:.2f}'


def render(snapshot, format='markdown'):
    title = f"{snapshot['name']}（{snapshot['code']}）诊断卡"
    lines = [('状态', '获取失败' if snapshot['status']=='failed' else '部分资料已取得'),
             ('获取时间', snapshot['fetched_at']), ('行情时间',snapshot.get('quote_time') or '接口未提供'),
             ('行情口径','历史收盘快照' if snapshot.get('quote_mode')=='historical_close' else '即时比价表，时间未知'),
             ('转债报价',metric(snapshot.get('quote_price'))),
             ('正股报价',metric(snapshot.get('stock_price'))),
             ('转股价',metric(snapshot.get('conversion_price'))),
             ('转股价值',metric(snapshot.get('conversion_value'))),
             ('转股溢价率',metric(snapshot.get('conversion_premium'),True)),
             ('第三方纯债估值',metric(snapshot.get('provider_estimates',{}).get('bond_floor')))]
    gaps = snapshot.get('gaps',[]) + snapshot.get('errors',[])
    if 'quote_age_calendar_days' in snapshot:
        lines.append(('行情距获取日（日历天）',snapshot['quote_age_calendar_days']))
    evidence=snapshot.get('issue_term_evidence')
    if evidence:
        lines += [('原始条款证据核对日期',evidence['reviewed_on']),
                  ('原始募集说明书PDF页码',str(evidence['pdf_pages'])),
                  ('原始到期兑付总额',metric(evidence['maturity_total_payment'])),
                  ('原始末期票息',metric(evidence['final_coupon'])),
                  ('原始到期兑付是否含末期息','是' if evidence['maturity_includes_final_coupon'] else '否'),
                  ('原始回售类型',str(evidence.get('put_type','未核对')))]
        gaps.append('原始发行条款核对说明：'+evidence['review_method'])
    terms=snapshot.get('provider_terms')
    if terms:
        lines += [('第三方评级',str(terms.get('RATING') or '缺失')),
                  ('第三方到期日',str(terms.get('EXPIRE_DATE') or '缺失'))]
        for key,label in [('INTEREST_RATE_EXPLAIN','票息'),('REDEEM_CLAUSE','赎回'),('RESALE_CLAUSE','回售')]:
            if terms.get(key): gaps.append(f'第三方{label}条款摘录（待原文核验）：{str(terms[key])[:250]}')
    provider = snapshot.get('provider_redemption')
    if provider:
        lines += [('第三方强赎状态',str(provider.get('强赎状态') or '缺失')),
                  ('第三方强赎计数',str(provider.get('强赎天计数') or '缺失'))]
        gaps += ['强赎字段来自集思录，未核对公告原文；缺失记录不等于无风险。']
    caution = '第三方纯债估值不是本引擎债底。未核实现金流和条款，不输出完整定价或买卖结论。'
    if snapshot.get('is_demo'): caution = '教学快照，非真实行情。' + caution
    if format == 'html':
        e = html.escape
        rows = ''.join(f'<tr><th>{e(a)}</th><td>{e(str(b))}</td></tr>' for a,b in lines)
        items = ''.join(f'<li>{e(str(g))}</li>' for g in gaps)
        sources = ''.join(f'<li>{e(k)}：{e(v)}</li>' for k,v in snapshot['sources'].items())
        return f'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>{e(title)}</title><style>body{{max-width:850px;margin:40px auto;padding:0 20px;font:16px/1.7 system-ui;color:#183044;background:#f6f8fb}}table{{width:100%;border-collapse:collapse;background:white}}th,td{{text-align:left;padding:10px;border-bottom:1px solid #dde4ec}}.notice{{padding:16px;background:#fff2cf}}li{{overflow-wrap:anywhere}}</style><h1>{e(title)}</h1><p class="notice">{e(caution)}</p><table>{rows}</table><h2>资料缺口</h2><ul>{items}</ul><h2>来源</h2><ul>{sources}</ul></html>'
    text = f'# {markdown_text(title)}\n\n{caution}\n\n| 项目 | 结果 |\n|---|---|\n'
    text += ''.join(f'| {markdown_text(a)} | {markdown_text(b)} |\n' for a,b in lines)
    text += '\n## 资料缺口\n\n' + ''.join(f'- {markdown_text(g)}\n' for g in gaps)
    text += '\n## 来源\n\n' + ''.join(f'- {markdown_text(k)}：{markdown_text(v)}\n' for k,v in snapshot['sources'].items())
    return text
