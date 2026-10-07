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
├── VISION*.md                 产品方向
├── docs/                      双语开发与架构文档
├── src/pylistall/              CLI、目录树、筛选、Git 日志、剪贴板
├── tests/                     行为与回归测试
├── scripts/check.py           检查组织入口
├── pyproject.toml             元数据、依赖、构建与检查配置
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

第二条命令会替换剪贴板；验证收集输出时使用可丢弃的样例目录。
`-p` 也需要剪贴板。对不熟悉的目录进行测试前，阅读
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

这会临时改变项目 `.venv` 的解释器。当前 74 项测试覆盖筛选、二进制优先级、
UTF-8 边界、读取上限、目录树、CLI 输出与错误、Git 分组和剪贴板后端选择。
测试使用临时目录，模拟剪贴板程序、pyperclip 和 Git 日志获取，
不会修改真实剪贴板，也不依赖桌面会话。后端模拟验证命令及编码，不等于真实 OS 集成。

基线修复包括统一包含模式规范化、根层级及嵌套层级的默认排除、
增量 UTF-8 采样和兼容 Python 3.9 的 dataclass。
当前没有使用 `xfail` 的已知缺陷测试。保留严格的预期失败处理；
临时标记须有原因与移除计划，新增回归必须正常失败。

## 构建与验证发行包

构建后端保持 setuptools。在仓库根目录执行：

```sh
uv build
uv run --locked python -m twine check dist/*
```

`uv build` 在 `dist/` 中生成 wheel 和源码包，默认从源码包构建 wheel。
验证时使用新的输出目录，例如 `uv build --out-dir dist/verify-1`，
并只检查其中的包，避免混入旧版本。版本来自 `pyproject.toml`，验证无需升级版本。
隔离构建依赖遵循 `[build-system].requires`，与项目依赖锁分开。

在独立环境中安装生成的 wheel；将下面的 `0.3.0` 替换为正在验证的版本：

```sh
uv venv .pytest_cache/wheel-smoke
uv pip install --python .pytest_cache/wheel-smoke dist/pylistall-0.3.0-py3-none-any.whl
```

PowerShell：

```powershell
.\.pytest_cache\wheel-smoke\Scripts\pylistall.exe --help
```

macOS 或 Linux：

```sh
.pytest_cache/wheel-smoke/bin/pylistall --help
```

这验证了没有可编辑项目安装时的入口。完整仓库验收需要在独立的新克隆目录、
没有现有 `.venv` 的情况下，重复环境同步、帮助、统一检查、构建、元数据检查和
wheel 安装。在可丢弃的克隆目录中也检查最低 Python 的兼容性。

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

## 完成标准与发布门槛

本地完成要求：相关双语文档与链接正确、锁文件最新、统一检查通过、差异仅包含预期修改。
Python 兼容性修改必须通过最低与默认版本。打包修改还须通过新检出仓库的环境准备、
帮助、wheel 和源码包构建、Twine 元数据检查及隔离 wheel 安装。
明确实际验证范围，不把剪贴板模拟测试描述成真实平台验证。

发布前要求上述检查通过，并有明确版本决策、匹配的发行元数据以及一致的发行说明和标签。
审查要发布的具体文件，确保不混入旧包。CI 和自动发布属于后续工作，
当前本地检查不代表已经建立。版本升级、远程推送、发布标签和上传是单独授权的任务。
