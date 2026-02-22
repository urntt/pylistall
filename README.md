# pylistall

[![PyPI version](https://img.shields.io/pypi/v/pylistall.svg)](https://pypi.org/project/pylistall/)
[![Python versions](https://img.shields.io/pypi/pyversions/pylistall.svg)](https://pypi.org/project/pylistall/)
[![License](https://img.shields.io/github/license/urntt/pylistall.svg)](https://github.com/urntt/pylistall)

[中文说明](README.zh-CN.md)

`pylistall` is a cross-platform command-line tool that collects file contents under a directory and copies them to the system clipboard in a structured format.

It also prints the absolute path and a tree-style directory structure. If the directory contains a `.git` repository, it can optionally include the Git commit log.

This tool is designed for efficiently sharing project context with AI tools, debugging, documentation, or code review.

---

## Features

* Copy file contents directly to clipboard
* Tree-style directory structure output (by default, only files in the current directory are included)
* Display absolute path
* Recursive traversal of subdirectories (optional, disabled by default)
* Include or exclude files using glob patterns (optional, includes all non-binary files by default)
* Include binary files (optional, disabled by default)
* Include Git log (optional, disabled by default)
* Cross-platform support:

  * macOS (`pbcopy`)
  * Windows (`clip`)
  * Linux (`xclip` or `pyperclip` fallback)

---

## Installation

From the project root (where `pyproject.toml` is located):

```bash
python -m pip install .
```

Verify installation:

```bash
pylistall --help
```

Uninstall:

```bash
python -m pip uninstall pylistall
```

---

## Usage

```bash
pylistall [path] [options]
```

If `path` is not provided, the current directory (`.`) is used.

---

## Output Format

Example:

````text
STRUCTURE:
/Users/example/project
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

## Options

### Recursive traversal

```bash
-r, --recursive
```

Recursively include files in subdirectories.
Optional, disabled by default. When enabled, both the tree structure and copied file contents will include files from the current directory, subdirectories, and all nested subdirectories.

Example:

```bash
pylistall -r
```

---

### Include binary files

```bash
-b, --binary
```

Include binary files.
Optional, disabled by default. When enabled, binary file contents will be included like regular files. Regardless of whether this option is enabled, binary file names will always appear in the tree structure.

Example:

```bash
pylistall -b
```

---

### Include Git log

```bash
-g, --git-log [N]
```

Optional, disabled by default. Behavior depends on usage:

| Command | Result                             |
| ------- | ---------------------------------- |
| no `-g` | do not include Git log             |
| `-g`    | include all Git log entries        |
| `-g N`  | include the last N Git log entries |

Examples:

```bash
pylistall -g
```

```bash
pylistall -g 5
```

When enabled, if the ROOT directory does not contain a `.git` folder, a message will be shown.

---

### Include only specific files

```bash
-i, --include PATTERN
```

Include only files matching glob patterns.
Optional, disabled by default. When enabled, both the tree structure and copied file contents will include only the selected files. Multiple patterns can be separated by commas.

Examples:

```bash
pylistall -i "*.py"
```

```bash
pylistall -i "*.py,README.md"
```

---

### Omit specific files

```bash
-o, --omit PATTERN
```

Exclude files matching glob patterns.
Optional, disabled by default. When enabled, both the tree structure and copied file contents will exclude the selected files. Multiple patterns can be separated by commas.

Examples:

```bash
pylistall -o "*.log"
```

```bash
pylistall -o "*.log,*.tmp"
```

---

### Limit file read size

```bash
--max-bytes N
```

Limit the maximum number of bytes read per file.
Optional, disabled by default. When enabled, reading of each file will be limited to at most N bytes.

Example:

```bash
pylistall --max-bytes 10000
```

---

## Examples

Basic usage:

```bash
pylistall
```

Recursive traversal with Git log:

```bash
pylistall -r -g 3
```

Include binary files:

```bash
pylistall -b
```

Include only Python files:

```bash
pylistall -i "*.py"
```

Exclude test files:

```bash
pylistall -o "test_*"
```

---

## Clipboard Support

Platform-specific clipboard backends:

| Platform | Backend           |
| -------- | ----------------- |
| macOS    | pbcopy            |
| Windows  | clip              |
| Linux    | xclip / pyperclip |

No additional configuration is required on macOS or Windows.

---

## Requirements

Python 3.9 or higher

---

## License

MIT License
