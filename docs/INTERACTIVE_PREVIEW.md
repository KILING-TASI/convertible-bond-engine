# 冻结结果交互演示

主分支新增，尚未进入 v0.11.0 发布标签。Python 3.10+，无新运行依赖。在仓库根目录安装后：

```sh
python -m cbengine.preview examples/demo.json --interactive --out-dir local-data/interactive-first-run
```

打开新目录中的 report.html。目录存在则拒绝，不覆盖。已有 docs/preview 历史结果保持原样。[交互 HTML](interactive-preview/report.html)、[实际截图](interactive-preview/report.png)、[输入](interactive-preview/input.json)与[冻结结果](interactive-preview/result.json)使用自编教学数据。

筛选支持价格、条件收益率、风险和当前条款，查找诊断名称；数值排序先按单位分组，不把收益率与价格混排，未知留空且排在已知值之后。顶端全价、现金流来源、条件收益率及未知状态不会因筛选消失。净价和实际应计息未提供。

情景仅选择核心已计算的基准及 ±100/200 bp 零息曲线平移结果，比较精确重估、久期/凸性近似和误差；JavaScript 不重新定价，不计算策略收益。没有任意冲击或含权模型。

另存按钮下载新 JSON，包含所选条件、可见诊断、所选情景、完整输入与冻结结果、输入/结果 SHA256、估值日、核心及交互方法版本。文件名含日期和下载时间；浏览器决定最终保存位置，不写回输入或历史报告。交互版本 frozen-selection-1；它描述展示选择，不是新的估值方法。缺值和条款 unknown 保留。

本机真实 Chromium 已验证类别筛选、数值排序、空选择、多情景比较和下载内容与 Python 核心一致，并截图检查。页面无外部库、字体文件或网络请求；原创交互代码按 MIT，第三方权利边界沿用[范围清单](../THIRD_PARTY_NOTICES.md)。
