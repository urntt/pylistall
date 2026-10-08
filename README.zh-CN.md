# pylistall

[![PyPI version](https://img.shields.io/pypi/v/pylistall.svg)](https://pypi.org/project/pylistall/)
[![Python versions](https://img.shields.io/pypi/pyversions/pylistall.svg)](https://pypi.org/project/pylistall/)
[![License](https://img.shields.io/github/license/urntt/pylistall.svg)](https://github.com/urntt/pylistall)

[English](README.md)

pylistall 是跨平台 CLI，帮助你与 AI、审查者或协作者分享项目上下文。一个命令收集
目录树、选定文件内容和可选 Git 历史，展示结果、复制 Markdown 或保存为单个本地文件。
需要 Python 3.9 或更高版本。

## 安装

```sh
python -m pip install pylistall
pylistall --help
```

未发布的检出版本可使用 `python -m pip install .`。以下变更尚未发布；已发布行为见
[GitHub Releases](https://github.com/urntt/pylistall/releases)。

## 用法

```sh
pylistall [path] [options]
pylistall . -r -o
pylistall . -r -o -c
pylistall . -r -o -f context.md
pylistall . -r -g 3 -d files
pylistall . -r -o -D -M 100000 -f
```

收集根路径默认是当前目录。默认展示结果，不操作剪贴板。管道或重定向输出 Markdown；
状态提示和警告写入 stderr。

| 选项 | 行为 |
| --- | --- |
| `-r --recursive` | 展开子目录；否则只收集直接文件 |
| `-i --include PATTERN` | 限定内容，可重复或逗号分隔 |
| `-o --omit [PATTERN]` | 排除内容；裸 `-o` 启用下述默认集 |
| `-b --binary [PATTERN]` | 包含所有二进制文件或仅匹配者 |
| `-m --max-bytes N` | 单文件源字节上限，标记截断 |
| `-g --git-log [N]` | 全部或最近 N 个提交，默认关闭 |
| `-l --follow-links` | 跟随文件和目录链接，允许根外目标 |
| `-c --copy` | 额外复制 Markdown，终端仍展示 |
| `-f --file [DEST]` | 保存单文件，不展示终端正文，可与 `-c` 组合 |
| `-w --overwrite` | 允许覆盖输出文件，必须配合 `-f` |
| `-d --disable PARTS` | 省略 `root`、`tree`、`git`、`files`，可重复或逗号分隔 |
| `-D --dry-run` | 准确收集并报告大小、目的地，不复制、不写入 |
| `-M --max-output-bytes N` | 正整数 Markdown UTF-8 总量预算，默认不限 |
| `-h --help` | 显示帮助 |

至少保留一个输出部分。禁用 `files` 不采样或读取内容，禁用 `git` 不查询 Git。
所有目的地使用同一组启用部分。总量超限返回 1，不交付正文、剪贴板内容或文件。
预算包含标题、围栏和换行，不包含状态提示。

### 筛选与链接

模式通过 `fnmatch` 匹配名称和逻辑相对路径；重复或逗号分隔的模式去除空白与空项。
排除优先于包含和二进制策略；显式 `-i` 可强制包含二进制，`-b` 只影响二进制。
字节以 UTF-8 替换解码，不解压或解释图片、文档；业务日志与依赖锁文件仍可收集。

内容过滤不隐藏目录树名称。目录以 `/` 结尾，链接标记 `@`，默认不读取或展开。
`-l` 允许根外目标，目录展开仍需 `-r`。祖先循环和跟随后断链跳过并警告；非循环的
重复别名分别保留。排除同时检查逻辑和解析路径；显式根目录链接会解析。

裸 `-o` 在根层和嵌套位置覆盖这些类别：

- Git 元数据、Python 环境／缓存、`build`、`dist`、`*.egg-info`、`node_modules`、
  `.idea`、`.vscode`、`.gitignore`、`.DS_Store`、`Thumbs.db`。
- Python／测试：`.nox`、`.hypothesis`、`.ipynb_checkpoints`、`__pypackages__`、
  `.eggs`、`htmlcov`、`.coverage`、`.coverage.*`。
- 前端：`.next`、`.nuxt`、`.output`、`.svelte-kit`、`.turbo`、`.parcel-cache`、
  `.vite`、`coverage`、`.nyc_output`、`*.tsbuildinfo`、`.eslintcache`、`.stylelintcache`。
- 其他生成文件：`.cache`、`target`、`.gradle`、`.vs`、`*.swp`、`*.swo`、`*~`、
  `desktop.ini`、`pylistall-output-*.md`。
- 敏感名称：`.env`、`.env.*`、`.envrc`、`.pypirc`、`.netrc`、`id_rsa`、`id_dsa`、
  `id_ecdsa`、`id_ed25519`、`*.key`、`*.pem`、`*.p12`、`*.pfx`、
  `.aws/credentials`、`.streamlit/secrets.toml`。

名单也会排除部分样例与公开证书，不能检测任意秘密，不读取 `.gitignore`。
自定义 `-o PATTERN` 不启用默认集；可用 `-o -o "custom/*"` 组合。分享前审查内容，
实际边界见[架构](docs/architecture.zh-CN.md#安全边界与当前限制)。

### 文件目的地

裸 `-f` 保存在**命令执行目录**，使用本机本地时间文件名
`pylistall-output-%Y-%m-%d-%H-%M-%S.md`。相对目的地同样从命令执行目录计算，
独立于收集根目录；支持绝对路径及 `~`。已有目录或以平台路径分隔符结尾的参数使用
该目录加默认名称；其他参数是完整文件名，不自动补扩展名。

收集与预算成功后才创建缺失父目录。已有名称和同秒碰撞默认报错，`-w` 才允许覆盖。
文件使用 UTF-8、无 BOM、LF；覆盖失败保留原文件。本次目标及其别名始终排除于内容
收集之外，即使没有 `-o`，已有名称仍可出现在树中。`-D` 预览大小与目的地，不创建
目录、不写文件、不复制。失败返回非零，stderr 准确报告每个已完成的目的地。

### Git 历史

`-g` 查找 `.git` 目录与 worktree 指针文件。非递归只查根层，递归按绝对路径分组，
日志使用 oneline 和 decorate。无仓库、空日志及 Git 失败有明确标记，需 PATH 中有 Git。

## 输出格式

目录包含 `README.txt` 和 `src/main.py` 时，`pylistall . -r -o` 输出：

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

首行是绝对根路径，可选 Git 分组在文件之前。路径按 Markdown 字面量转义；已知类型
使用语言标签，未知类型使用 `text`。围栏随内容增长避免反引号冲突，保留排序与
`[...TRUNCATED...]` 标记。

## 从 0.3.1 迁移

默认复制改为默认展示，需要继续复制时添加 `-c`；不展示正文的导出使用 `-f`。
移除 `-p --print`：直接省略即可展示，替换为 `-c` 即可展示并复制。
`-d files` 省略文件名及内容，保留其他部分；`-h` 仍是帮助。
Markdown 新增分组标题、语言标签及防冲突围栏。

## 剪贴板支持

仅 `-c` 需要剪贴板：macOS 使用 `pbcopy`，Windows 使用 `clip`，Linux 使用 `xclip`
或 pyperclip。默认展示及文件导出无需桌面环境。

## 贡献与发布

见[开发指南](docs/development.zh-CN.md)、[愿景](VISION.zh-CN.md)及
[架构](docs/architecture.zh-CN.md)。变更见[更新记录](CHANGELOG.zh-CN.md)，维护者遵循
[发布指南](docs/releasing.zh-CN.md)。项目使用 MIT 许可证。
