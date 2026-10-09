# 可转债定价与博弈引擎

独立实现的 A 股可转债研究工具。v0.7 提供 **L1诊断、市场快照、公告时间线、PDF字段匹配、证据归档、质量检查及结构化规则参考**。离线核心不依赖行情账户；代码查询及PDF核验分别按需启用依赖。

## 纠错后的结构化规则

```sh
python -m cbengine.rules examples/rule-context-demo.json --out local-data/rules.json
cb-engine examples/demo.json --rule-context examples/rule-context-demo.json
cb-engine local-data/verified.json --rule-context examples/rule-context-113042.json --quality-as-of 2026-10-09 --format html --out local-data/rule-card.html
```

参考用户提供的cn-market-rules-v0.1.0整理14项纠错登记，见[纠错清单](docs/rule-corrections.json)。包内[规则文件](cbengine/data/market_rules.json)有14条记录，明确官方参考、公司专属条款、研究政策和待核事项，并保留来源、核对日期、生效时间及适用范围。只包含重写的事实整理和检查逻辑，没有安装上传包的Skill或导入其指令。

纠正股票印花税参数、沪深IPO资格与单位、创业板普通转股权限及退市整理例外、北交所920身份识别；撤销未转股比例等于损失等错误推论。未核实的历史案例、临停与转股时段、交易单位和费用细节保持待核，不进入自动决策。

`--rule-context`只用于单债诊断，须提供同一代码与截止日、明确市场SSE/SZSE/BSE、板块main/star/chinext/bse及阶段ordinary/delisting_period。创业板权限须显式声明，缺失不当作已具备。市场不能由代码前缀猜测。示例金额均为教学算例，不是用户实际持仓或建议。

IPO参考区分1万元参与门槛和每5000元市值/500股单位；提供当期网上上限及来源时才计算给定上限下的数量。股票税额仅算减半印花税，不含其他费用和券商舍入。公司强赎/下修/回售没有通用默认阈值，只返回证据需求。信用筛选阈值不是监管规则。

截止日不能晚于核对日2026-10-09；未确证历史生效日保留null并只支持核对日参考。已知生效日期也不证明拥有当时冻结的资料。部分官方正文访问超时，相关记录明确标为官方索引摘录核对，不是全文核验。未来使用须重新核对来源并升级参考库。

L1条款新增`inclusive`布尔值：above/below方向分别对应严格大于/小于；inclusive=true改为大于等于/小于等于。示例输入已显式填写。旧输入暂保留含等号行为并输出legacy-inclusive-assumption警示，须根据原文补参数。不会用通用参考库覆盖逐只条款。

## 实际PDF核验与版本归档

```sh
python -m pip install ".[evidence]"
cb-engine local-data/notices.json --terms examples/terms-113042.json --terms-pdf /path/to/prospectus.pdf --notice-reviews examples/notice-review-113042.json --notice-pdf /path/to/adjustment.pdf --quality-as-of 2026-10-09 --store local-data/evidence --out local-data/verified.json
python -m cbengine.archive local-data/evidence --code 113042
```

需自行取得与样本哈希一致的实际原文，仓库不分发PDF。`--terms-pdf`和`--notice-pdf`分别读取本地原文，核对实际SHA256、前8页主体/标题、明确页码上的唯一摘录及字面数值。正文PDF目前一次只支持一份核对底稿。不安装PDF依赖仍可使用核心诊断及底稿声明；无法读取原生文本的扫描件需要人工复核，不自动OCR。

底稿的`verification_checks`逐项指定field、page、excerpt、mode及number_token。数字核验匹配字面数值；文本核验匹配字面字符串。不把“含息”或“无普通回售”等人工语义判断自动提升为机器核验。每个匹配结果绑定完整底稿摘要，字段更改后不能继续使用旧匹配记录。日期规范化、单位换算、主体与证券代码映射、来源下载真实性及完整法律解释仍需单独核对。

`--store`在用户选择的独立目录下按代码追加版本，保存快照摘要、前版本摘要及引用PDF副本。重复内容不追加；已有记录或PDF修改、版本缺失和并发写入会拒绝继续。核验标记绑定的实际PDF必须提供或已存于同一档案。归档使用锁及临时文件落盘，不写入包目录。版本摘要只用于检测内容一致性，没有外部签名或时间戳，不能称为不可篡改，也不认证源数据真实。只供本地使用，分享前自行检查原文许可。

2026-10-09实文件验收：读取上银转债原始募集说明书，匹配面值100、末期票息字面4.00、含息兑付比例字面112；读取2026-06-02调整公告，匹配转股价8.57与8.35。归档保存两份实际PDF，并通过离线版本链与文件摘要检查。其余未列出的条款、生效日期的语义解释和未读公告不因此升级为机器核验。

## 行情质量检查

所有市场快照输出会附`data_quality`：分别列出可得性、新鲜度、溢价率复算一致性及原始条款PDF检查记录。`--quality-as-of YYYY-MM-DD`指定评估截止日；默认北京时间今日。`--max-lag-days 3`指定允许的日历天滞后，范围0至366。重放旧快照不会悄悄刷新网络。

行情时点未知保持unknown；超出允许滞后标stale；行情或快照取得日期晚于截止日标future。缺报价/平价、溢价率复算不一致都会单列。满足带日期展示策略不代表可用于现金流定价、含权估值、回测或完整交易日判断。本版不重新请求接口作体检，也不承诺数据源在线状态。

输入JSON拒绝重复键、NaN/Infinity和浮点溢出，避免条款或现金流参数被静默覆盖。

## 后续公告候选与正文核对底稿

```sh
cb-engine --code 113042 --announcements --start-date 2026-01-01 --end-date 2026-10-09 --out local-data/notices.json
cb-engine local-data/notices.json --notice-reviews examples/notice-review-113042.json --format html --out local-data/reviewed-notices.html
```

代码和日期是验收示例，不代表当前仍存续或任何投资结论。`--announcements`是显式联网查询；已有快照无发行人映射时可指定`--issuer-code 601229`，已有映射时必须一致。缺少参数的旧快照不会猜发行人身份。默认从快照获取日回溯180日，最大区间366日，结束日不晚于快照获取日。

查询巨潮全部类别发行人公告，再以标题中的转债名称、代码或转债相关词筛选；元数据保留公告日、链接、候选分类和身份匹配程度。泛称“可转债”的标题可能对应其他券。查询失败、未找到候选、正文未核对是不同状态；均不能推断无风险。标题分类只发现线索，不激活强赎、回售或不赎回承诺，也不改转股价。

`--notice-reviews`附加人工正文核对底稿，要求对应已发现链接、同一转债代码和公告日，明确原文来源、核对日期、事件类型与生效日。标记依赖调用者声明，不是自动法律鉴定。转股价调整需给出旧价、新价及生效日；底稿不会自动改变定价输入。公告日与生效日分开，尚未附底稿的公告仍是候选。

2026-10-09真实查询验收：601229发行人在2026-01-01至2026-10-09区间返回69条元数据，其中11条标题含转债相关词。另人工阅读[转股价调整原文](https://static.cninfo.com.cn/finalpage/2026-06-02/1225343748.PDF)第1至2页，核对113042从8.57调整至8.35，公告日2026-06-02、生效日2026-06-08。此底稿不代表其余10份公告正文已核对。查询可能包含历史行情日之后的公告，不能直接作为历史行情日的回测信息集；元数据也不能证明当日具体公开时刻。

## 输入代码生成中文资料卡

```sh
python -m pip install ".[market]"
cb-engine --code 113042 --out local-data/snapshot.json
cb-engine local-data/snapshot.json --format markdown --out local-data/report.md
cb-engine local-data/snapshot.json --format html --out local-data/report.html
```

`--code` 显式联网查询东方财富比价表；失败或关键字段不全时，降级到东方财富单债历史估值接口。另尝试取得集思录强赎信息和东方财富单债条款转录。代码只是调用示例，不代表该债仍存续。单接口最多等待30秒；最多四个接口合计约120秒。获取时间使用北京时间，但不是报价时间。查询不自动更新历史输入，不自动覆写现金流，也不将行情报价当作已核实全价。

状态 `partial` 表示资料卡仅展示可得字段；债底、YTM、条款判断缺证据时不计算。东方财富纯债价值列为第三方估值；集思录强赎状态列为第三方信息，不冒充原文核验。即时及历史接口都失败时保存 `failed` 记录并返回退出码3；本地输入错误返回2。快照可离线重放，提供JSON底稿及Markdown/HTML卡片。

2026-10-09真实联网验收：比价表连接被远端关闭；历史估值、单债详情及集思录强赎接口均取得数据。113042（上银转债）最新有效历史收盘日期为2026-10-08，报价117.925、第三方转股价值117.4850299401。此为当次成功验收，不保证长期可用或所有代码覆盖。

历史快照选择不晚于获取日的最新完整行，价格和平价来自同一行；拒绝最新日期重复，不用较新但缺价格的行。`quote_age_calendar_days`表示日历天，不是交易日滞后。降级后不将详情中的当前正股价/转股价拼到历史行。其他第三方条款和强赎字段自身时点仍未知，与历史行情应分开理解。

示例卡片可离线运行：

```sh
cb-engine examples/market-demo.json --format html --out local-data/demo-card.html
```

市场快照不能直接用于原L1批量筛选或持仓定价：它缺少已核实现金流与条款。完整定价仍使用原有输入契约。

## 原始募集说明书证据

```sh
cb-engine local-data/snapshot.json --terms examples/terms-113042.json --format html --out local-data/reviewed-card.html
```

`--terms`附加明确的人工核对底稿，要求代码匹配、来源、PDF页码、核对日期和范围，检查末期利息是否包含在到期兑付总额中。它是调用者提供的证据声明，不是自动PDF解析或真实性鉴定。原始条款与当前有效状态分开。

113042样本已经人工阅读[原始募集说明书](https://static.cninfo.com.cn/finalpage/2021-01-21/1209154427.PDF)第19、23、24页：六期票息为0.3/0.8/1.5/2.8/3.5/4元；到期总兑付112元包含末期4元利息，现金流组件应是4+108，而非4+112。兑付在期满后五个交易日内，具体日须查兑付公告。其回售是募集资金用途变更后的特别回售，没有普通低价回售。证据文件保存原PDF的SHA256，不分发完整原文件。未完成全量后续公告核验，不能据此生成当前触发状态、确定日期YTM或完整含权价。

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

v0.6证据和质量流程参考[research-workbench](https://github.com/KILING-TASI/research-workbench)的实际文件核验、版本化知识卡、数据源质量分层与严格JSON理念；本包独立实现这些小型组件，没有导入该仓库的研究工作流依赖。

仅用于研究；结果依赖输入与假设，不执行交易。

## 免责声明

本项目仅供学习与研究，不构成投资建议或交易指令，不保证收益或结果准确性。请在使用前阅读[免责声明与使用边界](DISCLAIMER.md)，并结合本次数据来源、假设与缺口独立判断。代码许可不包含第三方数据使用授权。
