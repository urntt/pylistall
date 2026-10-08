# 发布指南

[English](releasing.md)

本文面向准备发布的维护者与 agent。贡献环境及检查见[开发指南](development.zh-CN.md)，
用户安装见 [README](../README.zh-CN.md)。每种语言的发布内容分别以
[CHANGELOG.md](../CHANGELOG.md) 和 [CHANGELOG.zh-CN.md](../CHANGELOG.zh-CN.md)
为权威来源，工作流提取对应版本章节生成 GitHub Release。

## 一次性服务配置

PyPI 和 TestPyPI 使用独立账号与发布者配置，不把 API token、密码或恢复码放进仓库。
工作流采用 [Trusted Publishing](https://docs.pypi.org/trusted-publishers/using-a-publisher/)，
通过 GitHub OIDC 身份获取短期凭据。

在 `urntt/pylistall` 配置以下 GitHub environments，两者仅允许从 `main` 部署。
`pypi` 要求维护者 `urntt` 批准；单维护者仓库允许维护者审查自己的部署，
禁止管理员绕过。TestPyPI 无需额外批准，让正式发布决策发生在演练验证之后。

| 服务 | 项目 | 仓库所有者 | 仓库 | 工作流文件名 | Environment |
| --- | --- | --- | --- | --- | --- |
| TestPyPI | `pylistall` | `urntt` | `pylistall` | `release.yml` | `testpypi` |
| PyPI | `pylistall` | `urntt` | `pylistall` | `release.yml` | `pypi` |

已有 PyPI 项目在 **Your projects → Manage → Publishing**
[添加发布者](https://docs.pypi.org/trusted-publishers/adding-a-publisher/)。
TestPyPI 尚无项目时，在 **Your account → Publishing** 注册
[pending publisher](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/)，
项目名称使用上表的值；首次上传成功后建立项目。工作流文件名填写 `release.yml`，
不带 `.github/workflows/`。所有值必须准确匹配，登录与注册可能需要账号所有者操作。

上传前确认两个 environments 和两个发布者都已配置。
只有工作流文件不代表服务权限已建立或上传已成功；TestPyPI 验证通过前保留正式发布批准。

## 准备版本

1. 从最新 `main` 建立体现目的的分支，遵守[贡献流程](development.zh-CN.md#贡献流程)。
2. 选择新的稳定版本 `X.Y.Z`。修复现有行为使用补丁版，功能与兼容性改变需要明确版本决策。
   已发布文件名不能复用。修改 `pyproject.toml` 的 `project.version`，运行 `uv lock`，
   不更新无关依赖版本。
3. 两份更新记录各添加恰好一个有实际内容的 `## [X.Y.Z]` 章节，保持翻译等价。
   标题记录准备发布的内容，实际发布以 GitHub Releases 为准；同步更新受影响的双语文档。
4. 最低与默认 Python 均运行统一检查；按[发行包验证](development.zh-CN.md#构建与验证发行包)
   在新检出仓库中验证锁定环境和两种发行包。
5. 审查差异及发行元数据，创建 PR，最新 `CI` 通过后合并。
   版本、说明与标签必须对应同一版本的源码。

发布准备 PR 合并后才创建带说明的标签：

```sh
git switch main
git pull --ff-only
git tag -a vX.Y.Z -m "release vX.Y.Z"
git push origin vX.Y.Z
```

将 `X.Y.Z` 替换为选定版本，保留已有标签与作者设置。
推送标签会运行 CI，不会上传包或创建 GitHub Release。

## 验证与发布

在 **Actions → Release → Run workflow** 中选择 `main` 分支，输入准确标签，
先不勾选 `publish` 运行验证。[发布工作流](../.github/workflows/release.yml)
支持稳定的 `vX.Y.Z` 标签；拒绝其他分支触发、版本不匹配、不在 `main` 历史中的标签、
缺失更新说明、混杂的发行包及不一致的元数据。

工作流为该标签调用现有 CI，包含三平台六组检查和两个打包任务。
取同一次 CI 中默认 Python 已验证的两个发行包，检查两种归档与已安装项目的元数据，
记录 SHA-256 和源码提交。后续发布任务不会重新构建；发行包和双语说明保留 30 天。

准备开始实际演练与发布时，再勾选 `publish` 运行：

1. CI 与发行验证全部通过后，才能开始上传。
2. 独立 OIDC 任务将准确的两个包上传 TestPyPI。
3. 核对远端文件名与 SHA-256，下载两种包，在隔离环境安装下载的 wheel，
   验证元数据和导入位置，再运行 CLI 帮助。运行依赖从普通 PyPI 解析，不混合多个索引。
4. `pypi` environment 等待维护者审查 TestPyPI 结果、源码标签、清单与发布说明；
   批准部署后，同一组字节上传到 PyPI。
5. PyPI 通过相同的哈希与安装验证后，独立任务才从更新记录创建 GitHub Release，
   并附加 wheel 与源码包。

上传任务拥有 OIDC 权限，不检出或执行项目代码；构建和检查任务仅有仓库读取权限。
只有最终 GitHub Release 任务能写仓库内容，普通推送与 PR 不发布。

## 失败处理与发布后验证

各阶段依赖前一阶段成功。检查失败、缺少发布者配置、哈希不匹配或安装失败都会停止晋级。
正式部署被拒绝或未批准时，不会上传 PyPI。索引 JSON 可见性短暂重试，哈希不符立即失败。

索引上传不是原子事务，失败可能留下一个已上传文件。重试前检查索引；工作流不会静默跳过
已有文件名。后续阶段失败时优先使用 **Re-run failed jobs**，保留已检查的发行包。
不重新构建或移动已发布版本的标签；上传字节需要改变时准备新版本。
PyPI 上传后若安装验证或 GitHub Release 创建失败，上传已实际发生，修复对应阶段，
不要重新发布。

发布后核对两个项目页面、GitHub Release 和工作流结果。安装检查只运行帮助，不触碰真实
剪贴板。核对 README 的 PyPI 版本与 Python 版本徽章；Python 徽章读取已发布的 classifiers，
缓存刷新可能延迟，显示正确后才恢复该徽章。

针对工作流实际清单的本地诊断命令：

```sh
uv run --locked python scripts/verify_published.py testpypi path/to/manifest.json
uv run --locked python scripts/verify_published.py pypi path/to/manifest.json
```

打标签前可用 `uv run --locked python scripts/release.py vX.Y.Z --dist-dir dist/verify-1`
检查本地构建的发行包与说明；工作流另启用 `--check-git`，要求真实标签及其在 `main` 中的祖先关系。

交付说明准确标签、源码提交、运行链接、索引结果及剩余限制。
本地构建、纯验证、TestPyPI 上传和 PyPI 发布是不同结果，只报告实际完成的部分。
