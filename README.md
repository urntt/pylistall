# pylistall

[![PyPI version](https://img.shields.io/pypi/v/pylistall.svg)](https://pypi.org/project/pylistall/)
[![Python versions](https://img.shields.io/pypi/pyversions/pylistall.svg)](https://pypi.org/project/pylistall/)
[![License](https://img.shields.io/github/license/urntt/pylistall.svg)](https://github.com/urntt/pylistall)

[中文说明](README.zh-CN.md)

pylistall is a cross-platform CLI for sharing project context with AI assistants,
reviewers, or collaborators. Collect a directory tree, selected file contents and
optional Git history. Display the result, copy Markdown, or save one local file.
Python 3.9 or newer is required.

## Installation

```sh
python -m pip install pylistall
pylistall --help
```

For an unpublished checkout, use `python -m pip install .`. The changes below are
unreleased; published behavior is described in [GitHub Releases](https://github.com/urntt/pylistall/releases).

## Usage

```sh
pylistall [path] [options]
pylistall . -r -o
pylistall . -r -o -c
pylistall . -r -o -f context.md
pylistall . -r -g 3 -d files
pylistall . -r -o -D -M 100000 -f
```

The collection path defaults to the current directory. Default operation displays
the result and does not touch the clipboard. Pipe or redirect output to obtain
Markdown. Status messages and warnings go to stderr.

| Option | Behavior |
| --- | --- |
| `-r --recursive` | Expand directories; otherwise collect immediate files only |
| `-i --include PATTERN` | Restrict contents; repeatable or comma-separated |
| `-o --omit [PATTERN]` | Omit contents; bare `-o` enables the defaults below |
| `-b --binary [PATTERN]` | Include all binaries, or matching binaries only |
| `-m --max-bytes N` | Per-file source-byte limit; mark truncated content |
| `-g --git-log [N]` | All Git commits, or the last N; disabled by default |
| `-l --follow-links` | Follow file and directory links, including external targets |
| `-c --copy` | Additionally copy Markdown while still displaying |
| `-f --file [DEST]` | Save one file and suppress terminal body; may combine with `-c` |
| `-w --overwrite` | Permit replacing an output file; requires `-f` |
| `-d --disable PARTS` | Omit `root`, `tree`, `git`, `files`; repeatable or comma-separated |
| `-D --dry-run` | Collect and report exact Markdown size and destinations without copying/writing |
| `-M --max-output-bytes N` | Positive total Markdown UTF-8 budget; default unlimited |
| `-h --help` | Show help |

At least one output part must remain enabled. Disabling `files` avoids sampling
and reading contents; disabling `git` avoids Git queries. All destinations use the
same enabled parts. Exceeding the total budget returns 1 and delivers no body,
clipboard content or file. The budget includes headings, fences and newlines;
it excludes status messages.

### Filters and links

Patterns match filenames and logical relative paths using `fnmatch`; repeated or
comma-separated values trim whitespace and empty entries. Omission takes priority
over inclusion and binary policy. Explicit `-i` can force binary inclusion. `-b`
affects binaries only. Included bytes are decoded as UTF-8 with replacement, without
extracting archives or interpreting images. Business logs and lock files remain eligible.

Content filters do not hide tree names. Directories end in `/`; links are marked
`@` and skipped by default. `-l` permits targets outside the root, and directory
expansion still requires `-r`. Ancestor cycles and broken followed targets are
skipped with warnings; repeated non-cyclic aliases remain separate. Omit rules
check logical and resolved paths. An explicitly supplied root link is resolved.

Bare `-o` covers these categories at the root and nested levels:

- Git metadata, Python environments/caches, `build`, `dist`, `*.egg-info`,
  `node_modules`, `.idea`, `.vscode`, `.gitignore`, `.DS_Store`, `Thumbs.db`.
- Python/testing: `.nox`, `.hypothesis`, `.ipynb_checkpoints`, `__pypackages__`,
  `.eggs`, `htmlcov`, `.coverage`, `.coverage.*`.
- Frontend: `.next`, `.nuxt`, `.output`, `.svelte-kit`, `.turbo`, `.parcel-cache`,
  `.vite`, `coverage`, `.nyc_output`, `*.tsbuildinfo`, `.eslintcache`, `.stylelintcache`.
- Other generated files: `.cache`, `target`, `.gradle`, `.vs`, `*.swp`, `*.swo`,
  `*~`, `desktop.ini`, `pylistall-output-*.md`.
- Sensitive names: `.env`, `.env.*`, `.envrc`, `.pypirc`, `.netrc`, `id_rsa`,
  `id_dsa`, `id_ecdsa`, `id_ed25519`, `*.key`, `*.pem`, `*.p12`, `*.pfx`,
  `.aws/credentials`, `.streamlit/secrets.toml`.

This list also excludes some examples and public certificates. It cannot detect
arbitrary secrets and does not load `.gitignore`. Custom `-o PATTERN` does not
enable defaults; combine both with `-o -o "custom/*"`. Review collected content
before sharing. See [current boundaries](docs/architecture.md#safety-boundaries-and-current-limitations).

### File destinations

Bare `-f` saves in the **command's current directory**, using the local timestamp
`pylistall-output-%Y-%m-%d-%H-%M-%S.md`. Relative destinations use that same current
directory, independently of the collection root; absolute paths and `~` work too.
An existing directory or trailing platform separator selects a directory with the
default name. Otherwise the argument is the complete filename; no extension is added.

Missing parents are created after successful collection and budget validation.
Existing names, including same-second collisions, fail unless `-w` is supplied.
Files use UTF-8 without BOM and LF; a failed overwrite preserves the original.
The active destination and its aliases are excluded from content even without
`-o`, while an existing name remains in the tree. `-D` previews size/destination
without creating directories, writing files or copying. Failures return nonzero;
stderr reports each completed destination.

### Git history

`-g` discovers `.git` directories and worktree pointer files. Without `-r`, only
the root is checked; recursion groups repositories by absolute path. Each group
uses oneline, decorated logs. Missing repositories, empty logs and Git failures
have explicit markers. Git must be available on PATH.

## Output format

For a directory with `README.txt` and `src/main.py`, `pylistall . -r -o` produces:

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

The absolute root is first. Optional Git groups precede files. Paths are escaped
as literal Markdown; known file types get language tags, unknown types use `text`.
Fence lengths grow to avoid content backtick collisions. Content ordering and
`[...TRUNCATED...]` markers remain visible.

## Migration from 0.3.1

Default clipboard copying becomes default display. Add `-c` to keep copying;
use `-f` to export without displaying the body. `-p --print` is removed: omit it
for display, or replace it with `-c` for display plus copying. Use `-d files` to
omit file names and contents while retaining other parts. `-h` remains help.
Markdown gains headings, language tags and collision-safe fences.

## Clipboard support

Only `-c` needs a working clipboard: macOS uses `pbcopy`, Windows `clip`, and
Linux `xclip` or pyperclip. Default display and file export work without a desktop.

## Contributing and releases

See [development](docs/development.md), [vision](VISION.md), and
[architecture](docs/architecture.md). Changes are tracked in the
[changelog](CHANGELOG.md); maintainers follow [releasing](docs/releasing.md).
The project uses the MIT license.
