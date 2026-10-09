import argparse
import json
from pathlib import Path
from .engine import diagnose
from .batch import screen, portfolio, validated_batch
from .market import fetch_snapshot
from .report import render
from .evidence import attach_terms
from .announcements import discover, attach_reviews
from .validation import load
from .pdfverify import verify_pdf
from .quality import assess
from .archive import append
from .rules import evaluate
from .analysis import enrich
from .event_chain import build as build_event_chain
from .coverage import attach as attach_coverage


def main():
    parser = argparse.ArgumentParser(description="可转债 L1 可审计诊断")
    parser.add_argument("input", type=Path, nargs='?', help="单债、持仓或市场快照 JSON")
    parser.add_argument('--code', help='六位转债代码，显式联网获取当前快照')
    parser.add_argument('--format', choices=['json','markdown','html'], default='json')
    parser.add_argument('--terms',type=Path,help='附加已人工核对的原始发行条款证据JSON')
    parser.add_argument('--announcements',action='store_true',help='显式联网查询发行人后续公告候选')
    parser.add_argument('--issuer-code',help='发行人股票代码；已有映射时必须一致')
    parser.add_argument('--start-date',help='公告查询开始日YYYY-MM-DD，默认回溯180日')
    parser.add_argument('--end-date',help='公告查询结束日YYYY-MM-DD，默认快照获取日')
    parser.add_argument('--notice-reviews',type=Path,help='附加公告正文核对底稿JSON，需已有候选列表')
    parser.add_argument('--terms-pdf',type=Path,help='实际募集说明书PDF，与--terms一起提供')
    parser.add_argument('--notice-pdf',type=Path,help='实际公告PDF；当前仅支持一份正文底稿')
    parser.add_argument('--store',type=Path,help='独立本地证据目录，追加版本及已核验PDF')
    parser.add_argument('--quality-as-of',help='质量评估截止日YYYY-MM-DD，默认北京时间今日')
    parser.add_argument('--max-lag-days',type=int,default=3,help='历史行情最大日历天滞后，默认3')
    parser.add_argument('--rule-context',type=Path,help='明确市场、板块、阶段与权限的规则检查JSON')
    parser.add_argument('--analysis-input',type=Path,help='独立收益率/正股条款计数底稿JSON')
    parser.add_argument('--directory-audit',type=Path,help='附加原始分页响应与查询区间证据JSON')
    parser.add_argument("--out", type=Path)
    parser.add_argument('--mode', choices=['diagnose','screen','portfolio'], default='diagnose')
    parser.add_argument('--max-price', type=float)
    parser.add_argument('--max-premium', type=float, help='小数，例如0.3')
    parser.add_argument('--min-net-ytm', type=float, help='小数，例如0.02')
    parser.add_argument('--exclude-call-risk', action='store_true')
    args = parser.parse_args()
    try:
        if args.mode!='diagnose' and any((args.announcements,args.terms,args.notice_reviews,args.rule_context)):
            raise ValueError('公告及证据附加只支持单债资料卡模式')
        if bool(args.code) == bool(args.input):
            raise ValueError('提供输入文件或--code，两者只能选一个')
        if args.code and args.mode != 'diagnose':
            raise ValueError('--code 当前只支持单债资料卡')
        if args.terms_pdf and not args.terms: raise ValueError('--terms-pdf需要--terms')
        if args.notice_pdf and not args.notice_reviews: raise ValueError('--notice-pdf需要--notice-reviews')
        data = fetch_snapshot(args.code,require_dated=bool(args.analysis_input)) if args.code else load(args.input)
        documents=[]
        filters = (args.max_price, args.max_premium, args.min_net_ytm)
        if args.mode != 'screen' and (any(v is not None for v in filters) or args.exclude_call_risk):
            raise ValueError('screen filters require --mode screen')
        market = isinstance(data,dict) and data.get('kind') == 'market_snapshot'
        if not args.announcements and any((args.issuer_code,args.start_date,args.end_date)):
            raise ValueError('公告日期与发行人参数需要--announcements')
        if args.announcements:
            if market and data.get('status')=='failed':
                data['gaps'].append('行情获取失败，已跳过后续公告查询。')
            else: data=discover(data,args.start_date,args.end_date,args.issuer_code)
        if args.terms:
            if not market: raise ValueError('--terms只支持市场快照')
            if data.get('status')!='failed':
                terms=load(args.terms)
                terms.pop('pdf_verification',None)
                data=attach_terms(data,terms)
                if args.terms_pdf:
                    checked=data['issue_term_evidence']
                    checked['pdf_verification']=verify_pdf(checked,args.terms_pdf)
                    documents.append({'path':args.terms_pdf,'sha256':checked['pdf_verification']['document_sha256']})
        if args.notice_reviews:
            if market and data.get('status')=='failed':
                data['gaps'].append('行情获取失败，已跳过正文核对底稿附加。')
            else:
                reviews=load(args.notice_reviews)
                verification=None
                data=attach_reviews(data,reviews)
                if args.notice_pdf:
                    if not isinstance(reviews,list) or len(reviews)!=1: raise ValueError('--notice-pdf当前需单份正文底稿')
                    entry=next(n for n in data['announcements']['entries'] if n['source_url']==reviews[0]['announcement_url'])
                    verification=verify_pdf(entry['reviewed_evidence'],args.notice_pdf)
                    documents.append({'path':args.notice_pdf,'sha256':verification['document_sha256']})
                if verification:
                    entry=next(n for n in data['announcements']['entries'] if n['source_url']==reviews[0]['announcement_url'])
                    entry['pdf_verification']=verification
        if market:
            if args.directory_audit: data=attach_coverage(data,load(args.directory_audit))
            if args.analysis_input: data=enrich(data,load(args.analysis_input))
            data=dict(data,data_quality=assess(data,args.quality_as_of,args.max_lag_days))
            data['event_chain']=build_event_chain(data,data['data_quality']['as_of'])
            if args.rule_context:
                context=load(args.rule_context)
                if context.get('code')!=data['code'] or context.get('as_of')!=data['data_quality']['as_of']:
                    raise ValueError('规则上下文代码/截止日须与当前诊断一致')
                data['rule_checks']=evaluate(context)
            if args.store: data['archive_receipt']=append(args.store,data,documents)
        elif args.store or args.quality_as_of or args.analysis_input or args.directory_audit or args.max_lag_days!=3:
            raise ValueError('归档和质量检查参数只支持市场快照')
        if market and args.mode != 'diagnose': raise ValueError('市场资料不具备现金流及条款证据，不能用于筛选或组合定价')
        if market: result=data
        elif args.mode == 'portfolio': result = portfolio(data)
        elif args.mode == 'screen': result = screen(data,*filters,args.exclude_call_risk)
        else: result = validated_batch(data) if isinstance(data,list) else diagnose(data)
        if args.rule_context and not market:
            if not isinstance(result,dict): raise ValueError('规则上下文仅支持单债诊断')
            context=load(args.rule_context)
            if context.get('code')!=result['code'] or context.get('as_of')!=result['as_of']:
                raise ValueError('规则上下文代码/截止日须与诊断一致')
            result['rule_checks']=evaluate(context)
        if args.format != 'json' and not market:
            raise ValueError('中文卡片格式当前仅支持市场快照')
        output = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) if args.format=='json' else render(result,args.format)
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(output+"\n", encoding="utf-8")
    except (ValueError, KeyError, TypeError, OSError) as exc:
        parser.exit(2, f"输入错误：{exc}\n")
    if not args.out:
        print(output)
    if isinstance(result,dict) and result.get('status') == 'failed':
        parser.exit(3)


if __name__ == "__main__":
    main()
