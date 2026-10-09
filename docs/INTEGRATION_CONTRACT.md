# 独立引擎接入契约草案 1.0

状态：历史迁移契约草案；现已另实现[有界可选桥接](BOUNDED_WORKBENCH_BRIDGE.md)及当前工作台脚本同输入对照。工作台侧入口已有本地原生调用端到端回执，入口已提交到待审PR #6，最终提交回执另存，仍不宣称完整模块迁移。原CLI保持兼容。宿主应保存engine_version、schema_version=cb-integration-1.0、method_version、输入摘要、来源及as_of；未知状态不能转成安全结论。

|模块|输入/输出口径|方法版本|
|---|---|---|
|现金流|date、每100面值gross/net amount、CNY、source；ACT/365F，不猜税率|dated-cashflow-1|
|净价/全价|dirty=clean+accrued；accrued及依据必须显式，缺失不反推|declared-accrual-1|
|曲线|年有效零息率、期限递增、线性插值、禁止外推；不能用YTM曲线冒充|zero-annual-1|
|收益率|显式现金流和全价求年有效IRR；输出小数，展示百分数另乘100|cashflow-irr-1|
|风险|零息率平移DV01；非平坦曲线不等于YTM久期|zero-parallel-1|
|条款|观察数量与正式权利状态分离；unknown、缺口、依据和生效日保留|evidence-clause-1|

旧workbench的cashFlows.year须由同一估值日和实际支付日按ACT/365F生成，不能直接以1、2、3年替代。flat discountYield可映射平坦年有效零息率；非平坦不能压缩成单一收益率。其yieldPct为百分数，需要除100。minimumSuppliedScenarioYieldPct只在输入情景间取最小，不是完整最差收益率。rolling_clause的above/below默认含等号，而独立引擎遵循具体条款严格/含等号口径，不直接移植。旧输入自声明tradingDaysComplete不等于正式证据认证。

`scripts/compare_workbench.py`只读取用户指定的本地参考脚本，记录文件SHA256，用同一日期换算现金流比较现值、平坦修正久期、DV01。参考文件不复制、没有运行时依赖。它是本地已安装脚本对照，不代表GitHub research-workbench主分支；缺失参考文件则无法验证。条款及含权模型不在此对照范围。
