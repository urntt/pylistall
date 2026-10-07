# 开发指南

[English](development.md)

本文说明本地环境准备和行为测试。用户用法见
[README.zh-CN.md](../README.zh-CN.md)，agent 指导见 [AGENTS.md](../AGENTS.md)。

## 本地环境

请使用 [pyproject.toml](../pyproject.toml) 中 `requires-python` 支持的 Python 版本。
实现通过使用不带 `slots` 选项的 dataclass，保留声明的 Python 3.9 兼容性。
验证版本支持时，应同时在声明的最低版本和当前开发解释器上运行测试。

在仓库根目录创建独立环境：

```sh
python -m venv .venv
```

Windows PowerShell 可以直接调用环境中的解释器，无需激活环境或调整执行策略：

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
```

macOS 或 Linux：

```sh
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest
```

可编辑安装会使用当前工作树。`dev` 可选依赖安装 pytest，普通用户安装不会
增加测试依赖。依赖锁定和自动化 CI 留待后续的开发流程步骤建立。

## 测试边界

测试位于 `tests/`，通过独立临时目录覆盖文件筛选、二进制包含优先级、UTF-8
识别、读取限制、目录树、CLI 输出与错误、Git 日志分组以及剪贴板后端选择。

CLI 测试捕获剪贴板调用；后端测试模拟外部程序和 pyperclip；Git 分组测试
替换日志读取过程。因此测试不会更改真实剪贴板，也不需要桌面剪贴板软件。
后端模拟验证命令选择与编码，不能替代真实操作系统上的集成验证。

测试描述预期的可观察行为，包括现有的“目录树反映真实文件系统，独立于内容
过滤规则”的设计。只有输出格式本身需要验证的小型示例才使用完整输出断言。

## 回归覆盖

初始基线发现的三个缺陷已经修复。对应的临时 `xfail` 标记已移除，测试现在
按普通测试通过：

- 重复与逗号分隔的 `-i` 复用其他过滤选项使用的模式规范化逻辑，包括清理
  空白和空条目。
- 默认忽略规则覆盖根层级的工具文件。根层级变体从现有默认规则派生；
  自定义模式的匹配方式与目录树行为保持原有约定。
- UTF-8 采样使用严格的增量解码，通过多读取一个字节判断尾部半个字符来自
  采样截断还是文件本身不完整。采样大小仍有限制，采样内部的无效字节仍会
  进入二进制启发式判断。

目前没有已知缺陷使用 `xfail`。继续启用 `xfail_strict`，确保将来的临时标记
在缺陷修复时必须移除。新增回归应正常失败，并修复其根因。
