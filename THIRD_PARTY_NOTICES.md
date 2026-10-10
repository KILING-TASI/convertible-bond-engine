# 许可范围与第三方材料

核对日期：2026-10-10。根据仓库所有者授权，根 LICENSE 补充 `Copyright (c) 2026 KILING-TASI`，保留原有 `Copyright (c) 2026 convertible-bond-engine contributors`。MIT 正文及第三方原许可不变；授权范围仍限原创代码和有权授权的原创说明。

## 范围清单

| 材料 | 范围与处理 |
| --- | --- |
| cbengine/*.py、scripts/*.py、tests/*.py | 本项目独立编写的实现，按根 MIT 许可；未发现外部实现复制，检查不等于穷尽权利认证 |
| 原创说明及教学示例 | 有权授权的原创表达、教学输入和生成的教学报告按 MIT；引用原文、第三方标记与来源材料除外 |
| docs/preview/ 与 docs/interactive-preview/ 的 report.png、report.html、input.json、result.json | 自编教学数据、原创 HTML；真实浏览器渲染，无第三方行情、公告全文或账户资料；不附字体文件 |
| examples/terms-113042.json、notice-review-113042.json | 原创核验结构含公告事实、短摘录、来源链接、页码及哈希；原公告及摘录不整体授予 MIT，未取得原文再分发授权；仓库没有附 PDF 全文 |
| cbengine/data/market_rules.json、docs/rule-corrections.json | 独立重写的事实整理、检查逻辑及来源链接；没有上传规则包代码或 Skill 指令。引用规则和原材料的权利不因整理改变 |
| 东方财富、集思录、巨潮等来源 | 数据及原文适用各提供方权利与服务条款；MIT 不授予抓取、商业使用或再分发权，来源链接不是授权证明 |
| 本地 local-data 档案和缓存 | Git 忽略且不打包；使用者自行审查文件、数据和原文分享权利 |

本清单不是所有数据或资料的权利认证。第三方内容未被本项目重新授权；如后续引入实现或材料，须先记录来源和适用许可，再决定分发范围。

## 可选依赖和参考

| 组件 | 上游许可 / 本项目使用范围 |
| --- | --- |
| [AKShare](https://github.com/akfamily/akshare/blob/main/LICENSE) | MIT；可选 market 依赖，接口调用，不复制实现；组件许可不包含行情授权 |
| [pypdf](https://github.com/py-pdf/pypdf/blob/main/LICENSE) | BSD-3-Clause；可选 evidence 依赖，用于本地 PDF 文本读取 |
| [requests](https://github.com/psf/requests/blob/main/LICENSE) | Apache-2.0；公告分页联网调用所用外部组件，通常由 market 依赖环境提供 |
| [QuantLib](https://github.com/lballabio/QuantLib/blob/master/LICENSE.TXT) | 上游 BSD 风格许可；独立可选数值对照，不随本项目包分发实现或二进制 |
| [FinancePy](https://github.com/domokane/FinancePy/blob/master/LICENSE) | GPL-3.0；仅核对许可和公开接口，未复制、导入、执行或分发代码，没有该运行依赖 |
| [research-workbench](https://github.com/KILING-TASI/research-workbench) | 参考工作流思路；同输入比较读取用户指定的本地脚本，不将其代码打包或改变其许可 |
| [Playwright](https://github.com/microsoft/playwright/blob/main/LICENSE) | Apache-2.0；仅本地截图制作工具，不是项目运行依赖或包内组件 |

外部组件及其传递依赖仍按各自安装版本的原许可、NOTICE 与版权要求使用；本仓库不重新授权，也不随包捆绑这些实现。许可证目录仅保留 AKShare、pypdf、requests 和 QuantLib 的上游许可文本，不表示外部代码已经包含。来源提交和文本 SHA256 见[许可来源记录](licenses/sources.json)；安装版本的许可证可能不同，分发安装环境须另外核对。

## 发布包

包元信息 MIT 指向原创代码的许可。LICENSE、此清单及第三方许可原文随 wheel 和源码包保存；必要说明、示例和规则资源一并收录。真实 PDF、账户数据、原始设计、上传 ZIP、网络缓存与外部库二进制不随包分发。

本轮新增研究复查、报告说明及合成教学为作者原创MIT；同作者随包通用I/O代码独立保留，不要求其他仓库安装。规则有限事实和来源链接不改变原文权利；未捆绑实际公告/研报PDF或私人账户资料。
