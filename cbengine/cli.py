import argparse
import json
from pathlib import Path
from .engine import diagnose
from .batch import screen, portfolio, validated_batch


def main():
    parser = argparse.ArgumentParser(description="可转债 L1 可审计诊断")
    parser.add_argument("input", type=Path, help="单债对象或单债对象列表 JSON")
    parser.add_argument("--out", type=Path)
    parser.add_argument('--mode', choices=['diagnose','screen','portfolio'], default='diagnose')
    parser.add_argument('--max-price', type=float)
    parser.add_argument('--max-premium', type=float, help='小数，例如0.3')
    parser.add_argument('--min-net-ytm', type=float, help='小数，例如0.02')
    parser.add_argument('--exclude-call-risk', action='store_true')
    args = parser.parse_args()
    try:
        data = json.loads(args.input.read_text(encoding="utf-8-sig"))
        filters = (args.max_price, args.max_premium, args.min_net_ytm)
        if args.mode != 'screen' and (any(v is not None for v in filters) or args.exclude_call_risk):
            raise ValueError('screen filters require --mode screen')
        if args.mode == 'portfolio': result = portfolio(data)
        elif args.mode == 'screen': result = screen(data,*filters,args.exclude_call_risk)
        else: result = validated_batch(data) if isinstance(data,list) else diagnose(data)
        output = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(output+"\n", encoding="utf-8")
    except (ValueError, KeyError, TypeError, OSError) as exc:
        parser.exit(2, f"输入错误：{exc}\n")
    if not args.out:
        print(output)


if __name__ == "__main__":
    main()
