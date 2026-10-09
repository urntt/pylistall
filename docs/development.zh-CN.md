# 开发指南

[English](development.md)

本文是开发者与 agent 的贡献流程。先阅读 [AGENTS.md](../AGENTS.md)、
[愿景](../VISION.zh-CN.md)和相关[架构章节](architecture.zh-CN.md)。
用户安装与选项说明放在 [README](../README.zh-CN.md)。

## 仓库结构

```text
pylistall/
├── AGENTS.md / CLAUDE.md       agent 规则 / 导入这些规则
├── README*.md                 用户指南
├── CHANGELOG*.md              双语版本变更
├── VISION*.md                 产品方向
├── docs/                      双语开发与架构文档
├── .github/                   CI 工作流与双语 pull request 模板
├── src/pylistall/              CLI、模式、共享遍历、输出、进度、目的地、Git、剪贴板
├── tests/                     行为与回归测试
├── scripts/                   统一检查、CI 矩阵与 wheel 冒烟验证
├── pyproject.toml             元数据、依赖、构建与检查配置
├── MANIFEST.in                源码包包含的贡献资源
├── uv.lock                    解析后的运行与开发依赖
└── .python-version            默认开发解释器
```

## 环境准备

按[官方安装说明](https://docs.astral.sh/uv/getting-started/installation/)安装 uv，
不要把 uv 本身安装到项目虚拟环境中。本流程使用 uv 0.12.23 验证。
从新检出的仓库开始，PowerShell、macOS 和 Linux 使用相同命令：

```sh
uv sync --locked
uv run --locked python --version
uv run --locked pylistall --help
```

uv 创建 `.venv`，以可编辑方式安装项目，并包含 `dev` 开发依赖组。
无需激活环境或手工用 pip 安装依赖；本地缺少解释器时，uv 可以下载。

[.python-version](../.python-version) 将默认开发解释器固定为 Python 3.14.3。
包的支持范围仍由 [pyproject.toml](../pyproject.toml) 中的 `requires-python` 定义，
当前为 Python 3.9 及以上。语法和标准库 API 都必须兼容该范围。

此前尚未发布的 `dev` extra 已迁移到 `[dependency-groups].dev`，
包含 pytest、Ruff 和 Twine，不再作为安装 extra 暴露。
普通用户继续使用 pip，开发工具不会成为运行依赖。`uv.lock` 记录版本及
Python、平台条件下的解析结果；`--locked` 会拒绝过时锁文件，不会静默更新。

## 运行与检查修改

通过锁定环境运行 CLI：

```sh
uv run --locked pylistall --help
uv run --locked pylistall . -r -o -i "*.py"
```

第二条命令展示收集输出，不修改剪贴板；手动验证使用可丢弃的样例目录。
只有 `-c` 需要剪贴板。对不熟悉的目录进行测试前，阅读
[架构中的当前限制](architecture.zh-CN.md#安全边界与当前限制)。

必须使用的统一检查入口：

```sh
uv run --locked python scripts/check.py
```

它依次使用当前 Python 解释器执行 Ruff 规则检查、Ruff 格式检查和 pytest，
首个失败即停止并返回非零状态。脚本自行定位仓库根目录，配置保存在 `pyproject.toml`。
Ruff 目标语法为 Python 3.9，行宽为 88，启用 `E4`、`E7`、`E9`、`F`、`I`，
包含导入排序。

有意应用格式与导入修复后，重新运行统一入口：

```sh
uv run --locked ruff check . --fix
uv run --locked ruff format .
uv run --locked python scripts/check.py
```

检查 Python 兼容性时，在最低支持版本上运行同一入口，再恢复默认环境：

```sh
uv run --locked --python 3.9 python scripts/check.py
uv sync --locked
```

这会临时改变项目 `.venv` 的解释器。CLI 行为基线测试覆盖筛选、名称筛选与二进制权限、
UTF-8 边界、读取上限、目录树、CLI 输出与错误、Git 分组和剪贴板后端选择。
测试使用临时目录，模拟剪贴板程序、pyperclip 和 Git 日志获取，
不会修改真实剪贴板，也不依赖桌面会话。后端模拟验证命令及编码，不等于真实 OS 集成。
输出测试覆盖精确 UTF-8 预算、禁用收集器、dry-run、文件碰撞、别名、失败清理及
原文件保留；可丢弃的真实 Git 仓库验证 Unicode 日志传输。
展示测试覆盖字面量路径、导入回退、TTY 分流、分页选择、平台编码及关闭管道。
手动集成在真实终端使用短、长临时样例，检查颜色、Unicode、短输出自动退出、空格、
`/`、`q`、`-n` 与 Markdown 重定向；模拟测试不能替代终端检查。Rich 运行依赖用于
语法展示，复用已锁定版本，维护锁文件时保留其他解析版本。
发布测试还覆盖混杂发行包、元数据不一致、缺失说明、错误标签及远端哈希改变时的拒绝行为，
不依赖网络上传。

基线修复包括统一包含模式规范化、根层级及嵌套层级的默认排除、
增量 UTF-8 采样和兼容 Python 3.9 的 dataclass。
当前没有使用 `xfail` 的已知缺陷测试。保留严格的预期失败处理；
临时标记须有原因与移除计划，新增回归必须正常失败。

### 收集与终端验收

回归覆盖名称视图、真实目录剪枝、根目录豁免、Git 独立性、链接目标祖先排除、
全部 disable 组合、动态名称定界符及 Base64 原始前缀。通过扫描／采样调用记录证明
没有为进度重复读取；精确预算覆盖编码说明和截断标记。计数分别验证 Files 条目、
已检查与实际收集；取消覆盖 Git、进度和安全写入清理。

在真实 Windows 终端用临时样例进行人工验收：

1. 准备含深层目录、中文及 emoji 名称、较长路径、空文件和大文件的可丢弃目录。
2. 运行 `uv run --locked pylistall SAMPLE -r -o -n`，观察扫描转圈、文件计数、路径裁剪，
   确认没有错误百分比、Rich 标记解释或状态覆盖正文。
3. 将 stdout 重定向为文件，确认 stderr 仍有进度、Markdown 没有 ANSI；
   重定向 stderr 确认进度关闭。分别检查 `-P` 与 `-n` 独立。
4. 检查 `-D`、文件导出和取消后的清理，保留剪贴板模拟。
5. 在 less 中检查短输出自动退出、长输出翻页／搜索／`q`，确认进度先清理。
   Ctrl+C 应返回 130，无 traceback，覆盖写入保留原文件。

PR 分开记录自动检查和人工界面结果。沙箱无法创建链接时在允许的环境重跑；
不要把 PTY 或模拟输出等同于全部真实终端验收，未验证项目应明确列出。

## 构建与验证发行包

遍历测试在临时目录创建真实链接，包括 Windows junction。符号链接测试仅在 Windows
缺少创建链接权限时跳过；覆盖根外目标、祖先循环、重复别名、断链、排除一致性及
嵌套目录枚举失败，不读取用户的其他项目。

构建后端保持 setuptools。在仓库根目录执行：

```sh
uv build
uv run --locked python -m twine check dist/*
uv run --locked python scripts/smoke_wheel.py
```

`uv build` 在 `dist/` 中生成 wheel 和源码包，默认从源码包构建 wheel。
验证时使用新的输出目录，例如 `uv build --out-dir dist/verify-1`，
并只检查其中的包，避免混入旧版本。版本来自 `pyproject.toml`，验证无需升级版本。
隔离构建依赖遵循 `[build-system].requires`，与项目依赖锁分开。
`MANIFEST.in` 将贡献文档、锁文件、脚本与工作流定义包含进源码包，
使其中的发布测试保留所需文件。

[wheel 冒烟验证](../scripts/smoke_wheel.py) 要求目录中恰有一个 wheel 和一个源码包。
它在 `.pytest_cache` 内建立临时环境，安装 wheel，确认导入来自该环境，
将发行元数据与开发环境安装结果比较，并运行已安装 CLI 的帮助；结束后删除临时环境。
单独构建目录可作为参数传入：
`uv run --locked python scripts/smoke_wheel.py dist/verify-1`。

完整仓库验收需要在独立的新克隆目录、没有现有 `.venv` 的情况下，
重复环境同步、帮助、统一检查、构建、元数据检查和 wheel 安装。
在可丢弃的克隆目录中也检查最低 Python 的兼容性。

### 元数据与徽章

项目使用 SPDX 许可证表达式并明确包含 `LICENSE`；setuptools 的最低版本
支持在 Python 3.9 上生成该元数据格式。运行依赖和 Python 支持范围仍在
`pyproject.toml` 中定义，开发依赖组不会成为 wheel 的 extra。

Python classifiers 列出 CI 覆盖的边界版本，当前为 3.9 和 3.14，
不能替代 `requires-python`。Shields 的 PyPI Python 版本徽章读取已发布包的
classifiers，不读取 `Requires-Python` 或当前仓库。元数据修改需要发布新版本并
等待缓存刷新后才会反映到徽章；发布时验证其显示结果，再恢复到 README。

## 锁文件维护

有意修改 `pyproject.toml` 中的依赖后：

```sh
uv lock
uv sync --locked
uv run --locked python scripts/check.py
```

一并审查和提交 `pyproject.toml` 与 `uv.lock`。
有意升级单个包时使用 `uv lock --upgrade-package pytest`；
只有全部依赖更新都在任务范围内时才使用 `uv lock --upgrade`。
也要检查最低 Python 对应的条件版本。`uv lock --check` 可验证锁文件是否最新，
不会接受变更。不要手工修改解析条目，也不要用 `--frozen` 替代 `--locked`
来绕过配置与锁文件不一致的问题。

## 贡献流程

1. 复现问题或明确预期行为；修改实现前阅读相关测试和权威文档。
2. 按 [Git 规则](../AGENTS.md#git-与提交)建立体现目的的分支，
   保留已有历史、作者设置和无关的用户改动。
3. 完成聚焦的修改，需要时增加有意义的行为覆盖；相关中英文文档在同一变更中更新。
   配置留在权威文件内，其他位置用链接引用。
4. 审查 `git diff`，运行统一检查，说明测试解释器、平台范围和限制，
   使用英文 Conventional Commits 提交。
5. 推送已获授权的分支，使用[模板](../.github/pull_request_template.md)创建 pull request。
   审查完整差异，最新版本的 `CI` 检查通过后才能合并。开发者与 agent 使用同样的检查，
   本地通过不能替代 GitHub 上的结果。

## 持续集成

[CI 工作流](../.github/workflows/ci.yml) 在推送、pull request 和手动触发时运行。
Actions 固定到提交 SHA，uv 固定到已验证的工具版本；任务从新检出的仓库开始，
使用 `uv sync --locked` 同步环境。

[矩阵脚本](../scripts/ci_matrix.py) 从已安装的项目元数据读取最低 Python，
从 `.python-version` 读取默认解释器。两个版本分别在 Windows、Linux 和 macOS
运行 CLI 帮助及统一检查。Python 支持约束的形式改变时，同步修改解析脚本。
测试通过模拟验证平台命令，不等于验证真实桌面剪贴板。

六项检查全部通过后，两个 Python 版本的 Linux 打包任务分别构建 wheel 和源码包，
运行 Twine 及隔离 wheel 冒烟验证，并将发行包保留七天，不上传到 PyPI。
最终 `CI` 任务在任一必要任务失败、取消或跳过时失败，为分支保护提供稳定的检查名称。

`main` 要求通过 pull request 合并，且分支相对 `main` 为最新、`CI` 通过，
管理员也遵守这些要求。单维护者仓库不要求额外审查者批准。
只审查和合并已验证的版本；分支有新修改或更新了 `main` 后，等待新的 CI 结果。

## 完成标准与发布门槛

本地完成要求：相关双语文档与链接正确、锁文件最新、统一检查通过、差异仅包含预期修改。
Python 兼容性修改必须通过最低与默认版本。打包修改还须通过新检出仓库的环境准备、
帮助、wheel 和源码包构建、Twine 元数据检查及隔离 wheel 安装。
明确实际验证范围，不把剪贴板模拟测试描述成真实平台验证。

发布前要求上述检查通过，并有明确版本决策、匹配的发行元数据以及一致的发行说明和标签。
审查要发布的具体文件，确保不混入旧包；最新版本还必须通过 CI。
[发布指南](releasing.zh-CN.md) 规定服务配置、标签准备、TestPyPI 验证、正式批准与失败处理。
版本升级、远程推送、发布标签和上传是单独授权的任务。
