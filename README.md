# pylistall

[![PyPI version](https://img.shields.io/pypi/v/pylistall.svg)](https://pypi.org/project/pylistall/)
[![License](https://img.shields.io/github/license/urntt/pylistall.svg)](https://github.com/urntt/pylistall)

[中文说明](README.zh-CN.md)

`pylistall` is a cross-platform command-line tool that collects file contents under a directory and copies them to the system clipboard in a structured format.

It also prints the absolute path and a tree-style directory structure. If the directory contains a `.git` repository, it can optionally include the Git commit log.

This tool is designed for efficiently sharing project context with AI tools, debugging, documentation, or code review.

---

## Features

* Copy file contents directly to clipboard
* Tree-style directory structure output
* Display absolute path
* Recursive traversal of subdirectories (optional, disabled by default)
* Include or omit files using glob patterns (optional, includes all non-binary files by default)
* Include binary files (optional, disabled by default)
* Git log output (optional, disabled by default)
* Cross-platform support:

  * macOS (`pbcopy`)
  * Windows (`clip`)
  * Linux (`xclip` or `pyperclip` fallback)

---

## Installation

Using PyPI:

```bash
python -m pip install pylistall
```

Or, from the project root (where `pyproject.toml` is located):

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

If `[path]` is not provided, the current directory (`.`) is used.

---

## Output Format

Example input:

```bash
cd /Users/example/project
pylistall . -r -o -g
```

Example output:

````text
/Users/example/project
├── .git/
│   ├── HEAD
│   ├── config
│   └── ...
├── src/
│   └── main.py
└── README.txt

/Users/example/project/.git
a1b2c3d (HEAD -> main) Initial commit

`README.txt`:

```
This is an exmaple Project.
```

`src/main.py`:

```
print("Hello World!")
```
````

Notes:

* The tree always reflects the real filesystem.
* Tree behavior is only affected by `-r`, not affected by `-i`, `-o`, or `-b`.
* Directories end with `/`.

---

## Options

### Recursive traversal

```bash
-r, --recursive
```

Recursively include subdirectories.

When enabled:

* Tree will include files from the current directory, subdirectories, and all nested subdirectories
* Copied file content will include files in all these directories
* Will try to find Git logs in all directories

**Optional, disabled by default.**

---

### Print copied content

```bash
-p, --print
```

Print the full generated output to stdout.

**Optional, disabled by default.**

---

### Include only specific files

```bash
-i, --include PATTERN
```

Include only files matching glob patterns, using Comma-separated patterns.

When `-i` is used:

* Only matching files are included in content output (whitelist mode)
* `-i` can force-include binary files even if `-b` is not provided

**Optional, repeatable, disabled by default.**

---

### Omit specific files

```bash
-o, --omit [PATTERN]
```

Exclude files matching glob patterns, using Comma-separated patterns.

Behavior:

* If `-o` is provided without `[PATTERN]`, a default omit set is enabled.
  The default set includes:
  `.git/**`, `**/__pycache__/**`, `**/.pytest_cache/**`, `**/.mypy_cache/**`, `**/.ruff_cache/**`, `**/.tox/**`, `**/.venv/**`, `**/venv/**`, `**/build/**`, `**/dist/**`, `**/*.egg-info/**`, `**/node_modules/**`, `**/.idea/**`, `**/.vscode/**`, `**/.gitignore`, `**/.DS_Store`, `**/Thumbs.db`

* If both default and custom omit rules are desired, repeat `-o`:

```bash
pylistall -o -o "README.md,test_cases/*"
```

**Optional, repeatable, disabled by default.**

---

### Binary files

```bash
-b, --binary [PATTERN]
```

Controls whether binary files are included in content output.
Does not affact non-binary files.

Precedence rules:

1. `-o` always omits matching files (including binariy files).
2. `-i` can force-include specific binary files.
3. `-b` controls only remaining binary files.

Inclusion rules:

* Not provided (disabled) → binary files excluded (unless forced by `-i`)
* `-b` → include all binary files
* `-b [PATTERN]` → include only binary files matching `[PATTERN]`

Examples:

```bash
pylistall -b
pylistall -b "*.zip,photo.png"
pylistall -i "run.exe"
```

Default set of binary files:

  `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.bmp`, `.ico`, `.pdf`, `.zip`, `.rar`, `.7z`, `.tar`, `.gz`, `.bz2`, `.xz`, `.exe`, `.dll`, `.so`, `.dylib`, `.bin`, `.dat`, `.class`, `.jar`, `.pyc`, `.pyo`, `.woff`, `.woff2`, `.ttf`, `.otf`, `.mp3`, `.wav`, `.flac`, `.mp4`, `.mov`, `.mkv`, `.avi`, `.doc`, `.docx`

**Optional, disabled by default.**

---

### Git log

```bash
-g, --git-log [N]
```

Include Git log output.

Behavior:

* If not provided (disabled) → no Git logs
* `-g` → include all entries
* `-g N` → include last N entries

Rules:

* If no `.git` entry is found, `[No .git found]` is included in the output.
* Without `-r`, only the `.git` folder or file in the root folder is checked.
* With `-r`, `.git` entries are discovered recursively.
* Each Git log group is prefixed with the absolute `.git` path.
* Multiple `.git` are printed as separate groups.

  When multiple `.git` entries are found:
  * They are sorted by path (case-insensitive), separated by blank lines.
  * If both a `.git` directory and a `.git` file exist at the same path, the directory is printed first and the file second.

**Optional, disabled by default.**

---

### Limit file read size

```bash
-m, --max-bytes N
```

Limit the maximum number of bytes read per file.
If content exceeds `N` bytes, it is truncated and marked.

**Optional, disabled by default.**

---

## Examples

Basic usage:

```bash
pylistall
```

Recursive traversal with 3 recent Git logs:

```bash
pylistall -r -g 3
```

Enable default omit set:

```bash
pylistall -o
```

Allow all binary files:

```bash
pylistall -b
```

Include only Python files:

```bash
pylistall -i "*.py"
```

Exclude all files that starts with `test_` in `test` folder:

```bash
pylistall -o "test/test_*"
```

---

## Clipboard Support

Platform-specific clipboard backends:

| Platform | Backend           |
| -------- | ----------------- |
| macOS    | pbcopy            |
| Windows  | clip              |
| Linux    | xclip / pyperclip |

---

## Requirements

Python 3.9 or higher

---

## License

MIT License
