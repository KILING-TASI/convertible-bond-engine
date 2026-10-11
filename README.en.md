# Convertible bond cash-flow and term review

Review declared cash flows, yields, curve sensitivity and clause evidence. This is not a complete option-adjusted convertible pricing or trading engine.

[中文说明](README.md) · [Release v0.12.9](https://github.com/KILING-TASI/convertible-bond-engine/releases/tag/v0.12.9) · [Skill instructions](SKILL.md) · [Input preparation](BEGINNER.md)

Current release: **regular release**. Python **3.10+**. Base runtime dependencies: none. Optional extras: `market`, `evidence`. See [USAGE.md](USAGE.md) for scope.

## First run

Download the [complete source ZIP](https://github.com/KILING-TASI/convertible-bond-engine/releases/download/v0.12.9/convertible-bond-engine-v0.12.9-source.zip), extract it and enter the directory containing `try_demo.py`:

```console
python try_demo.py --no-open --out-dir reports/first-demo
```

Alternatively, clone `https://github.com/KILING-TASI/convertible-bond-engine.git`, run `cd convertible-bond-engine`, then execute the command above. Open the report at the path printed by the command. Teaching data is synthetic; use a new output directory and keep prior reports.

## CLI and Skill

From the source directory:

```console
python -m pip install .
convertible-bond-engine --help
```

Repository and distribution: `convertible-bond-engine`. Primary CLI: `convertible-bond-engine`. Skill name in SKILL.md: `convertible-bond-engine`. Installing the CLI does not register the Skill; configure the complete resources in an assistant that supports local Skills. Build or optional dependencies may require network access during installation.

## Scope and rights

Read the [Chinese capability boundaries](README.md#能力与边界) and [detailed commands](USAGE.md). Each tool can run independently; cross-tool calls need explicit configuration. Successful execution does not authenticate source documents, fill missing data or establish investment validity. No trade execution or guaranteed returns.

Original code uses MIT. Third-party code and documents/data retain their own licenses and rights. Default-branch documentation edits do not rewrite released archives or frozen results.

[Changes](CHANGELOG.md) · [Third-party rights](THIRD_PARTY_NOTICES.md) · [Contribution](CONTRIBUTING.md) · [Security](SECURITY.md)
