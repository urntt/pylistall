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

Example clipboard text:

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

Notes:

* The tree always reflects the real filesystem.
* Tree behavior is only affected by `-r`, not affected by `-i`, `-o`, or `-b`.
* Directories end with `/`.

---

## Options

### Recursive traversal

**Optional, disabled by default.**

```bash
-r, --recursive
```

Recursively include subdirectories.

When enabled:

* Tree will include files from the current directory, subdirectories, and all nested subdirectories
* Copied file content will include files in all these directories
* Will try to find Git logs in all directories

---

### Print copied content

**Optional, disabled by default.**

```bash
-p, --print
```

Print the full generated output to stdout before copying it to the clipboard.
This option still requires a working clipboard backend.

---

### Include only specific files

**Optional, repeatable, disabled by default.**

```bash
-i, --include PATTERN
```

Include only files matching glob patterns. Repeat the option or use comma-separated
patterns; surrounding whitespace and empty entries are ignored.

When `-i` is used:

* Only matching files are included in content output (whitelist mode)
* `-i` can force-include binary files even if `-b` is not provided

---

### Omit specific files

**Optional, repeatable, disabled by default.**

```bash
-o, --omit [PATTERN]
```

Exclude files matching glob patterns. Repeat the option or use comma-separated
patterns; surrounding whitespace and empty entries are ignored.

Behavior:

* If `-o` is provided without `[PATTERN]`, a default omit set is enabled.
  The default set includes:
  `.git/**`, `**/__pycache__/**`, `**/.pytest_cache/**`, `**/.mypy_cache/**`, `**/.ruff_cache/**`, `**/.tox/**`, `**/.venv/**`, `**/venv/**`, `**/build/**`, `**/dist/**`, `**/*.egg-info/**`, `**/node_modules/**`, `**/.idea/**`, `**/.vscode/**`, `**/.gitignore`, `**/.DS_Store`, `**/Thumbs.db`

  Default patterns beginning with `**/` also apply at the target directory root.
  For example, both `.venv/config.txt` and `nested/.venv/config.txt` are omitted.
  Custom patterns retain their existing `fnmatch` matching behavior.

* If both default and custom omit rules are desired, repeat `-o`:

```bash
pylistall -o -o "README.md,test_cases/*"
```

---

### Include binary files

**Optional, disabled by default.**

```bash
-b, --binary [PATTERN]
```

Controls whether binary files are included in content output.
Does not affect non-binary files.
Included bytes are decoded as UTF-8 with replacement; archives, images, and
documents are not converted or extracted.

Precedence rules:

1. `-o` always omits matching files (including binary files).
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

---

### Git log

**Optional, disabled by default.**

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

* Groups are sorted by path (case-insensitive), separated by blank lines.

---

### Limit file read size

**Optional, disabled by default.**

```bash
-m, --max-bytes N
```

Limit the maximum number of bytes read per file.
If content exceeds `N` bytes, it is truncated and marked.

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

Exclude all files that start with `test_` in the `test` folder:

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

Normal collection needs a desktop clipboard backend. The tool does not
automatically exclude secrets or confine symbolic links to the target directory.
Review the files you select before sharing; current boundaries are documented in
[architecture](docs/architecture.md#safety-boundaries-and-current-limitations).

---

## Requirements

Python 3.9 or higher

---

## License

MIT License

## Contributing

See the [development guide](docs/development.md) for setup, checks, builds, and
contribution steps. Product direction is in the [vision](VISION.md); module
responsibilities and data flow are in [architecture](docs/architecture.md).
