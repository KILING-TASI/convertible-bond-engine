# 固定现金流外部交叉验证：设计与首批验收

## 已有与首批新增

既有L1已计算现金流现值、ACT/365F、线性零息节点插值及平行利率DV01/久期/凸性。v0.10复用diagnose输出，不替换这些实现；添加固定现金流与QuantLib的可选小型对照。贴现输入新增显式discount_curve_kind=zero_spot及discount_compounding=annual_effective校验；旧输入仍兼容，但标记口径假设，不能认证其来源是零息率。

首批仅CNY、每100面值、估值日等于结算日、明确未来税前现金流、ACT/365F和年有效复利的平坦零息率。信用口径须声明included_in_rate或risk_free_only，禁止再额外重复扣减违约损失。净价=全价-所声明应计息；应计息目前不是独立票息日历计算结果。到期收益率曲线、其他日计数/复利或结算日不对齐则拒绝此次对照。

## 可复现接口

```sh
python -m cbengine.crosscheck examples/crosscheck-flat.json --out local-data/local-check.json
# 可选：在独立验证环境中安装QuantLib==1.43，不是本项目运行依赖
python -m cbengine.crosscheck examples/crosscheck-flat.json --quantlib --out local-data/external-check.json
```

没有请求外部库时external.status=not-run；缺库明确报错，不能记为外部验证通过。请求后比较全价、净价及修正久期；价格或久期差超过1e-8返回mismatch及退出码3。输入摘要、版本、口径、适配器和差值留存。对照使用SimpleCashFlow、FlatForward、CashFlows.npv及duration，避免默认票息日历改变现金流。QuantLib 1.43的InterestRate版duration适配采用五参数接口。

## 实际验收与差异解释

2026-10-09本地独立验证环境实际运行QuantLib 1.43。例子估值日2026-10-09，2027/2028/2029/2030年10月9日现金流0.3/0.5/1/111.5，年有效零息率4.5%，零应计息为教学声明。

两边全价约95.109397018574，修正久期约3.803671472959；价格绝对差约2.84e-14、久期绝对差约4.44e-16，低于1e-8。非真实债价或信用曲线，匹配不证明市场数据正确。

整数年贴现的95.12083273与本例不同：ACT/365F跨2028闰年，部分现金流期限多1/365年，不能把差额误认作实现错误。相同4.5%数值若直接作为连续复利率，也与4.5%年有效复利不同；需先用log(1+r)转换。输出保留这两个刻意未对齐的控制反例，不作为替代估值。

## 外部许可与接口复核

- [QuantLib许可](https://github.com/lballabio/QuantLib/blob/master/LICENSE.TXT)：BSD风格，包含保留版权/许可及不背书条件。本项目未复制其实现，不随包分发其二进制；可选接口使用不改变外部组件自身许可。
- [FinancePy许可](https://github.com/domokane/FinancePy/blob/master/LICENSE)：GPL-3.0。只核对许可和公开接口，不复制、导入或分发其代码，不增加其依赖；**本批未运行FinancePy数值对照**。
- [FinancePy债券接口](https://github.com/domokane/FinancePy/blob/master/financepy/products/bonds/bond.py)：核对clean_price_from_discount_curve、dirty_price_from_discount_curve、accrued_interest、modified_duration及key_rate_durations_zero_tent。其YTM久期与基于零息曲线的节点冲击不是同一口径，不能直接比标签。后续若增加隔离对照须先制定许可与分发方案并对齐日历、频率及曲线复利。

这些是成熟参考，不沿用“零竞争”调研结论；并不意味着任意外部模型无需扩展即可覆盖中国转债。

## 仍未闭环与后续

1. 实际净价/全价与应计息：补完整票息起止、结算日与经核实的舍入规则；当前仍是显式输入。
2. 真实曲线：报价种类、历史时间、信用成分、贴现因子/即期率转换与bootstrap；本批仅夯实类型和复利校验，没有完成真实曲线构建。
3. 非平坦插值：对齐年度/连续零息率和对数贴现因子的插值差异，先逐现金流比DF，再比较价格。
4. 停牌计数：保留v0.9的显式缺口与暂停计数，不新增未经官方/个案核验的排除或滚动约定。
5. 关键利率久期：在现金流与曲线基准稳定后增加节点冲击，与现有平行DV01核对，不重写基础风险度量。
6. 含权/OAS/博弈：后置。此次固定现金流对照不包含中国滚动强赎窗口、下修、承诺、重置及发行人裁量，不能据其通过称含权模型已验证。


## v0.11 节点与付息日对照

新增crosscheck-nonflat.json：各现金流日期与年有效零息节点重合，利率2%、3%、4%、5%。全价93.373343151721；QuantLib 1.43价格差0，曲线平移敏感度差约1.50e-10。只认证节点处，不认证跨节点插值。非平坦风险为全部零息率平行变动的敏感度，不是单一YTM修正久期。

crosscheck-payment-boundary.json显式包含估值日2元现金流，全价95.373343151721；价格差0，敏感度差约1.47e-10。同日支付是否属于持有人须另查实际结算权利。两例净价均减输入声明的2元应计息；这不是独立的应计息算法验证。


## 主分支风险命名补强

schema_version=2、method_version=fixed-cashflow-crosscheck-2.0新增明确口径，旧键兼容保留。zero_curve_parallel_duration是零息曲线平移敏感度；discount_weighted_average_time是指定曲线下的支付期限加权平均，不把非平坦情景标为YTM久期。单一YTM久期在元信息中明确not-calculated。方法、非平坦反例和付息前后验收见[方法卡](FIXED_INCOME_METHOD_CARDS.md)。历史结果不回写。
