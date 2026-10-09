# 公告目录覆盖证据 v1

使用 `python -m cbengine.coverage input.json --out audit.json`。输入要求issuer_code、bond_code、bond_name、org_id、identity_source、start、end；最长366日，最多20页，每页30条。记录请求区间、时间、逐页原始响应及摘要、数量、失败页和候选公告。失败返回partial和退出码3。

使用 `cb-engine snapshot.json --directory-audit audit.json --out result.json` 接入。原始响应摘要与合并记录不一致时拒绝。

2026-10-09实际查询上银发行人601229，org_id=9900010207，区间2026-01-01至2026-10-09，返回69条（30/30/9），标题筛选11条转债候选。pagination_observed只指本次查询记录分页一致；legal_event_coverage仍unknown，conversion_history_complete仍false。它不证明全部条款公告、首次公开时间、原文真实性或停牌规则。

即使输入自行声明交易日与调价历史完整，条款计数也只作条件观察，正式状态保持unknown。需要真实日历、调价链及原文证据才能进一步认证。
