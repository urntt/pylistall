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
* Include or omit files using glob patterns (optional, filters both the tree and Files)
* Expand binaries as Base64 and include Git logs (optional, disabled by default)
* Choose output parts, preview collection, and limit total output size
* Terminal headings, colors, code highlighting, and interactive paging
* Collection progress and current operations on interactive stderr
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

Notes:

* The project title is always first; path and tree share one `bash` block,
  followed by optional Git groups and Files.
* `-i` filters file names in the tree and Files, keeping connecting directories.
  `-o` removes matching names and prunes completely omitted directories.
* `-r` controls directory expansion and `-l` controls link following.
* Directories end with `/`; links are marked `@` and skipped by default.
* Headings use inline code with dynamic backticks; control characters are shown
  as visible escapes. Known file types have language tags;
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

Omit `path`, `tree`, `git`, or `files` from every destination. Repeat the option or
use comma-separated values. The project title cannot be disabled; all four parts
may be disabled to output only that title. `root` is no longer accepted.

Disabling `files` avoids sampling and reading file contents; disabling `git`
avoids Git queries. Copying, saving and display use the same enabled parts.

```bash
pylistall -r -g 3 -d files
pylistall -d path,tree -d git -c
```

---

### Include only specific files

**Optional, repeatable, disabled by default.**

```text
-i, --include PATTERN
```

Include only files matching glob patterns. Repeat the option or use comma-separated
patterns; surrounding whitespace, empty entries and duplicates are removed. Matching uses
`fnmatch` against the filename and logical relative path.

When `-i` is used:

* Only matching file names remain in the tree and Files, along with their ancestors.
* Parent directories need not match; `-i` does not prune the scan.
* Matching binary names remain visible but require `-b` to expand their contents.
* Matching omit rules still take precedence.

---

### Omit specific files

**Optional, repeatable, disabled by default.**

```text
-o, --omit [PATTERN]
```

Exclude matching names from the tree and Files. Entire omitted directories are
not scanned. Repeated and comma-separated values are trimmed and deduplicated. Omissions take precedence over `-i` and `-b`,
checking both logical and resolved paths when links are followed.

Bare `-o` enables the default set at the root and nested levels:

* Git metadata, Python environments/caches (including `.venv`), `build`, `dist`, `*.egg-info`,
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
locks are retained. The explicitly selected root itself is exempt from filtering.
Directory rules match their name, relative path, or relative path ending in `/`:
`src`, `src/` and `src/**` prune `src`; `src/*.py` removes matching files without
pruning `src`. Include cannot restore an omitted subtree.

Default patterns beginning with `**/` also apply at the root. Custom patterns keep
ordinary `fnmatch` behavior and do not automatically enable defaults. `*.py` matches file names at every level;
`src/*.py` can also match deeper paths because `fnmatch` treats `/` as an ordinary
character. Custom `**/.venv/**` does not match root `.venv` automatically.
Platform case handling is preserved. To combine:

```bash
pylistall -o -o "README.md,test_cases/*"
```

---

### Include binary files

**Optional, disabled by default.**

```text
-b, --binary [PATTERN]
```

Controls expansion of already selected binary candidates, without adding file
names or changing the tree. `-o` removes names first, then `-i` selects names, and
`-b` grants binary content permission. Text files do not need `-b`.

* Not provided → retain a path heading and a binary placeholder, without a body.
* Bare `-b` → expand all candidate binaries.
* `-b PATTERN` → expand only binary candidates matching filename or logical path.

Authorized bytes use padded Base64 without inserted line breaks, labelled
`Encoding: Base64` in a `text` block. Base64 is neither compression nor file
interpretation. With `-m`, encode the raw prefix; its encoding remains decodable.
Binary `[...TRUNCATED...]` appears outside the code block, and only the prefix
can be restored. Read failures remain visible errors, never encoded error text.

```bash
pylistall -b
pylistall -i "*.png" -b
pylistall -i "*.py" -b "*.png"  # does not add PNG candidates
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
* With `-r`, discover nested repositories in unpruned directories.
* Discovery is independent of `-i`; explicitly requested logs remain available
  when `.git` metadata is omitted. Entire omitted parent directories are skipped.
* Without omissions, `.git` may also appear in the tree and Files as ordinary data.
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
also check resolved targets and their omitted directory ancestors. Ancestor cycles and broken followed targets are
skipped with warnings, while repeated non-cyclic aliases remain separate.
An explicitly supplied root link is resolved even without this option.

---

### Preview collection

**Optional, disabled by default.**

```text
-D, --dry-run
```

Collect accurately and report Markdown UTF-8 bytes, Files entry count, successfully
collected bodies, discovered entries, skips and destinations on stderr. No body is displayed, nothing is copied, and
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
headings, encoding labels, fences and newlines. Colors, progress, summaries and
status messages do not count. This budget is not a total memory limit.
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

### Disable collection progress

**Optional; enabled on interactive stderr unless `TERM=dumb`.**

```text
-P, --no-progress
```

Shows scan, tree and Git operations with a spinner, then checked/candidate and
successfully collected file counts. No percentage is claimed for unknown totals.
Paths are literal and clipped to terminal width; refresh is at most 10 times per
second. Output redirection, `-f`, `-c` and `-D` still allow progress when stderr is
interactive. Redirect stderr or use `-P` to suppress it. This is independent of
`-n`, which controls paging. Feedback is cleared before results or the pager.
Missing or failing progress components quietly disable feedback; Ctrl+C cleans
resources and returns 130.

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
