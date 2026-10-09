# 有界工作台可选桥接

状态：引擎侧接口与当前工作台脚本同输入对照已实现；主分支增量，未发新版。工作台侧可选入口由其任务负责，本地原生调用已完成端到端验收；入口已提交到待审PR #6（当前入口32e42b4，历史回执分别保存），不在此仓库替换或删除内置入口。教学联调不认证真实条款或数据。

## 显式接口

`from cbengine.bridge import calculate`，调用 `calculate(spec)`。无新依赖。输入schema_version为cb-fixed-cashflow-1，输出method_version为fixed-cashflow-bridge-1.0、risk_method_version为zero-parallel-1，保留引擎版本、输入SHA256、来源、估值日和净全价口径。

示例：[平坦输入](../examples/bridge-fixed-demo.json)、[非平坦输入](../examples/bridge-nonflat-demo.json)。只接受CNY每100面值，settlement_date=as_of，ACT/365F、annual_effective、zero_spot和included_in_rate显式声明。discount_curve为期限/年有效零息率节点；来源仍是调用者声明，不是曲线真实性认证。节点递增、期限覆盖全部未来现金流；拒绝外推。

price_basis为clean或dirty。净价需accrued_interest及来源；全价未提供应计息时，输出clean_price和accrued_interest为null，不猜算。cashflows逐项给日期、coupon、redemption、coupon_tax、redemption_tax和source；金额/税额显式，正的税前/税后现金流，未来严格递增。只支持100年内期限，不桥付息当日权利。

maturity_payment包含includes_final_coupon、quoted_amount和source。含末息报价需等于coupon+redemption；不含末息报价需等于redemption。Decimal字面核对拆分，拒绝把含息111.5再次作为redemption加1.5。字段缺失、不支持字段（包括退出场景）均拒绝。

独立隔离调用也可用 `python -m cbengine.bridge examples/bridge-fixed-demo.json --out-dir local-data/bridge-native-first-run`。新目录保存input.json/result.json，不覆盖；主机需使用已安装本项目或显式引擎路径的Python环境，不依赖工作台安装全部行情组件。

## 输出与等价范围

输出逐期gross/net/years/spot/pv、纯债现值、税前/税后年有效IRR、zero_curve_parallel_duration、discount_weighted_average_time、convexity_parallel、DV01及既有曲线冲击结果。旧完整L1接口保持原样；桥接不导出内部适配用占位正股价或转股价值，current_rights与actual_exit始终unknown。

工作台单一discountYield只有平坦年有效零息率时，才与此贴现/风险口径等价。cashFlows.year由同一日期ACT/365F换算；收益率小数与工作台yieldPct需除/乘100。工作台未提供显式税额诊断，税后对照只调用其现有yield_rate辅助函数，不能称原诊断已支持税额。

不等价：正式条款权利、真实退出、完整YTW、转股价值、非平坦曲线风险、真实应计息算法。非平坦不能强行压缩为单一YTM；工作台现有诊断没有贴现权重平均期限字段，单列not-provided，不伪造匹配。

## 实际联调记录

2026-10-09读取工作台本地工作树convertible_review.py，git HEAD 8ba3cb3f49aeba1d972b488cfa80468e8252c2e9；各记录另含具体文件SHA256，可能包含待审PR或未提交内容，不代表GitHub已发布版本。

- [平坦六项对照](bridge-acceptance/flat.json)：现值95.109397018574、税前IRR-0.011218746053、税后IRR-0.012654334702、曲线平移敏感度3.803671472959、凸性18.158070406715、DV01 0.036176490025。六项差均小于1e-8。
- [非平坦对照](bridge-acceptance/nonflat.json)：税前/税后IRR同输入匹配；现值和曲线风险标not-equivalent，不宣称全量匹配。
- [八个失败反例](bridge-acceptance/failures.json)：缺应计息、含息重复、税额缺失、曲线外推、连续复利、同日支付、退出字段及面值不符均拒绝。

可复跑，只读取用户明确指定的本地参考代码，不复制进本项目；需自行在PYTHONPATH提供已安装引擎或仓库根路径：

```sh
python scripts/compare_bridge_workbench.py /path/to/convertible_review.py --input examples/bridge-fixed-demo.json --out-dir local-data/bridge-first-run
```

输出目录必须新建，保存input.json/result.json。该联调是数学适配检查，不是合同、法律或真实数据认证。方法与原许可见[方法卡](FIXED_INCOME_METHOD_CARDS.md)和[第三方清单](../THIRD_PARTY_NOTICES.md)。


## 工作台入口端到端回执（另存，不覆盖旧记录）

2026-10-09实际执行当前工作台 `scripts/bounded_engine_gateway.py` 的 `run('convertible', project_dir, input_path, new_out_dir)`，使用独立子进程原生入口。工作台git HEAD为add664afe56e38d1ac681577289f9b282afc906d，引擎调用HEAD为2e8b293d0552e3ddb330fc4ce7f47bd2a3959570。工作树可能含尚未提交入口；回执另记gateway实际源码SHA256和引擎方法文件哈希，不以git HEAD单独认证工作树版本。

- [平坦原生回执](native-bridge-v1/flat-result.json)及[实际输入](native-bridge-v1/flat-input.json)：status=native-response-preserved，原生退出码0；engine_response与直接calculate逐字段相同。
- [非平坦原生回执](native-bridge-v1/nonflat-result.json)及[实际输入](native-bridge-v1/nonflat-input.json)：透传一致；这不是与工作台单一discountYield风险的等价认证。
- [缺税额拒绝回执](native-bridge-v1/missing-tax-result.json)及[实际输入](native-bridge-v1/missing-tax-input.json)：保留原生退出码2、status=blocked、engine_response=null及错误原因；没有升级为成功。

三组检查输入字节SHA、gateway源码SHA及bridge.py方法文件SHA。成功结果中的权利状态均保留unknown。汇总见[本地端到端验收](native-bridge-v1/summary.json)。旧bridge-acceptance数学对照和历史预览保持冻结。可使用对应工作台入口复跑：

```sh
python /path/to/research-workbench/scripts/bounded_engine_gateway.py convertible --project-dir /path/to/convertible-bond-engine --input /path/to/convertible-bond-engine/examples/bridge-fixed-demo.json --out-dir /path/to/new-result-directory
```

上述是本地可选桥接验收。工作台PR #6仍由该任务提交与审核，不在此仓库合并；没有发布新版本或完整模块迁移。这里只证明原生输入/响应透传与既有数学交集，不能证明合同、数据、账户或实际退出等价。


## 历史已提交入口联合回执（801f224）

此前未提交入口的回执保留为历史。本次按工作台PR #6最终提交801f22404785544a1c11e7930eee30e76fbdb21c重跑，可转债引擎调用提交b45460847c53f0d1bedb5729c15f1e20711652b1。确认工作台入口换行规范化后与该提交一致；实际加载文件字节SHA256为a2b80ecefaeaa33671c31dc2809f4c42c4739c21452117679e8bc564c4a252d3。PR状态仍OPEN，未合并、未发布。

[最终汇总](native-bridge-final-801f224/summary.json)保留三组独立调用与版本：

- [平坦](native-bridge-final-801f224/flat-result.json)、[非平坦](native-bridge-final-801f224/nonflat-result.json)：退出码0，原生响应与直接引擎调用逐字段一致，条款unknown保留。
- [缺税额](native-bridge-final-801f224/missing-tax-result.json)：退出码2、blocked、原生响应null，错误未提升为成功。

输入字节、gateway实际源码及bridge.py方法文件SHA均核对。仅确认可转债原生桥和此前已证数学交集，不为北交所、组合或规则引擎验收签字；非平坦透传成功仍不代表与内置单一YTM风险等价。旧回执与冻结输入未覆盖。


## 后续入口源码更新后的可转债回执

工作台提交32e42b41a33688a47decd2540d823ff475b19b44更新了入口文件的规则报告展示，实际gateway字节SHA256为38123e66d683441a226987ab00ed6c25941615d222eee3f6769f871302c14945。本次对该已提交文件重新执行可转债三组原生调用，不把前次a2b摘要当作本次源码。调用时引擎HEAD为11f66796631376f0a3ed63308131b2cb02b046e7；桥接算法未在本批修改。

[新汇总](native-bridge-final-32e42b4/summary.json)：[平坦](native-bridge-final-32e42b4/flat-result.json)、[非平坦](native-bridge-final-32e42b4/nonflat-result.json)逐字段等于直接引擎响应，权利unknown保留；[缺税额](native-bridge-final-32e42b4/missing-tax-result.json)继续blocked、退出码2、响应null。输入、方法文件及入口实际字节SHA均核对。PR #6仍OPEN。

旧native-bridge-final-801f224及a2b摘要只代表当时源码，保持历史冻结。此批仅确认更新入口下的可转债透传与失败保留，不对规则报告、其他引擎、合同权利或真实数据签字；不合并、不发新版。
