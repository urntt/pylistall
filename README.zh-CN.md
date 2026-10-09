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
* glob 模式包含或排除文件（可选，同时筛选目录树与 Files）
* 将二进制展开为 Base64 与包含 Git 日志（可选，默认禁用）
* 选择输出部分、预览收集结果及限制输出总量
* 终端分组标题、颜色、代码高亮与交互分页
* 在交互 stderr 显示收集进度与当前操作
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
围栏或代码行号；管道及重定向输出 UTF-8／LF Markdown，不受 Python 本地编码影响，
不添加 ANSI。Shell 可能解码或重新编码重定向输出；需要保证文件为 UTF-8／无 BOM／LF
时使用 `-f`，Windows PowerShell 5.1 也适用。状态提示和警告写入 stderr。

---

## 输出格式

目录包含 `README.txt` 和 `src/main.py` 时，示例输入：

```bash
cd /Users/example/project
pylistall . -r -o -c
```

剪贴板文本示例（文件导出和重定向使用相同 Markdown）：

````markdown
# `project`

```bash
/Users/example/project
├── src/
│   └── main.py
└── README.txt
```

## Files

### `README.txt`

```text
Example project.
```

### `src/main.py`

```python
print("Hello World!")
```
````

注意事项：

* 项目标题始终位于最上方；路径与树共用 `bash` 代码块，随后为可选 Git 分组和 Files。
* `-i` 同时筛选树和 Files 的文件名，保留连接文件的祖先目录；
  `-o` 隐藏匹配条目并提前剪掉完整排除的目录。
* `-r` 控制目录展开，`-l` 控制链接跟随。
* 文件夹以 `/` 结尾，链接标记 `@`，默认不读取或展开。
* 标题中的名称使用动态反引号行内代码；控制字符显示为可见转义。
  已知类型有语言标签，未知类型使用 `text`，
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

在所有目的地省略 `path`、`tree`、`git` 或 `files`，可重复或逗号分隔。
项目标题不可禁用；允许禁用全部四个部分，仅输出标题。旧 `root` 名称返回参数错误。

禁用 `files` 不采样或读取文件内容，禁用 `git` 不查询 Git。
复制、保存与终端展示使用同一组启用部分。

```bash
pylistall -r -g 3 -d files
pylistall -d path,tree -d git -c
```

---

### 仅包含指定文件

**可选，可重复使用，默认禁用。**

```text
-i, --include PATTERN
```

仅包含匹配 glob 模式的文件。可重复或逗号分隔，去除首尾空白、空项和重复规则。
通过 `fnmatch` 匹配文件名和逻辑相对路径。

当启用 `-i` 时：

* 树和 Files 仅保留匹配的文件名及其祖先目录。
* 父目录不必匹配，`-i` 不会剪掉扫描范围。
* 匹配的二进制名称仍展示，但正文必须由 `-b` 授权展开。
* 匹配的排除规则仍优先。

---

### 排除指定文件

**可选，可重复使用，默认禁用。**

```text
-o, --omit [PATTERN]
```

从树和 Files 排除匹配名称；完整排除的目录不再扫描。重复或逗号分隔的值去除空白、空项和重复规则。
排除优先于 `-i` 和 `-b`，跟随链接时同时检查逻辑路径和解析目标。

裸 `-o` 在根层和嵌套位置启用默认集：

* Git 元数据、Python 环境／缓存（包含 `.venv`）、`build`、`dist`、`*.egg-info`、`node_modules`、
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
业务日志和依赖锁文件保留。显式收集的根目录本身不参与过滤。
目录名称、相对路径或相对路径加 `/` 命中时剪枝：`src`、`src/`、`src/**`
都剪掉 `src`；`src/*.py` 只排除匹配文件，不剪掉 `src`。包含规则无法恢复被排除的子树。

以 `**/` 开头的默认规则也作用于根层。自定义模式保持普通 `fnmatch` 行为，
不自动启用默认集。`*.py` 可按文件名匹配任意层级；`src/*.py` 也可能匹配
更深路径，因为 `fnmatch` 把 `/` 当普通字符。自定义 `**/.venv/**` 不自动覆盖
根层 `.venv`；大小写处理保留平台行为。需要组合时：

```bash
pylistall -o -o "README.md,test_cases/*"
```

---

### 包含二进制文件

**可选，默认禁用。**

```text
-b, --binary [PATTERN]
```

只控制已选候选二进制的正文展开，不增加文件名、不改变目录树。
先由 `-o` 排除，再由 `-i` 筛选名称，最后由 `-b` 授权二进制正文；文本不需要 `-b`。

* 未提供 → 保留路径标题和二进制占位说明，不生成正文。
* 裸 `-b` → 展开全部候选二进制。
* `-b PATTERN` → 仅展开文件名或逻辑相对路径匹配的候选二进制。

获准的字节输出标准、带填充、不插入换行的 Base64，标注 `Encoding: Base64`，
使用 `text` 代码块。Base64 不压缩、不解释文件。`-m` 先限制原始字节前缀再编码，
编码仍可正确解码；二进制 `[...TRUNCATED...]` 位于代码块外，只能恢复前缀。
读取失败保留错误标记，不编码错误文字。

```bash
pylistall -b
pylistall -i "*.png" -b
pylistall -i "*.py" -b "*.png"  # 不额外加入 PNG 候选
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
* 递归时查找未剪枝目录中的嵌套仓库。
* 查找独立于 `-i`；`.git` 元数据被排除时仍可显式读取日志，
  但完整排除的上级目录内不再查找仓库。
* 未启用排除时，`.git` 仍可作为普通数据出现在树和 Files 中。
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
内容显示逻辑相对路径，排除也检查解析目标及其被排除的目录祖先。祖先循环和跟随后断链跳过并警告，
非循环的重复别名分别保留。显式传入的根目录链接即使没有此选项也会解析。

---

### 预览收集结果

**可选，默认禁用。**

```text
-D, --dry-run
```

准确收集后向 stderr 报告 Markdown UTF-8 大小、Files 条目数、实际收集数、已发现条目、跳过数及目的地。
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

为全部启用部分生成的 Markdown 设置正整数 UTF-8 字节预算，包含标题、编码说明、围栏及换行。
不计算颜色、进度、摘要和状态提示；此预算不等于总内存限制。超限返回 1，不交付部分终端正文、剪贴板内容或文件。
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

### 关闭进度反馈

**可选；stderr 为交互终端且 `TERM` 不为 `dumb` 时默认启用。**

```text
-P, --no-progress
```

扫描、树组装和 Git 使用转圈显示当前操作，未知总量不显示百分比。
文件阶段显示已检查／候选总数及实际收集数量；终端排版还有独立的 `render` 阶段，
显示当前路径和已排版块数，完成后再展示或分页。路径按字面量展示并按终端宽度裁剪，
每秒最多刷新 10 次。stdout 重定向、`-f`、`-c`、`-D` 不单独关闭进度，
只要 stderr 仍是终端即可显示；重定向 stderr 或使用 `-P` 可关闭。
此选项与控制分页的 `-n` 独立。正文或分页前先清理进度。
反馈组件缺失或失效时静默关闭；Ctrl+C 清理资源并返回 130。

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
