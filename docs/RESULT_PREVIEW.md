# 教学结果预览

状态：主分支演示，使用 0.11.0 计算核心；预览入口尚未进入 v0.11.0 发布标签。

## 生成

仓库根目录：

```sh
python -m pip install .
python -m cbengine.preview examples/demo.json --out-dir local-data/preview-first-run
```

Python 3.10+，无额外运行依赖。目录已存在返回退出码 2，不覆盖。输出 input.json、result.json、report.html；HTML 为本地自包含页面，无外部字体或脚本。

提交的[报告](preview/report.html)来自同一命令，输出改为 `docs/preview`。[输入](preview/input.json)复用仓库自编教学样本；[结果](preview/result.json)记录版本、输入 SHA256、估值日、L1 诊断及未知的事件链。没有第三方行情、账户资料或公告全文。

## 案例与限制

输入全价 118.50 元；0.3/0.5/1/111.5 元税前现金流按实际支付日贴现，4.5% 年有效平坦教学曲线得到 95.109397 元纯债现值。ACT/365F 跨闰年，不能直接替代成整数年。税前到期 IRR 约 -1.121875%，只是假设现金流的条件收益率。

教学强赎计数 14/15 只描述提供的观察序列。事件链没有完整公告证据，正式强赎、下修、回售及当前转股价均 unknown。预览不把 L1 的观察条件状态当作法律权利，也不推断无风险。

本页面不执行外部库对照；已验证范围见[交叉验证说明](EXTERNAL_CROSSCHECK.md)。实际应计息、跨节点非平坦插值、真实信用曲线、停牌计数及完整含权模型仍不在此演示范围。

## 实际截图

[report.png](preview/report.png)由本机 Chromium 浏览器渲染提交的 HTML 后截取，视口 1280×1120、缩放 1；截图经过视觉检查。画面保留教学标识、引擎版本和估值日。截图不是 AI 生成；后续改输入或报告应重新渲染并检查。
