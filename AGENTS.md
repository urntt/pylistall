# AGENTS.md

`CLAUDE.md` 文件会导入此文件，因此请将所有 agent 指导信息保存在此处。

## 项目简介

pylistall 是一个跨平台命令行工具，用于收集指定目录下的文件内容，并以结构化格式复制到系统剪贴板。

它还会输出绝对路径和树状目录结构。如果目录包含 .git 仓库，还可以选择附加 Git 提交日志。

该工具适用于高效地与 AI 工具共享项目上下文，以及用于调试、文档编写或代码审查。

## 项目决策

### 结构

### 平台

- Python 支持范围以 `pyproject.toml` 的 `requires-python` 为准；标准库 API 必须兼容声明的最低版本，支持范围调整时同步更新文档和测试。
  Python support is defined by `requires-python` in `pyproject.toml`; standard-library APIs must work on the declared minimum version, and support changes must update documentation and tests together.

### 安全

### 发布

### 行为

### 依赖

### 开发

### 测试

- 测试位于 `tests/`，开发环境与运行命令见 [开发指南](docs/development.zh-CN.md)。
  Tests live in `tests/`; see the [development guide](docs/development.md) for setup and commands.
- 测试使用临时目录并模拟剪贴板调用，避免修改真实剪贴板或依赖桌面环境。
  Tests use temporary directories and mock clipboard calls to avoid modifying the real clipboard or requiring a desktop session.
- 已知缺陷的 `xfail` 必须说明原因并有移除计划；修复时在同一变更中移除标记和更新文档。
  Known-defect `xfail` markers must have a reason and removal plan; remove them and update documentation in the same change as the fix.
- 不为新增回归添加预期失败标记来绕过测试。
  Do not mark new regressions as expected failures to bypass tests.

## 文档

- `README.md`：面向用户的项目概览、使用入口、版本发布与许可证说明。
- `VISION.md`：产品方向、需求、架构原则与长期决策。
- `docs/development.md`：面向开发者的环境准备、启动、构建、测试与仓库结构。
- `docs/architecture.md`：模块边界、安全模型与数据流。
- 将面向开发者和面向用户的文档分开。每份文档明确读者与职责，不把构建、测试或内部实现细节混入用户使用说明。
- 维护权威文档的单一来源；其他文档通过链接引用，不复制需要独立维护的规范。
- 代码变更影响已记录的行为、API、架构、配置、工作流程或用法时，在同一变更中更新相关文档。
- Markdown 围栏代码块必须注明语言标识；纯文本示意或目录结构使用 `text`。

## 开发原则

- 修复根因，而非仅处理症状。实施永久修复前先诊断底层原因；必要的立即缓解措施应明确为临时方案，并继续完成根因修复。
- 对预期随环境、部署或产品需求变化的值，优先采用配置驱动设计。避免无法解释或重复的魔法值；具名常量更适合作为明确来源时，不为其引入多余配置。
- 数据、状态、配置、业务逻辑和权威文档保持单一事实来源，并明确归属与维护责任，避免重复维护同一信息。
- 没有明确的迁移与移除计划时，不并行维护旧实现与替代实现；需要过渡时，先明确迁移步骤及旧实现移除计划。

### Git 与提交

- 所有操作代表用户进行。不要更改或覆盖已有 Git author 或 committer 身份；任务中新建提交确实需要配置身份且尚未配置时，使用姓名 `urntt`、邮箱 `urntts@gmail.com`。
- 未经用户明确要求，不改写已有提交的作者归属。
- 提交消息与 pull request 描述不得添加 `Co-Authored-By` trailer 或会话链接。
- 使用分支时，采用体现变更目的的类别前缀，例如 `feat/`、`fix/`、`refactor/`、`docs/`、`test/`、`chore/`。
- 提交消息遵循 [Conventional Commits](https://www.conventionalcommits.org/)，使用英文，格式为 `<type>(<scope>): <subject>`；subject 首字母小写且末尾不加句号。

## Agents 协作

- 与用户交流、解释、进度和计划使用中文；代码、注释、docstring、分支名和提交消息使用英文，仓库文档、README 与面向用户的交付物提供中英双语。
- 不要过于依赖记忆和本地环境，要尽量保证从 Github 克隆下来的仓库可以直接以和现在一致的方式继续开发或操作。
