# 单仓非editable安装验收

日期：2026-10-10。状态：当前待审源码579febe的实际本地目录/进程/虚拟环境隔离通过；不是新OS、容器或物理无其他仓。宿主仍保留其他项目，它们没有复制到隔离目录或安装到该虚拟环境。完整本地回执保存在work验收目录，公开[结果与命令](STANDALONE_ACCEPTANCE.json)仅将隔离路径前缀做占位替换。

## 提供物与环境

通过git archive导出单仓源码ZIP，排除.git、local-data、作者work输出及PDF。构建普通wheel，不使用editable安装。新的独立venv未启用system_site_packages；只安装本仓wheel，未安装其他自家仓库，计算核心没有第三方运行依赖。第三方构建依赖按pyproject声明安装，wheel和源码归档摘要在回执中。

子进程清除PYTHONPATH/PYTHONHOME和RESEARCH_WORKBENCH路径变量、作者组件/数据路径；为该子进程设置空HOME/用户配置与缓存目录，不改系统HOME/CODEX_HOME，不删除真实缓存。sys.path及模块origin完整记录；cbengine从该venv/site-packages加载，标准库仍来自宿主Python，不能将其称全新系统。venv中的pip等安装工具版本记录，不借用作者专业包。

## 最短流程与实际结果

在隔离运行目录使用venv Python，输入只取已安装wheel自带share/convertible-bond-engine/examples/demo.json：

```sh
python -m pip install --no-deps --no-cache-dir /path/to/convertible_bond_engine-0.11.0-py3-none-any.whl
python -m cbengine.preview /path/to/venv/share/convertible-bond-engine/examples/demo.json --out-dir /path/to/new-run/preview
```

实际生成input.json/result.json/report.html，全价118.50、纯债现值95.10939701857427、税前条件年化收益率-0.011218746052657966（小数），当前条款unknown，教学标识和软件0.11.0正确。HTML的本地输入/结果链接存在。LICENSE、README、免责声明和第三方清单在安装包中可得。没有作者现金流数据或其他专业库参与。

附加验证已有原生桥可独立运行，并生成结果；固定现金流核心对照不带QuantLib时输出not-run。三项可选库akshare/pypdf/QuantLib实际均未安装。

失败例：同一输出目录二次调用退出码2且原结果摘要未变；显式请求QuantLib外部对照退出码2而不是通过。未联网采集，也不把教学结果认证为真实证券或投资有效性。

## 可复跑与远端证据

仓库提供[scripts/verify_standalone.py](../scripts/verify_standalone.py)，从提供的wheel创建新venv，并从安装包资源执行上述流程，保存模块来源/依赖/完整命令回执：

```sh
python scripts/verify_standalone.py --wheel /path/to/package.whl --work-dir /path/to/new-isolated-directory
```

CI新增isolated-wheel-demo：只checkout本仓库，构建wheel，另建venv并从安装包资源跑最短流程，验收结果作为CI artifact保存。本批远端[运行37972409567](https://github.com/KILING-TASI/convertible-bond-engine/actions/runs/37972409567)已通过，[原回执摘要](STANDALONE_CI_ACCEPTANCE.json)保留模块来源、包摘要、依赖及命令；测试提交pin为9b6f175，后续只补验收记录。它不安装工作台或其他自家库。

## 版本与未验收范围

- 本轮实际待审源码pin=579febe；新增验收脚本/文档随后提交，数学实现没有改变，CI会验新提交构建的wheel。
- main与PR、已发布v0.11.0不同。旧Release没有本轮预览/桥新增入口；本批未单独构建和运行旧Release，不称其安装验收通过，不替换标签/资产。
- 当前批未做浏览器视觉、自然语言发现或Skill安装；本仓是Python包，不宣称Skill独立安装。已有截图的历史视觉检查不升级成本批隔离视觉。
- 真实联网数据、可选行情/PDF组件安装、全市场覆盖及含权模型未验收。

本批以单仓wheel核心独立运行、真实期望结果、模块来源及必要失败例的验收结案；不新增模型、采集器或安装到用户现有环境。许可与数据权利边界保持。
