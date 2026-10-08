import argparse
import json
from pathlib import Path
from .engine import diagnose
from .batch import screen, portfolio, validated_batch
from .market import fetch_snapshot
from .report import render


def main():
    parser = argparse.ArgumentParser(description="可转债 L1 可审计诊断")
    parser.add_argument("input", type=Path, nargs='?', help="单债、持仓或市场快照 JSON")
    parser.add_argument('--code', help='六位转债代码，显式联网获取当前快照')
    parser.add_argument('--format', choices=['json','markdown','html'], default='json')
    parser.add_argument("--out", type=Path)
    parser.add_argument('--mode', choices=['diagnose','screen','portfolio'], default='diagnose')
    parser.add_argument('--max-price', type=float)
    parser.add_argument('--max-premium', type=float, help='小数，例如0.3')
    parser.add_argument('--min-net-ytm', type=float, help='小数，例如0.02')
    parser.add_argument('--exclude-call-risk', action='store_true')
    args = parser.parse_args()
    try:
        if bool(args.code) == bool(args.input):
            raise ValueError('提供输入文件或--code，两者只能选一个')
        if args.code and args.mode != 'diagnose':
            raise ValueError('--code 当前只支持单债资料卡')
        data = fetch_snapshot(args.code) if args.code else json.loads(args.input.read_text(encoding="utf-8-sig"))
        filters = (args.max_price, args.max_premium, args.min_net_ytm)
        if args.mode != 'screen' and (any(v is not None for v in filters) or args.exclude_call_risk):
            raise ValueError('screen filters require --mode screen')
        market = isinstance(data,dict) and data.get('kind') == 'market_snapshot'
        if market and args.mode != 'diagnose': raise ValueError('市场资料不具备现金流及条款证据，不能用于筛选或组合定价')
        if market: result=data
        elif args.mode == 'portfolio': result = portfolio(data)
        elif args.mode == 'screen': result = screen(data,*filters,args.exclude_call_risk)
        else: result = validated_batch(data) if isinstance(data,list) else diagnose(data)
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
