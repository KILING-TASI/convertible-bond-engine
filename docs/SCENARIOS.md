# 教学情景实例验收

主分支之外的待审增量，未发新版。只把已有有意义测试/样本整合为短CLI入口，补一年现金流手算锚点和真实CLI/报告回执，不新增定价模型或真实数据采集。

```sh
python -m pip install .
python -m cbengine.scenarios --example-dir examples --out-dir local-data/scenarios-first-run
```

Python3.10+、核心标准库，无其他自家仓依赖。打开新目录index.html；每个场景保存input.json、必要analysis.json、receipt.json（预期/实际/错误/输入摘要/方法版本），正常场景另有原生结果。目录已存在拒绝，不覆盖旧文件。条件计数案例生成已有HTML资料卡，页面不重新定价。

| 场景 | 依据与改变判断的检查 |
| --- | --- |
| 净价98+应计息2／全价100 | 一年税前105、税后104，独立手算IRR5%/4%，4%曲线PV=105/1.04；净全价等价 |
| 全价但应计息未知 | 净价/应计息保持null，不猜算 |
| 净价缺应计息 | 退出码2，无伪造结果 |
| 含末息105再填redemption105 | 与coupon5重复，拒绝 |
| 非平坦节点 | 复用已有QuantLib1.43历史同口径基准93.373343151721、曲线敏感度3.784982084554；本入口不执行外部库，not-run不算外部通过 |
| 付息前／当日包含／当日排除／次日 | 复用原平坦算例；当日包含-排除=2，DV01不变；前/后满足一日年有效贴现/滚动恒等式 |
| 条件达到、无执行公告及缺完整调价链 | 第一天12<10×1.3，第二天12≥8×1.3；1/1条件达标，但trigger=null、正式状态unknown，事件链权利全unknown |
| 缺交易日 | 不补价，退出码2，无结果 |
| 重复输出 | 二次运行退出码2，第一次结果摘要不变 |

复用来源：tests/test_bridge.py、test_crosscheck.py、test_analysis.py与[方法卡](FIXED_INCOME_METHOD_CARDS.md)。共12个CLI代表场景，另有输出拒绝及四个支付联合恒等式，不为凑数量重复测试。教学标识在汇总与每个回执中保留，不等同公开真实样本覆盖。

本批实际本地CLI运行通过；[公开汇总](SCENARIO_ACCEPTANCE.json)不发布原始PDF/私有资料。完整新输出位于任务outputs/scenario-acceptance-20261010（最初版本）及scenario-acceptance-final-20261010（补分析输入关联后），旧输出不改。CI复用isolated-wheel-demo，从该次新venv已安装wheel的包内examples运行全部场景；模块来源仍核对为venv，不依赖作者缓存。

未覆盖：真实调价链/合同合法性、真实交易日历/停牌政策、联网行情、全面外部组件矩阵、含权/概率/LSM、视觉新验收。既有历史截图不算本批视觉验收，资料卡生成成功也不等于视觉通过。原软件0.11.0版本不升，场景方法cli-scenario-acceptance-1表示验收入口，定价方法沿用各原生结果。任务以这些代表情景、独立包运行与失败保留结案，不新增大平台。
