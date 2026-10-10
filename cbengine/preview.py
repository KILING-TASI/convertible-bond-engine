"""Generate a reproducible teaching preview from existing demo inputs."""
import argparse
import html
import json
import sys
from importlib.metadata import version, PackageNotFoundError
from pathlib import Path
from .engine import diagnose
from .event_chain import build
from .validation import load, digest
from importlib.resources import files


def generate(input_path, out_dir, interactive=False):
    spec=load(input_path)
    if isinstance(spec,dict) and 'price_basis' in spec and 'dirty_price' not in spec:
        raise ValueError('这是收益率底稿，不能单独作为教学定价预览；见 examples/README.md，用主入口 --analysis-input 配合匹配的市场快照')
    if spec.get('is_demo') is not True:
        raise ValueError('此预览只接受明确标记is_demo=true的教学输入')
    if out_dir.exists():
        raise ValueError('输出目录已存在，请选择新的目录；预览不覆盖已有文件')
    result=diagnose(spec)
    chain=build({'code':spec['code']},spec['as_of'])
    try:engine_version=version('convertible-bond-engine')
    except PackageNotFoundError:engine_version='0.12.2'
    bundle={'report_schema_version':1,'method_version':'dated-cashflow-1+zero-parallel-1+evidence-clause-1', 'interaction_method_version':'frozen-selection-1' if interactive else None,'type':'teaching-preview','engine_version':engine_version,'preview_status':'main-branch-demo; not included in v0.11.0 tag',
            'is_demo':True,'as_of':spec['as_of'],'input_sha256':digest(spec),'diagnosis':result,'event_chain':chain}
    e=html.escape
    rows=''.join(f"<tr><td>{e(c['date'])}</td><td>{c['years']:.6f}</td><td>{c['gross']:.2f}</td><td>{c['pv']:.6f}</td></tr>" for c in result['cashflows'])
    gross=result['yields']['maturity']['gross']*100
    curve_rates=' / '.join(f'{r*100:g}%' for r in sorted(set(c['spot'] for c in result['cashflows'])))
    final=spec['cashflows'][-1]
    payment_note=f"末期 {final['coupon']+final['redemption']:.2f} = 票息 {final['coupon']:.2f} + 兑付组件 {final['redemption']:.2f}"
    call=result['clauses']['call']
    call_count=f"{call['count']} / {call['required']}" if call else '未提供'

    page=f"""<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>可转债教学结果预览</title>
<style>*{{box-sizing:border-box}}body{{margin:0;background:#f1f5f9;color:#17283e;font-family:'Microsoft YaHei',sans-serif;font-size:15px;line-height:1.6}}main{{max-width:1140px;margin:30px auto;padding:0 24px}}.badge{{display:inline-block;padding:5px 12px;border-radius:6px;background:#dbeafe;color:#154892;font-weight:bold}}h1{{font-size:28px;margin:15px 0 4px}}.muted{{color:#52657a}}.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:24px 0}}.card,section{{background:white;border:1px solid #d8e2ee;border-radius:10px;padding:18px}}.value{{font-size:30px;font-weight:bold;margin:6px 0}}.note{{font-size:13px;color:#52657a}}.unknown{{color:#946000}}h2{{font-size:19px;margin:0 0 10px}}section{{margin:16px 0}}table{{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}}th,td{{padding:8px 12px;text-align:right;border-bottom:1px solid #e5eaf0}}th:first-child,td:first-child{{text-align:left}}th{{background:#f1f5f9}}.footer{{font-size:13px}}a{{color:#145db1}}@media(max-width:800px){{.grid{{grid-template-columns:repeat(2,1fr)}}main{{margin:18px auto;padding:0 12px}}}}</style>
<main><span class="badge">教学算例 · 非真实证券行情</span><h1>可转债现金流与条款证据预览</h1><div class="muted">引擎 {e(engine_version)} · 主分支演示 · 估值日 {e(spec['as_of'])} · 每 100 元面值，金额单位：元</div>
<div class="grid"><div class="card"><div>输入全价</div><div class="value">{result['dirty_price']:.2f}</div><div class="note">使用者给定的教学全价，非市场报价。</div></div>
<div class="card"><div>纯债现值</div><div class="value">{result['bond_floor']:.4f}</div><div class="note">给定现金流与 {e(curve_rates)} 教学曲线下的现值，不是保护承诺。</div></div>
<div class="card"><div>到期条件年化收益率（税前）</div><div class="value">{gross:.4f}%</div><div class="note">按教学兑付假设求 IRR；不是收益预测或完整最差收益率。</div></div>
<div class="card"><div>当前条款权利状态</div><div class="value unknown">未知</div><div class="note">强赎、下修、回售均为 unknown；缺完整公告及法律事件证据。</div></div></div>
<section><h2>现金流从哪里来</h2><div class="muted">来源：{e(spec['cashflow_source'])}。{e(payment_note)}。</div><table><thead><tr><th>支付日</th><th>ACT/365F 年数</th><th>税前支付</th><th>贴现现值</th></tr></thead><tbody>{rows}</tbody></table></section>
<section><h2>价格与风险的计算范围</h2><p>年有效零息率节点 {e(curve_rates)}，逐实际支付日计算，跨闰年使用 ACT/365F。曲线平移修正久期 <b>{result['modified_duration_parallel']:.6f}</b>；纯债 DV01 <b>{result['dv01']:.6f}</b> 元 / 基点。未计算含权价或 OAS。</p><p class="note">本预览不执行外部库对照。已有 QuantLib 验证覆盖固定现金流、平坦曲线、现金流日期与非平坦节点重合处及同日支付边界；不验证跨节点插值或实际应计息。</p></section>
<section><h2>观察结果不能替代正式权利</h2><p>教学 L1 强赎观察计数 {e(call_count)}，只描述输入序列。独立事件链没有公告原文或完整调价历史，当前权利状态仍未知；不能据此推断发行人已执行或不会执行。</p><p class="note">缺失状态随结果保留：目录未审计、原始条款未提供、后续法律事件未覆盖。不补正式结论。</p></section>
<p class="footer">可追溯文件：<a href="input.json">教学输入</a> · <a href="result.json">完整结果与事件链</a>。仅供学习与研究，不构成投资建议；本预览没有使用第三方真实数据。</p></main></html>"""
    if interactive:
        payload=json.dumps({'inputs':spec,'result':bundle,'result_sha256':digest(bundle)},ensure_ascii=False,allow_nan=False).replace('<', '\\u003c').replace('&', '\\u0026')
        script=files('cbengine').joinpath('data/preview.js').read_text(encoding='utf-8')
        ui="""<section><h2>筛选已算诊断</h2><p class="note">筛选仅改变可见行，不改变计算或权利状态。净价及实际应计息未提供，输入仍为教学全价。</p>
<label>类别 <select id="category"><option value="all">全部</option><option value="price">价格</option><option value="yield">条件收益率</option><option value="risk">纯债风险</option><option value="clause">当前条款（未知）</option></select></label>
<label>查找 <input id="search" type="search" placeholder="诊断名称"></label><label>排序 <select id="sort"><option value="name">名称</option><option value="ascending">同单位数值升序</option><option value="descending">同单位数值降序</option></select></label>
<p id="row-count" class="note"></p><div style="overflow-x:auto"><table><thead><tr><th>诊断</th><th>已算值</th><th>单位</th><th>状态</th></tr></thead><tbody id="diagnostics"></tbody></table></div></section>
<section><h2>比较已有风险情景</h2><p class="note">全部数值来自 Python 核心冻结结果；选择静态情景不会重新定价。冲击只针对零息曲线平移，不是行情价格或收益率预测。</p>
<label><input name="scenario" type="checkbox" value="0" checked>基准</label>
<label><input name="scenario" type="checkbox" value="-200">−200 bp</label><label><input name="scenario" type="checkbox" value="-100">−100 bp</label>
<label><input name="scenario" type="checkbox" value="100" checked>＋100 bp</label><label><input name="scenario" type="checkbox" value="200">＋200 bp</label>
<div style="overflow-x:auto"><table><thead><tr><th>曲线冲击</th><th>核心精确重估现值</th><th>久期 / 凸性近似</th><th>近似误差</th></tr></thead><tbody id="scenario-results"></tbody></table></div><p id="scenario-empty" class="note"></p>
<button id="save-view" type="button">另存选择、输入与方法版本（JSON）</button><p id="saved-note" class="note">另存新文件，不写回历史结果；保留全部原结果、来源、输入摘要和未知状态。</p>
<noscript>交互需要 JavaScript；上方冻结诊断和输入链接仍可阅读。</noscript></section>"""
        page=page.replace('<p class="footer">',ui+'<p class="footer">').replace('</main></html>',f'</main><script id="frozen-report" type="application/json">{payload}</script><script>{script}</script></html>')
    out_dir.mkdir(parents=True,exist_ok=False)
    (out_dir/'input.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    (out_dir/'result.json').write_text(json.dumps(bundle,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    (out_dir/'report.html').write_text(page,encoding='utf-8')
    return bundle


def main():
    parser=argparse.ArgumentParser(description='教学结果预览；新目录输出，不覆盖')
    parser.add_argument('--interactive',action='store_true',help='筛选和比较已计算结果，不在浏览器重新定价');
    parser.add_argument('input',type=Path);parser.add_argument('--out-dir',type=Path,required=True)
    args=parser.parse_args()
    output_existed=args.out_dir.exists()
    try:
        generate(args.input,args.out_dir,args.interactive)
    except (ValueError,KeyError,TypeError,OSError) as exc:
        if output_existed or isinstance(exc,FileExistsError):
            hint='输出目录已存在；请换一个新目录，例如 local-data/preview-second-run。不会覆盖旧文件。'
        elif isinstance(exc,OSError):
            hint='输入读取或结果写入失败；请核对输入路径、目录权限及可用空间，再用新目录重试。'
        elif isinstance(exc,ValueError) and '收益率底稿' in str(exc):
            hint=str(exc)
        elif isinstance(exc,KeyError):
            key=exc.args[0] if exc.args else None
            allowed={'code','as_of','cashflows','date','coupon','redemption','redemption_tax','dirty_price','stock_price','conversion_price','coupon_tax_rate','discount_curve','clauses'}
            hint=('缺少字段 '+key+'；' if isinstance(key,str) and key in allowed else '输入字段不完整；')+'请参照 examples/demo.json 核对教学标识、现金流、日期及曲线。'
        else:
            hint='输入无效；请参照 examples/demo.json 核对 JSON 格式、is_demo=true、未来现金流日期、金额和曲线节点。'
        parser.exit(2,hint+'\n')
    print('已生成教学预览（非真实行情）。结果目录：'+str(args.out_dir.resolve()),file=sys.stderr)
    print('请打开：'+str((args.out_dir/'report.html').resolve())+'；输入与完整结果另存为 input.json / result.json。',file=sys.stderr)

if __name__=='__main__':main()
