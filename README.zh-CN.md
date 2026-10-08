# pylistall

[![PyPI version](https://img.shields.io/pypi/v/pylistall.svg)](https://pypi.org/project/pylistall/)
[![Python versions](https://img.shields.io/pypi/pyversions/pylistall.svg)](https://pypi.org/project/pylistall/)
[![License](https://img.shields.io/github/license/urntt/pylistall.svg)](https://github.com/urntt/pylistall)

[English](README.md)

`pylistall` 是一个跨平台命令行工具，用于收集指定目录下的文件内容，并以结构化格式
展示结果。它也可以将 Markdown 复制到系统剪贴板或导出为单个文件。

输出包含绝对路径和树状目录结构。如果目录包含 `.git` 仓库，还可以选择附加 Git 提交日志。

该工具适用于高效地与 AI 工具共享项目上下文，以及用于调试、文档编写或代码审查。

---

## 功能特性

* 默认在终端展示收集到的上下文
* 复制 Markdown 到剪贴板或保存为单文件（可选）
* 树状目录结构与绝对根路径
* 递归遍历子目录（可选，默认禁用）
* glob 模式包含或排除文件（可选，默认包含非二进制文件）
* 包含二进制文件与 Git 日志（可选，默认禁用）
* 选择输出部分、预览收集结果及限制输出总量
* 终端分组标题、颜色、代码高亮与交互分页
* 跨平台支持：macOS、Windows、Linux

---

## 安装

使用 PyPI：

```bash
python -m pip install pylistall
```

或者，在项目根目录（包含 `pyproject.toml` 的目录）执行：

```bash
python -m pip install .
```

验证安装：

```bash
pylistall --help
```

卸载：

```bash
python -m pip uninstall pylistall
```

---

## 使用方法

```bash
pylistall [path] [options]
```

如果未提供 `path`，则默认使用当前目录（`.`）。

默认展示结果，不操作剪贴板。交互终端使用分组标题、颜色及代码高亮，不显示 Markdown
围栏或代码行号；管道及重定向使用 Markdown，不添加 ANSI。状态提示和警告写入 stderr。

---

## 输出格式

目录包含 `README.txt` 和 `src/main.py` 时，示例输入：

```bash
cd /Users/example/project
pylistall . -r -o -c
```

剪贴板文本示例（文件导出和重定向使用相同 Markdown）：

````markdown
/Users/example/project

## Directory tree

```text
├── src/
│   └── main.py
└── README.txt
```

## Files

### README\.txt

```text
Example project.
```

### src/main\.py

```python
print("Hello World!")
```
````

注意事项：

* 首行是根路径，随后依次为目录树、可选 Git 分组、文件内容。
* 目录树反映真实文件系统；内容过滤不隐藏树中的名称。
* `-r` 控制目录展开，`-l` 控制链接跟随。
* 文件夹以 `/` 结尾，链接标记 `@`，默认不读取或展开。
* Markdown 路径按字面量转义；已知类型有语言标签，未知类型使用 `text`，
  围栏随内容增长避免反引号冲突。
* 保留内容排序及 `[...TRUNCATED...]` 标记。

---

## 选项说明

### 递归遍历

**可选，默认禁用。**

```text
-r, --recursive
```

递归包含子目录。启用时：

* 目录树包含嵌套文件和文件夹。
* 内容收集包含嵌套目录中符合筛选规则的文件。
* 同时启用 `-g` 时，也会查找嵌套 Git 仓库。

---

### 复制输出到剪贴板

**可选，默认禁用。**

```text
-c, --copy
```

额外复制完整 Markdown。除非同时使用 `-f`，终端仍展示结果。
只有此选项需要可用的剪贴板后端。

---

### 保存输出到文件

**可选，默认禁用。**

```text
-f, --file [DEST]
```

将所有启用部分保存为单文件，不展示终端正文。可与 `-c` 组合，保存并复制同一份 Markdown。

目的地规则：

* 裸 `-f` 保存到**命令执行目录**，使用本地时间文件名
  `pylistall-output-%Y-%m-%d-%H-%M-%S.md`。
* 相对路径从同一个命令执行目录计算，独立于收集根目录；支持绝对路径与 `~`。
* 已有目录或以平台路径分隔符结尾的参数使用该目录加默认名称；其他参数是完整文件名。
* 自定义名称不自动添加扩展名。
* 收集与预算验证成功后才创建缺失的父目录。
* 已有名称及同秒碰撞默认报错，只有 `-w` 才允许覆盖。
* 文件使用 UTF-8、无 BOM、LF；覆盖失败保留原文件。
* 本次目标及其别名始终排除于内容之外，即使没有 `-o`；已有名称仍可出现在树中。

失败返回非零，stderr 准确报告每个已完成的目的地。

示例：

```bash
pylistall -r -o -f
pylistall -r -o -f context.md
pylistall -r -o -f ../exports/context -c
```

---

### 覆盖输出文件

**可选，默认禁用，必须配合 `-f`。**

```text
-w, --overwrite
```

允许替换已有输出文件，不能把目录覆盖成文件。同目录临时文件完成写入后才替换；
失败清理本次不完整文件，保留原文件。

```bash
pylistall -r -o -f context.md -w
```

---

### 禁用输出部分

**可选，可重复使用，默认禁用。**

```text
-d, --disable PARTS
```

在所有目的地省略 `root`、`tree`、`git` 或 `files`，可重复或逗号分隔。
至少保留一个实际启用的输出部分。

禁用 `files` 不采样或读取文件内容，禁用 `git` 不查询 Git。
复制、保存与终端展示使用同一组启用部分。

```bash
pylistall -r -g 3 -d files
pylistall -d root,tree -d git -c
```

---

### 仅包含指定文件

**可选，可重复使用，默认禁用。**

```text
-i, --include PATTERN
```

仅包含匹配 glob 模式的文件。可重复或逗号分隔，去除首尾空白与空项。
通过 `fnmatch` 匹配文件名和逻辑相对路径。

当启用 `-i` 时：

* 只有匹配的文件进入内容输出。
* 匹配的二进制文件即使没有 `-b` 也可包含。
* 匹配的排除规则仍优先。

---

### 排除指定文件

**可选，可重复使用，默认禁用。**

```text
-o, --omit [PATTERN]
```

排除匹配 glob 模式的内容。重复或逗号分隔的值去除空白与空项。
排除优先于 `-i` 和 `-b`，跟随链接时同时检查逻辑路径和解析目标。

裸 `-o` 在根层和嵌套位置启用默认集：

* Git 元数据、Python 环境／缓存、`build`、`dist`、`*.egg-info`、`node_modules`、
  `.idea`、`.vscode`、`.gitignore`、`.DS_Store`、`Thumbs.db`。
* Python／测试：`.nox`、`.hypothesis`、`.ipynb_checkpoints`、`__pypackages__`、
  `.eggs`、`htmlcov`、`.coverage`、`.coverage.*`。
* 前端：`.next`、`.nuxt`、`.output`、`.svelte-kit`、`.turbo`、`.parcel-cache`、
  `.vite`、`coverage`、`.nyc_output`、`*.tsbuildinfo`、`.eslintcache`、`.stylelintcache`。
* 其他生成文件：`.cache`、`target`、`.gradle`、`.vs`、`*.swp`、`*.swo`、`*~`、
  `desktop.ini`、`pylistall-output-*.md`。
* 敏感名称：`.env`、`.env.*`、`.envrc`、`.pypirc`、`.netrc`、`id_rsa`、`id_dsa`、
  `id_ecdsa`、`id_ed25519`、`*.key`、`*.pem`、`*.p12`、`*.pfx`、
  `.aws/credentials`、`.streamlit/secrets.toml`。

名单也会排除部分样例与公开证书，不能检测任意秘密，不加载 `.gitignore`。
业务日志和依赖锁文件保留；排除内容不会隐藏目录树名称。

以 `**/` 开头的默认规则也作用于根层。自定义模式保持普通 `fnmatch` 行为，
不自动启用默认集。需要组合时：

```bash
pylistall -o -o "README.md,test_cases/*"
```

---

### 包含二进制文件

**可选，默认禁用。**

```text
-b, --binary [PATTERN]
```

控制二进制包含，不影响文本文件。字节以 UTF-8 替换解码，不转换或解压图片、文档、压缩包。

优先级规则：

1. `-o` 始终排除匹配的文件，包括二进制。
2. `-i` 可强制包含指定二进制文件。
3. `-b` 仅控制其余二进制文件。

包含规则：

* 未提供 → 排除二进制，除非由 `-i` 强制包含。
* 裸 `-b` → 包含所有二进制。
* `-b PATTERN` → 仅包含匹配的二进制。

```bash
pylistall -b
pylistall -b "*.zip,photo.png"
pylistall -i "run.exe"
```

---

### 包含 Git 日志

**可选，默认禁用。**

```text
-g, --git-log [N]
```

裸 `-g` 包含全部提交，`-g N` 包含最近 N 条，N 必须为正数。

规则：

* 非递归仅检查根层 `.git` 目录或 worktree 指针文件。
* 递归时查找嵌套仓库。
* 分组按绝对 `.git` 路径排序，大小写不敏感。
* 日志使用 oneline 和 decorate，Markdown 分组使用路径子标题。
* 无仓库、空日志及 Git 失败都有明确标记。
* 需 PATH 中有 Git；`-d git` 关闭查询和输出。

---

### 限制文件读取大小

**可选，默认不限。**

```text
-m, --max-bytes N
```

限制每个文件读取的源字节数，N 必须非负。超出时添加 `[...TRUNCATED...]`。
此选项不限制目录树或 Git 日志。

---

### 跟随链接

**可选，默认禁用。**

```text
-l, --follow-links
```

跟随文件和目录链接，允许根目录之外的目标；目录展开仍需 `-r`。
内容显示逻辑相对路径，排除也检查解析目标。祖先循环和跟随后断链跳过并警告，
非循环的重复别名分别保留。显式传入的根目录链接即使没有此选项也会解析。

---

### 预览收集结果

**可选，默认禁用。**

```text
-D, --dry-run
```

准确收集后向 stderr 报告 Markdown UTF-8 大小、选中文件数、跳过条目及目的地。
不展示正文、不复制、不创建目录或文件。可与 `-c`、`-f` 组合预览目的地。

```bash
pylistall -r -o -D -c -f context.md
```

---

### 限制输出总量

**可选，默认不限。**

```text
-M, --max-output-bytes N
```

为全部启用部分生成的 Markdown 设置正整数 UTF-8 字节预算，包含标题、围栏及换行。
不计算颜色、摘要和状态提示。超限返回 1，不交付部分终端正文、剪贴板内容或文件。
dry-run 的大小与实际 Markdown 一致。

---

### 关闭终端分页

**可选，交互终端默认自动分页。**

```text
-n, --no-pager
```

分页要求 stdin、stdout 都是终端。优先使用 `PAGER`，否则查找 `less`（包括 Git for
Windows 自带程序），再回退系统 `more`。Less 默认 `-FRX`：短输出自动退出，空格翻页，
`/` 搜索，`q` 退出。空 `PAGER` 也会关闭分页；配置命令拆为程序与参数，不执行 shell 展开。

没有分页器或启动失败时直接展示。More 使用无颜色的平台编码，当前 Windows 代码页无法
表示的字符可能被替换。Rich 导入失败静默回退 Markdown；复制和文件始终保持 Markdown。
参考 [Git 分页默认值](https://git-scm.com/docs/git-config#Documentation/git-config.txt-corepager)。

---

### 帮助

```text
-h, --help
```

显示命令用法和可用选项。

---

## 使用示例

基础用法：

```bash
pylistall
```

递归收集，启用默认排除并包含最近三条 Git 提交：

```bash
pylistall -r -o -g 3
```

复制上下文或保存到文件：

```bash
pylistall -r -o -c
pylistall -r -o -f context.md
```

仅包含 Python 文件或排除测试文件：

```bash
pylistall -i "*.py"
pylistall -o "test/test_*"
```

预览目的地并限制总量：

```bash
pylistall -r -o -D -M 100000 -c -f context.md
```

---

## 剪贴板支持

不同平台使用的剪贴板后端：

| 平台 | 后端 |
| --- | --- |
| macOS | `pbcopy` |
| Windows | `clip` |
| Linux | `xclip` / `pyperclip` |

仅 `-c` 需要可用的桌面剪贴板，展示及文件导出无需剪贴板。分享前检查选定内容，
实际边界见[架构文档](docs/architecture.zh-CN.md#安全边界与当前限制)。

---

## 环境要求

Python 3.9 或更高版本；只有收集 Git 历史时才需要 Git。

---

## 许可证

MIT License

## 参与开发

环境准备、检查、构建和贡献步骤见[开发指南](docs/development.zh-CN.md)。
产品方向见[愿景](VISION.zh-CN.md)，模块职责与数据流见[架构文档](docs/architecture.zh-CN.md)。

## 版本发布

版本变更与迁移说明见[更新记录](CHANGELOG.zh-CN.md)，已发布版本见
[GitHub Releases](https://github.com/urntt/pylistall/releases)。维护者使用[发布指南](docs/releasing.zh-CN.md)。
