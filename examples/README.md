# 示例入口索引

全部演示结果只用于验证工具，不代表真实研究结论。以下命令在完整源码目录运行；pip安装后的示例位于环境的share/convertible-bond-engine/examples目录，也可下载完整源码取得。

| 文件 | 用途与入口 |
|---|---|
| demo.json | 完整教学定价输入：`python -m cbengine.preview examples/demo.json --out-dir reports/preview-first` |
| analysis-market-demo.json + analysis-demo.json | 市场快照与附加收益率底稿：`python -m cbengine.cli examples/analysis-market-demo.json --analysis-input examples/analysis-demo.json --quality-as-of 2026-10-09` |
| market-demo.json | 市场资料卡：`python -m cbengine.cli examples/market-demo.json --quality-as-of 2026-10-09` |
| portfolio.json | 教学组合输入：`python -m cbengine.cli examples/portfolio.json --mode portfolio` |
| rule-context-demo.json / rule-context-113042.json | `--rule-context`附加资料，代码和截止日必须与当前诊断一致，不独立定价 |
| terms-113042.json | `--terms`原始条款证据登记，配合匹配市场快照；登记不自动认证PDF |
| notice-review-113042.json | `--notice-reviews`附加公告核对底稿，需匹配候选列表；不是独立输入 |
| bridge-fixed-demo.json / bridge-nonflat-demo.json | 独立固定现金流桥接：`python -m cbengine.bridge examples/bridge-fixed-demo.json --out-dir reports/bridge-first` |
| crosscheck-*.json | 计算对照：`python -m cbengine.crosscheck examples/crosscheck-flat.json`；外部库对照另加`--quantlib`及相应依赖，不是preview入口 |
| *-result.json / market-demo.html | 已留存的示例输出，只供阅读，不作为输入重跑 |

预览输出必须使用新目录；`preview`没有原生`--auto-name`，再次运行请换目录。仓库名入口的`demo --out-dir ... --auto-name`支持自动另存。不要把附加底稿伪装成完整定价输入。
