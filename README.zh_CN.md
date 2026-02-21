# pylistall

[English](README.md)

`pylistall` 是一个跨平台命令行工具，用于收集指定目录下的文件内容，并以结构化格式复制到系统剪贴板。

它还会输出绝对路径和树状目录结构。如果目录包含 `.git` 仓库，还可以选择附加 Git 提交日志。

该工具适用于高效地与 AI 工具共享项目上下文，以及用于调试、文档编写或代码审查。

---

## 功能特性

* 将文件内容直接复制到剪贴板
* 树状目录结构输出（默认只输出当前目录下的文件）
* 显示绝对路径
* 递归遍历子目录（可选，默认禁用）
* 支持使用 glob 模式包含或排除文件（可选，默认包含全部非二进制文件）
* 包含二进制文件（可选，默认禁用）
* 输出 Git 日志（可选，默认禁用）
* 跨平台支持：

  * macOS（`pbcopy`）
  * Windows（`clip`）
  * Linux（`xclip` 或 `pyperclip` 备用方案）

---

## 安装

在项目根目录（包含 `pyproject.toml` 的目录）执行：

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

示例：

````text
ROOT: /Users/example/project

TREE:
.
├── main.py
└── utils.py

GIT LOG:
a1b2c3d (HEAD -> main) Initial commit

`main.py`:
```

print("Hello")

```

`utils.py`:
```

def func():
    pass

```

````

---

## 选项说明

### 递归遍历

```bash
-r, --recursive
```

递归包含子目录中的文件。
可选，默认禁用。启用时，树状目录结构与复制文件内容的范围将扩展至包含当前文件夹、子文件夹和子文件夹的子文件夹（以此类推）中的文件。

示例：

```bash
pylistall -r
```

---

### 包含二进制文件

```bash
-b, --binary
```

使用 `-b` 可包含二进制文件。
可选，默认禁用。启用时，二进制文件的文件内容会像其他文件一样被包含。无论是否启用这个选项，二进制文件的文件名都会出现在树状目录结构中。

示例：

```bash
pylistall -b
```

---

### 包含 Git 日志

```bash
-g, --git-log [N]
```

可选，默认禁用。行为取决于使用方式：

* 不使用 `-g` 时不包含 Git 日志
* 使用`-g` 但省略参数时包含全部 Git 日志
* 使用 `-g N` 时包含最近 N 条 Git 日志

示例：

```bash
pylistall -g
```

```bash
pylistall -g 5
```

启用时，如果 ROOT 目录中不存在 `.git` 文件夹，将显示提示信息。

---

### 仅包含指定文件

```bash
-i, --include PATTERN
```

仅包含匹配 glob 模式的文件。
可选，默认禁用。启用时，树状目录结构和复制文件内容将只包含选定的文件。多个文件之间使用逗号分隔。

示例：

```bash
pylistall -i "*.py"
```

```bash
pylistall -i "*.py,README.md"
```

---

### 排除指定文件

```bash
-o, --omit PATTERN
```

排除匹配 glob 模式的文件。
可选，默认禁用。启用时，树状目录结构和复制文件内容将排除选定的文件。多个文件之间使用逗号分隔。

示例：

```bash
pylistall -o "*.log"
```

```bash
pylistall -o "*.log,*.tmp"
```

---

### 限制文件读取大小

```bash
--max-bytes N
```

限制每个文件读取的最大字节数。
可选，默认禁用。启用时，在每个文件的读取过程中将限制最多读取 N 字节内容。

示例：

```bash
pylistall --max-bytes 10000
```

---

## 使用示例

基础用法：

```bash
pylistall
```

递归遍历并包含 Git 日志：

```bash
pylistall -r -g 3
```

包含二进制文件：

```bash
pylistall -b
```

仅包含 Python 文件：

```bash
pylistall -i "*.py"
```

排除测试文件：

```bash
pylistall -o "test_*"
```

---

## 剪贴板支持

不同平台使用的剪贴板后端：

* macOS：`pbcopy`
* Windows：`clip`
* Linux：`xclip` 或 `pyperclip` 作为备用方案

macOS 和 Windows 无需额外配置。

---

## 环境要求

Python 3.9 或更高版本

---

## 许可证

MIT License
