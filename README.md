# 可转债现金流与条款研究

计算纯债现值和条件收益率，核对转股价与赎回、回售等条款。

[原创代码 MIT](LICENSE) · [发行说明](https://github.com/KILING-TASI/convertible-bond-engine/releases/tag/v0.12.10) · [运行检查](https://github.com/KILING-TASI/convertible-bond-engine/actions) · [English](README.en.md)

当前发布：**v0.12.10 · 普通发行版**。Python **3.10+**；基础功能只需 Python，无第三方运行依赖。

[快速开始](#快速开始) · [使用自己的资料](#使用自己的资料) · [能力与边界](#能力与边界) · [文档与维护](#文档与维护)

## 能解决什么问题

**这只转债的收益率怎么算？不同条款条件会怎样影响现金流？**

独立维护可转债现金流和条款计算；采集和资料组织可以使用其他工具，也可自行准备。

| 需要准备 | 会得到什么 |
|---|---|
| 债券现金流、价格、转股价、条款日期及明确的利率和税费假设。 | 纯债现值、条件收益率、敏感性及条款计数与证据缺口。 |

## 快速开始

1. 安装 Python 3.10 或以上版本。
2. 下载[完整源码 ZIP](https://github.com/KILING-TASI/convertible-bond-engine/releases/download/v0.12.10/convertible-bond-engine-v0.12.10-source.zip)并解压，进入包含 `try_demo.py` 的目录。
3. 在该目录打开终端，运行：

```console
python try_demo.py --no-open --out-dir reports/first-demo
```

按终端给出的路径打开 HTML。也可以在源码目录双击 `Start-Demo.cmd`（Windows），或运行 `sh Start-Demo.sh`（Linux/macOS）。教学使用原创模拟资料，不自动取得真实数据。

使用 Git 时，先运行 `git clone https://github.com/KILING-TASI/convertible-bond-engine.git`，再运行 `cd convertible-bond-engine`，随后执行上面的教学命令。重复运行请指定新目录，历史结果会保留。

[报告示例源码](docs/preview/report.html)：GitHub 会展示 HTML 源码，请下载完整源码后在浏览器中打开。

## 使用自己的资料

先按[资料准备与排错](BEGINNER.md)整理来源、日期、单位和必要字段，再按[使用说明](USAGE.md)选择对应入口。以下两种使用方式分别配置。

**命令行（CLI）**：在源码目录安装本仓，然后查看可用命令：

```console
python -m pip install .
convertible-bond-engine --help
```

可选组件按需要安装：`market`、`evidence`。例如 `python -m pip install ".[market]"`；依赖范围见 [使用说明](USAGE.md)。安装时下载构建工具或可选依赖可能需要联网。

**助手 Skill**：按 [SKILL.md](SKILL.md) 配置，保留完整目录及其引用资源。安装 CLI 不会自动注册 Skill，也不表示已在第三方技能市场上架。

| 身份 | 名称 |
|---|---|
| GitHub 仓库 / Python 发行包 | `convertible-bond-engine` |
| 主要命令 | `convertible-bond-engine` |
| SKILL.md 中的名称 | `convertible-bond-engine` |

本仓可单独使用。需要跨工具功能时，再按说明安装并明确配置对应工具的位置。

## 能力与边界

当前不是完整含权定价或发行人博弈模型；未知条款、行权和实际到账不能填成确定结果。

报告中的来源、日期、假设和未知事项需一起阅读。程序运行成功不等于来源已经认证、资料完整或投资判断有效。原创代码采用MIT，第三方代码、公告、研报和数据仍按各自权利范围处理。

## 文档与维护

- [详细命令与方法](USAGE.md)
- [资料准备与排错](BEGINNER.md)
- [Skill 调用指引](SKILL.md)
- [版本记录](CHANGELOG.md)
- [许可与第三方范围](THIRD_PARTY_NOTICES.md)
- [审计范围](AUDIT_SCOPE.md)

[贡献说明](CONTRIBUTING.md) · [安全反馈](SECURITY.md) · [更新与清理](LIFECYCLE.md)

[按问题选择其他工具](https://github.com/KILING-TASI/research-workbench/blob/main/references/tool-navigation.md)；资料契约校验已并入[数据仓](https://github.com/KILING-TASI/cn-data-adapters/blob/main/CONTRACT_MIGRATION.md)。默认分支的文档整理不改写已发布的源码包和历史结果；版本变化见 [CHANGELOG.md](CHANGELOG.md)。

## 公开底稿验收

[覆盖登记](PUBLIC_VALIDATION.json)区分公开事实、混合教学与尚缺样本。运行 `python tools/verify_public_validation.py --run-checks --output reports/public-validation-v1.json` 可核对冻结文本与已登记反例；重复运行使用新文件。通过不表示重新认证原文或真实市场效果，未取得的样本仍列为缺口。
