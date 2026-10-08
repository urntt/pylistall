# pylistall

[![PyPI version](https://img.shields.io/pypi/v/pylistall.svg)](https://pypi.org/project/pylistall/)
[![Python versions](https://img.shields.io/pypi/pyversions/pylistall.svg)](https://pypi.org/project/pylistall/)
[![License](https://img.shields.io/github/license/urntt/pylistall.svg)](https://github.com/urntt/pylistall)

[中文说明](README.zh-CN.md)

`pylistall` is a cross-platform command-line tool that collects file contents under
a directory and displays them in a structured format. It can also copy Markdown
to the system clipboard or export it to a single file.

It includes the absolute path and a tree-style directory structure. If the
directory contains a `.git` repository, it can optionally include the Git commit log.

This tool is designed for efficiently sharing project context with AI tools,
debugging, documentation, or code review.

---

## Features

* Display collected context in the terminal by default
* Copy Markdown to the clipboard or save it to a single file (optional)
* Tree-style directory structure and absolute root path
* Recursive traversal of subdirectories (optional, disabled by default)
* Include or omit files using glob patterns (optional, includes non-binary files by default)
* Include binary files and Git logs (optional, disabled by default)
* Choose output parts, preview collection, and limit total output size
* Terminal headings, colors, code highlighting, and interactive paging
* Cross-platform support: macOS, Windows, and Linux

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

By default, the result is displayed without changing the clipboard. Interactive
terminals use headings, colors and syntax highlighting without Markdown fences
or line numbers. Pipes and redirection receive Markdown without added ANSI.
Status messages and warnings go to stderr.

---

## Output Format

Example input for a directory containing `README.txt` and `src/main.py`:

```bash
cd /Users/example/project
pylistall . -r -o -c
```

Example clipboard text (file export and redirection use the same Markdown):

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

Notes:

* The root is first, followed by the tree, optional Git groups, and file contents.
* The tree reflects the filesystem; content filters do not hide tree names.
* `-r` controls directory expansion and `-l` controls link following.
* Directories end with `/`; links are marked `@` and skipped by default.
* Markdown paths are escaped literally. Known file types have language tags;
  unknown types use `text`. Fences grow to avoid backtick collisions.
* Content ordering and `[...TRUNCATED...]` markers remain visible.

---

## Options

### Recursive traversal

**Optional, disabled by default.**

```text
-r, --recursive
```

Recursively include subdirectories. When enabled:

* The tree includes nested files and directories.
* Content collection includes matching files in nested directories.
* Git discovery checks nested repositories when `-g` is also enabled.

---

### Copy output to clipboard

**Optional, disabled by default.**

```text
-c, --copy
```

Additionally copy the complete Markdown to the clipboard. The terminal still
displays the result unless `-f` is supplied. Only this option needs a working
clipboard backend.

---

### Save output to a file

**Optional, disabled by default.**

```text
-f, --file [DEST]
```

Save all enabled output parts to one file and suppress the terminal body.
Combine with `-c` to save and copy the same Markdown.

Destination rules:

* Bare `-f` saves in the **command's current directory** using local time:
  `pylistall-output-%Y-%m-%d-%H-%M-%S.md`.
* Relative paths use that same current directory, independently of the collection
  root. Absolute paths and `~` are supported.
* An existing directory or trailing platform separator selects a directory with
  the default filename. Otherwise `DEST` is the complete filename.
* Custom filenames do not receive an automatic extension.
* Missing parents are created after collection and budget validation succeed.
* Existing names and same-second collisions fail unless `-w` is provided.
* Files use UTF-8 without BOM and LF. Failed overwrites preserve the original.
* The active destination and its aliases are excluded from contents even without
  `-o`; existing names may still appear in the tree.

Failures return nonzero, and stderr reports each completed destination.

Examples:

```bash
pylistall -r -o -f
pylistall -r -o -f context.md
pylistall -r -o -f ../exports/context -c
```

---

### Overwrite an output file

**Optional, disabled by default; requires `-f`.**

```text
-w, --overwrite
```

Allow replacing an existing output file. A directory cannot be overwritten as a
file. Replacement occurs after a same-directory temporary file is fully written;
failure cleans the incomplete file and preserves the original.

```bash
pylistall -r -o -f context.md -w
```

---

### Disable output parts

**Optional, repeatable, disabled by default.**

```text
-d, --disable PARTS
```

Omit `root`, `tree`, `git`, or `files` from every destination. Repeat the option or
use comma-separated values. At least one active output part must remain enabled.

Disabling `files` avoids sampling and reading file contents; disabling `git`
avoids Git queries. Copying, saving and display use the same enabled parts.

```bash
pylistall -r -g 3 -d files
pylistall -d root,tree -d git -c
```

---

### Include only specific files

**Optional, repeatable, disabled by default.**

```text
-i, --include PATTERN
```

Include only files matching glob patterns. Repeat the option or use comma-separated
patterns; surrounding whitespace and empty entries are ignored. Matching uses
`fnmatch` against the filename and logical relative path.

When `-i` is used:

* Only matching files are included in content output.
* Matching binary files can be included even without `-b`.
* Matching omit rules still take precedence.

---

### Omit specific files

**Optional, repeatable, disabled by default.**

```text
-o, --omit [PATTERN]
```

Exclude contents matching glob patterns. Repeated and comma-separated values are
trimmed; empty entries are ignored. Omissions take precedence over `-i` and `-b`,
checking both logical and resolved paths when links are followed.

Bare `-o` enables the default set at the root and nested levels:

* Git metadata, Python environments/caches, `build`, `dist`, `*.egg-info`,
  `node_modules`, `.idea`, `.vscode`, `.gitignore`, `.DS_Store`, `Thumbs.db`.
* Python/testing: `.nox`, `.hypothesis`, `.ipynb_checkpoints`, `__pypackages__`,
  `.eggs`, `htmlcov`, `.coverage`, `.coverage.*`.
* Frontend: `.next`, `.nuxt`, `.output`, `.svelte-kit`, `.turbo`, `.parcel-cache`,
  `.vite`, `coverage`, `.nyc_output`, `*.tsbuildinfo`, `.eslintcache`, `.stylelintcache`.
* Other generated files: `.cache`, `target`, `.gradle`, `.vs`, `*.swp`, `*.swo`,
  `*~`, `desktop.ini`, `pylistall-output-*.md`.
* Sensitive names: `.env`, `.env.*`, `.envrc`, `.pypirc`, `.netrc`, `id_rsa`,
  `id_dsa`, `id_ecdsa`, `id_ed25519`, `*.key`, `*.pem`, `*.p12`, `*.pfx`,
  `.aws/credentials`, `.streamlit/secrets.toml`.

The list also excludes some examples and public certificates. It cannot detect
arbitrary secrets and does not load `.gitignore`. Business logs and dependency
locks are retained. Excluding contents leaves names visible in the tree.

Default patterns beginning with `**/` also apply at the root. Custom patterns keep
ordinary `fnmatch` behavior and do not automatically enable defaults. To combine:

```bash
pylistall -o -o "README.md,test_cases/*"
```

---

### Include binary files

**Optional, disabled by default.**

```text
-b, --binary [PATTERN]
```

Controls binary inclusion without affecting text files. Included bytes are decoded
as UTF-8 with replacement; archives, images and documents are not converted or extracted.

Precedence rules:

1. `-o` always omits matching files, including binaries.
2. `-i` can force-include specific binaries.
3. `-b` controls only remaining binaries.

Inclusion rules:

* Not provided → binaries excluded, unless forced by `-i`.
* Bare `-b` → include all binaries.
* `-b PATTERN` → include matching binaries only.

```bash
pylistall -b
pylistall -b "*.zip,photo.png"
pylistall -i "run.exe"
```

---

### Git log

**Optional, disabled by default.**

```text
-g, --git-log [N]
```

Include Git history. Bare `-g` includes all entries; `-g N` includes the last N
entries, where N must be positive.

Rules:

* Without `-r`, check only the root `.git` directory or worktree pointer file.
* With `-r`, discover nested repositories.
* Groups are sorted by absolute `.git` path, case-insensitively.
* Logs use oneline and decorate; Markdown groups have path subheadings.
* Missing repositories, empty logs and Git failures have explicit markers.
* Git must be available on PATH. `-d git` suppresses Git queries and output.

---

### Limit file read size

**Optional, unlimited by default.**

```text
-m, --max-bytes N
```

Limit source bytes read per file. N must be nonnegative. Contents exceeding the
limit receive `[...TRUNCATED...]`. This does not limit the tree or Git logs.

---

### Follow links

**Optional, disabled by default.**

```text
-l, --follow-links
```

Follow file and directory links, including targets outside the root. Directory
expansion still requires `-r`. Contents use logical relative paths; omit rules
also check resolved targets. Ancestor cycles and broken followed targets are
skipped with warnings, while repeated non-cyclic aliases remain separate.
An explicitly supplied root link is resolved even without this option.

---

### Preview collection

**Optional, disabled by default.**

```text
-D, --dry-run
```

Collect accurately and report Markdown UTF-8 bytes, selected file count, skipped
entries and destinations on stderr. No body is displayed, nothing is copied, and
no directories or files are created. Combine with `-c` or `-f` to preview them.

```bash
pylistall -r -o -D -c -f context.md
```

---

### Limit total output size

**Optional, unlimited by default.**

```text
-M, --max-output-bytes N
```

Set a positive UTF-8 byte budget for the complete enabled Markdown, including
headings, fences and newlines. Colors, summaries and status messages do not count.
Exceeding the budget returns 1 and delivers no partial terminal body, clipboard
content or file. Dry-run reports the same size as actual Markdown.

---

### Disable terminal paging

**Optional; paging is automatic in interactive terminals.**

```text
-n, --no-pager
```

Paging requires both stdin and stdout to be terminals. `PAGER` takes priority;
otherwise pylistall looks for `less`, including Git for Windows' bundled executable,
then system `more`. Less defaults to `-FRX`: short output exits automatically,
Space advances, `/` searches and `q` quits. An empty `PAGER` also disables paging.
Configured commands use executable/arguments without shell expansion.

Missing or failed pagers display directly. More receives plain platform-encoded
text; characters unavailable in the current Windows codepage may be replaced.
Rich import failures silently fall back to Markdown. Clipboard and file outputs
always remain Markdown. See [Git's pager defaults](https://git-scm.com/docs/git-config#Documentation/git-config.txt-corepager).

---

### Help

```text
-h, --help
```

Display the command's usage and available options.

---

## Examples

Basic usage:

```bash
pylistall
```

Recursively collect with default omissions and three recent Git commits:

```bash
pylistall -r -o -g 3
```

Copy context or save it to a file:

```bash
pylistall -r -o -c
pylistall -r -o -f context.md
```

Include only Python files, or omit test files:

```bash
pylistall -i "*.py"
pylistall -o "test/test_*"
```

Preview destinations with a total budget:

```bash
pylistall -r -o -D -M 100000 -c -f context.md
```

---

## Clipboard Support

Platform-specific clipboard backends:

| Platform | Backend |
| --- | --- |
| macOS | `pbcopy` |
| Windows | `clip` |
| Linux | `xclip` / `pyperclip` |

Only `-c` needs a working desktop clipboard. Display and file export work without
one. Review selected content before sharing; current boundaries are documented in
[architecture](docs/architecture.md#safety-boundaries-and-current-limitations).

---

## Requirements

Python 3.9 or higher. Git is required only when collecting Git history.

---

## License

MIT License

## Contributing

See the [development guide](docs/development.md) for setup, checks, builds, and
contribution steps. Product direction is in the [vision](VISION.md); module
responsibilities and data flow are in [architecture](docs/architecture.md).

## Releases

See the [changelog](CHANGELOG.md) for version changes and migration notes, and
[GitHub Releases](https://github.com/urntt/pylistall/releases) for published versions.
Maintainers use the [release guide](docs/releasing.md).
