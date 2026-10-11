# 可转债现金流与条款研究

计算纯债现值和条件收益率，核对转股价与赎回、回售等条款。

[![原创代码 MIT](https://img.shields.io/badge/原创代码-MIT-green)](LICENSE) · [当前发行版 v0.12.7](https://github.com/KILING-TASI/convertible-bond-engine/releases/tag/v0.12.7) · [运行检查](https://github.com/KILING-TASI/convertible-bond-engine/actions)

## 能解决什么问题

**这只转债的收益率怎么算？不同条款条件会怎样影响现金流？**

独立维护可转债现金流和条款计算；采集和资料组织可以使用其他工具，也可自行准备。

## 快速开始

从[发行页](https://github.com/KILING-TASI/convertible-bond-engine/releases/tag/v0.12.7)下载完整源码并解压，需要 Python 3.10 或以上。在源码目录执行：

```text
python try_demo.py --no-open --out-dir reports/first-demo
```

按提示打开新生成的 HTML。Windows 也可双击 `Start-Demo.cmd`，Linux/macOS 可用 `sh Start-Demo.sh`。教学使用原创模拟资料，不自动取真实数据；重复运行使用新目录，历史结果保留。

[查看已保存的报告示例](docs/preview/report.html)。HTML请随完整源码下载后打开；示例按自身生成日期和口径阅读。

## 使用自己的资料

先按[资料准备](BEGINNER.md)填写输入，再看[详细命令与方法](USAGE.md)。需要安装CLI时，在自己的Python环境运行：

```text
python -m pip install .
convertible-bond-engine --help
```

仓库、Python发行包、安装命令及Skill注册名均为 `convertible-bond-engine`。CLI安装和Skill注册是两个步骤：自然语言调用按[SKILL.md](SKILL.md)配置，保留完整资源；不必安装全部仓库。安装普通构建依赖可能联网，教学流程不需要作者缓存。

## 结果范围

当前不是完整含权定价或发行人博弈模型；未知条款、行权和实际到账不能填成确定结果。

报告中的来源、日期、假设和未知事项需一起阅读。程序运行成功不等于来源已经认证、资料完整或投资判断有效。原创代码采用MIT，第三方代码、公告、研报和数据仍按各自权利范围处理。

## 文档与维护

- [详细命令与方法](USAGE.md)
- [资料准备与排错](BEGINNER.md)
- [Skill调用指引](SKILL.md)
- [版本记录](CHANGELOG.md)
- [许可与第三方范围](THIRD_PARTY_NOTICES.md)
- [审计范围](AUDIT_SCOPE.md)

[贡献说明](CONTRIBUTING.md) · [安全反馈](SECURITY.md) · [更新与清理](LIFECYCLE.md) · [English](README.en.md)

[按问题选择其他工具](https://github.com/KILING-TASI/research-workbench/blob/main/references/tool-navigation.md)。共12个活跃仓，另有1个供旧记录复查的[历史契约仓](https://github.com/KILING-TASI/cn-research-contracts)。各仓分别发布；main的后续文档整理不改写旧发行包和冻结结果。
