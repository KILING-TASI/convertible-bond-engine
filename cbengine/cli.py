import argparse
import json
from pathlib import Path
from .engine import diagnose


def main():
    parser = argparse.ArgumentParser(description="可转债 L1 可审计诊断")
    parser.add_argument("input", type=Path, help="单债对象或单债对象列表 JSON")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.input.read_text(encoding="utf-8-sig"))
        result = [diagnose(d) for d in data] if isinstance(data, list) else diagnose(data)
        output = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        parser.exit(2, f"输入错误：{exc}\n")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output+"\n", encoding="utf-8")
    else:
        print(output)


if __name__ == "__main__":
    main()
