# pylistall

[![PyPI version](https://img.shields.io/pypi/v/pylistall.svg)](https://pypi.org/project/pylistall/)
[![License](https://img.shields.io/github/license/urntt/pylistall.svg)](https://github.com/urntt/pylistall)

[English](README.md)

`pylistall` 是一个跨平台命令行工具，用于收集指定目录下的文件内容，并以结构化格式复制到系统剪贴板。

它还会输出绝对路径和树状目录结构。如果目录包含 `.git` 仓库，还可以选择附加 Git 提交日志。

该工具适用于高效地与 AI 工具共享项目上下文，以及用于调试、文档编写或代码审查。

---

## 功能特性

* 将文件内容直接复制到剪贴板
* 树状目录结构输出
* 显示绝对路径
* 递归遍历子目录（可选，默认禁用）
* 支持使用 glob 模式包含或排除文件（可选，默认包含全部非二进制文件）
* 包含二进制文件（可选，默认禁用）
* 输出 Git 日志（可选，默认禁用）
* 跨平台支持：

  * macOS（`pbcopy`）
  * Windows（`clip`）
  * Linux（`xclip` 或 `pyperclip` 作为备用方案）

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

---

## 输出格式

示例输入：

```bash
cd /Users/example/project
pylistall . -r -o -g
```

剪贴板文本示例：

```````````text
/Users/example/project
``````````
├── .git/
│   ├── config
│   └── HEAD
├── src/
│   └── main.py
└── README.txt
``````````

/Users/example/project/.git
a1b2c3d (HEAD -> main) Initial commit

`README.txt`:
``````````
This is an example project.
``````````

`src/main.py`:
``````````
print("Hello World!")
``````````
```````````

注意事项：

* 树状目录结构永远反映文件系统的真实状态。
* 树状目录结构的行为只会被 `-r` 影响，而不会被 `-i`，`-o`，或 `-b` 影响。
* 文件夹以 `/` 结尾。

---

## 选项说明

### 递归遍历

**可选，默认禁用。**

```bash
-r, --recursive
```

递归包含子目录中的文件。

启用时：

* 树状目录结构的范围将扩展至包含当前文件夹、子文件夹和子文件夹的子文件夹（以此类推）中的文件。
* 会复制以上所有文件夹里的文件内容。
* 还会尝试在这些文件夹里寻找 Git 日志。

---

### 打印复制的内容

**可选，默认禁用。**

```bash
-p, --print
```

在复制到剪贴板之前，把生成的全部内容输出到 stdout。
此选项仍需要可用的剪贴板后端。

---

### 仅包含指定文件

**可选，可重复使用，默认禁用。**

```bash
-i, --include PATTERN
```

仅包含匹配 glob 模式的文件。可重复选项或用逗号分隔模式，首尾空白和空项会被忽略。

当启用 `-i` 时：

* 只有符合条件的文件会被包含到内容输出中
* `-i` 可以强制包含二进制文件，即便没有 `-b`

---

### 排除指定文件

**可选，可重复使用，默认禁用。**

```bash
-o, --omit [PATTERN]
```

排除匹配 glob 模式的文件。可重复选项或用逗号分隔模式，首尾空白和空项会被忽略。

行为：

* 如果在使用 `-o` 时没有提供 `[PATTERN]`，则会使用一个默认忽略集。
  默认忽略集包含：
  `.git/**`，`**/__pycache__/**`，`**/.pytest_cache/**`，`**/.mypy_cache/**`，`**/.ruff_cache/**`，`**/.tox/**`，`**/.venv/**`，`**/venv/**`，`**/build/**`，`**/dist/**`，`**/*.egg-info/**`，`**/node_modules/**`，`**/.idea/**`，`**/.vscode/**`，`**/.gitignore`，`**/.DS_Store`，`**/Thumbs.db`

  以 `**/` 开头的默认规则也会作用于目标目录根层级。例如，`.venv/config.txt`
  和 `nested/.venv/config.txt` 都会被排除。自定义模式保持现有的 `fnmatch` 匹配行为。

* 如果想要在启用默认忽略集的同时忽略其他自定义规则，请重复使用 `-o`：

```bash
pylistall -o -o "README.md,test_cases/*"
```

---

### 包含二进制文件

**可选，默认禁用。**

```bash
-b, --binary [PATTERN]
```

控制是否复制二进制文件的内容。
不会影响非二进制文件。
包含的字节以 UTF-8 解码，无法解码的部分替换显示；不会转换或解压文档、图片和压缩包。

优先级规则：

1. `-o` 永远排除匹配的文件（包含二进制文件）。
2. `-i` 可以强制包含二进制文件。
3. `-b` 只控制剩余的二进制文件。

包含规则：

* 未提供（禁用）时 → 不包含二进制文件（除非被 `-i` 强制包含）
* `-b` → 包含所有二进制文件
* `-b [PATTERN]` → 包含所有匹配 `[PATTERN]` 的二进制文件

示例：

```bash
pylistall -b
pylistall -b "*.zip,photo.png"
pylistall -i "run.exe"
```

默认二进制文件集：

  `.png`，`.jpg`，`.jpeg`，`.gif`，`.webp`，`.bmp`，`.ico`，`.pdf`，`.zip`，`.rar`，`.7z`，`.tar`，`.gz`，`.bz2`，`.xz`，`.exe`，`.dll`，`.so`，`.dylib`，`.bin`，`.dat`，`.class`，`.jar`，`.pyc`，`.pyo`，`.woff`，`.woff2`，`.ttf`，`.otf`，`.mp3`，`.wav`，`.flac`，`.mp4`，`.mov`，`.mkv`，`.avi`，`.doc`，`.docx`

---

### 包含 Git 日志

**可选，默认禁用。**

```bash
-g, --git-log [N]
```

将 Git 日志添加到输出。

行为：

* 未提供（禁用）时 → 不包含 Git 日志
* 使用 `-g` 但省略参数时 → 包含全部 Git 日志
* 使用 `-g N` 时 → 包含最近 N 条 Git 日志

规则：

* 找不到 `.git` 时，会输出 `[No .git found]`。
* 没有 `-r` 时，只会检查根目录中的 `.git` 文件夹或文件。
* 有 `-r` 时，会递归查找 `.git` 文件夹或文件。
* 每一组 Git 日志前都会打印 `.git` 所在的绝对路径。
* 多个 `.git` 中的日志会被分组打印。

* 日志组按路径排序（大小写不敏感），以空行分隔。

---

### 限制文件读取大小

**可选，默认禁用。**

```bash
-m, --max-bytes N
```

限制每个文件读取的最大字节数。
如果文件内容超过了 `N` 字节，则会被截断并标记。

---

## 使用示例

基础用法：

```bash
pylistall
```

递归遍历并包含最近的三条 Git 日志：

```bash
pylistall -r -g 3
```

启用默认忽略集：

```bash
pylistall -o
```

允许全部二进制文件：

```bash
pylistall -b
```

仅包含 Python 文件：

```bash
pylistall -i "*.py"
```

排除 `test` 文件夹中所有以 `test_` 开头的文件：

```bash
pylistall -o "test/test_*"
```

---

## 剪贴板支持

不同平台使用的剪贴板后端：

* macOS：`pbcopy`
* Windows：`clip`
* Linux：`xclip` 或 `pyperclip` 作为备用方案

正常收集需要桌面剪贴板后端。工具不会自动排除秘密信息，也不会把符号链接限制在目标目录内。
分享前请检查选定文件；当前边界见[架构文档](docs/architecture.zh-CN.md#安全边界与当前限制)。

---

## 环境要求

Python 3.9 或更高版本

---

## 许可证

MIT License

## 参与开发

环境准备、检查、构建和贡献步骤见[开发指南](docs/development.zh-CN.md)。
产品方向见[愿景](VISION.zh-CN.md)，模块职责与数据流见[架构文档](docs/architecture.zh-CN.md)。
