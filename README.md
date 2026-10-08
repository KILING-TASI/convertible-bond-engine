# 可转债定价与博弈引擎

独立实现的 A 股可转债研究工具。v0.2 提供 **L1 现金流与条款诊断、快照筛选和持仓汇总**，支持单债和批量 JSON 输入，不依赖行情账户或作者本地环境。

## 快速开始

需要 Python 3.10+，计算核心无第三方运行依赖。

```sh
python -m pip install .
cb-engine examples/demo.json --out local-data/result.json
python -m unittest discover -s tests -v
```

也可直接运行 `python -m cbengine.cli examples/demo.json`。示例全部是教学假设，不是实际证券行情。批量诊断将输入改为对象列表；任一输入无效时整批拒绝输出。

## 批量筛选与持仓汇总

```sh
cb-engine examples/portfolio.json --mode screen --max-price 110 --max-premium 0.30 --min-net-ytm 0 --exclude-call-risk
cb-engine examples/portfolio.json --mode portfolio --out local-data/portfolio.json
```

批量输入必须非空、代码唯一、估值日一致。筛选结果保留入选诊断与每只未入选的原因，阈值包含等号；收益率与溢价率参数均为小数。强赎过滤排除状态未知及满足条件且无有效不强赎承诺的债券，不能排除所有未来风险。

持仓汇总增加 `quantity`，表示每张面值100元的持有张数，要求大于零。按数量累加现金价值和债底；组合溢价按总市值与总平价/债底之比计算，不平均个券溢价。DV01只汇总纯债部分，集中度用市值权重的平方和倒数表示。

条款返回 `status`：inactive、condition_met、condition_not_met 或 unknown。历史不足且计数未达到门槛，或者末条历史不是估值日时，状态为unknown、`trigger_condition_met`为null。观测日是否为交易日及中间缺漏仍需上游核对；估值日在休市日且仅提供上一交易日数据时，本版保守标记unknown。

## 已实现

- 按实际付息日计算纯债现值：ACT/365F、年复利零息曲线、逐期限线性插值，拒绝曲线外推。
- 税前/税后 YTM，显式退出场景的条件 YTP/YTC，以及已提供场景最小收益率。
- 转股价值、纯债和转股溢价率、到债底距离。
- 曲线平行变动的修正久期、DV01、凸性，±100/200bp 精确重估及近似误差。
- 强赎、下修、回售共用滚动计数；每条历史记录采用当日有效转股价；显式生效区间和重置日期。
- 不强赎承诺日期展示与来源要求，强赎条件提示。
- 基于使用者提供的适用下限测算下修下限及对应平价。
- 输入来源保留、异常拒绝、教学与缺口警示；持续集成测试。
- 快照筛选及排除原因、持仓总值、组合溢价、纯债DV01和集中度。

## 输入口径

完整字段见 [examples/demo.json](examples/demo.json)。所有金额按每100元面值；`dirty_price` 是全价，调用者须核对报价口径并转换。所有利率使用小数，如 `0.045`。

`cashflows` 的每期 `coupon` 与 `redemption` **必须互不重复**。若到期兑付110已经包含末期息1.5，填 coupon=1.5、redemption=108.5；若110不含末期息，填 coupon=1.5、redemption=110。`redemption_tax` 是显式税额，不能默认把全部溢价视为应税或免税。示例零税额仅为教学假设。`coupon_tax_rate` 由调用者根据身份与实际结算确定。

`discount_curve` 必须是包含信用因素的零息贴现曲线；市场到期收益率曲线不能未经转换冒充零息曲线。每个现金流期限必须在节点范围内。

条款三项键 `call`、`put`、`reset` 必须全部提供；确认不存在的条款填 null。其他条款必须明确来源、窗口、门槛、方向、滚动、生效日期及 `reset_on` 列表。不存在统一默认条款。`observations` 必须按日期递增，每行填写当日正股价和有效转股价。日历完整性及停牌处理需要上游核验，本版不自行补缺。

`exit_scenarios` 可提供 `call` 和 `put`，每项包含 date、gross_payment、net_payment、source。退出日现金流须完整包含当日票息或应计息，避免遗漏/重复。这些是**条件现金收益率**，并非预测、并非自动转股后收益。未提供全部适用场景时，不称为完整 YTW。

`reset_floor_inputs.applicable_floors` 仅填写该债募集说明书实际适用的下限，净资产下限不是本引擎对所有转债的统一假设。

## 与原设计的差异

原方案是长期蓝图，不是当前功能承诺。首版没有含权理论价、OAS、BS Greeks、隐含波动率、评级迁移、Merton PD、LSM、交易回测、自动公告解析、实时数据或交易执行。债底只是给定曲线与兑付假设下的现金流现值，不是信用或流动性保护承诺。

修正了几个建模口径：

1. 滚动窗口满后每天移出最旧记录，不能解释为固定窗口倒计时后归零。`days_to_fill_window` 仅表示尚缺多少历史记录。
2. 强赎条件满足不等于发行人已公告执行；投资者可能转股。未来含权模型需处理通知期及可执行动作，不能全部按100元结束路径。
3. 历史条款判断使用历史有效转股价，不能用当前转股价重算全历史。
4. 曲线下久期/凸性使用逐期导数；二阶近似有截断误差，±100bp误差超过固定阈值不自动判定为实现错误。
5. 深度虚值 Delta 不保证在任意波动率和期限下都小于固定阈值；强赎退出也不天然等同于损失。
6. 原方案整数年现金流0.3/0.5/1.0/111.5在4.5%贴现下的精确债底为95.12083273，显示为95.12，原95.13测试值应修正。日期版还应计入闰年造成的ACT/365F差异。

## 后续路线

见 [ROADMAP.md](ROADMAP.md)。先补可信数据和历史事件，再做含权模型及样本外回测。每个模型独立标注假设、版本和验证结果。

## 参考与许可

本仓库独立编写，未复制外部项目代码或上传用户原始设计文件。相关研究参考：[sw1507/convertibleBond](https://github.com/sw1507/convertibleBond)、[QuantLib](https://github.com/lballabio/QuantLib)、[AKShare](https://github.com/akfamily/akshare)。它们的许可不因本仓库 MIT 许可而改变。外部数据使用权由各提供方决定。

仅用于研究；结果依赖输入与假设，不执行交易。
