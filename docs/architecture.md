# Architecture

[中文](architecture.zh-CN.md)

This document describes the current implementation for maintainers and agents.
Future requirements belong in the [vision](../VISION.md), user options in the
[README](../README.md), and commands in the [development guide](development.md).

## Modules and data flow

| Module | Responsibility | Result or side effect |
| --- | --- | --- |
| `cli.py` | Parse arguments, validate the root, normalize options, assemble output | `OutputResult` with text, file count, and warnings |
| `tree.py` | Traverse and render the real filesystem tree | Tree text independent of content filters |
| `selection.py` | Normalize patterns, select files, detect binary content, read and render contents | Content text and selected file count |
| `gitlog.py` | Discover `.git` entries and run Git logs | Log groups and warnings |
| `util.py` | Choose a clipboard backend and send text | Writes to the system clipboard |

```text
arguments -> cli: validate root and construct options
                 |-> tree: traverse -> sort -> render
                 |-> gitlog (optional): discover .git -> git log -> group
                 |-> selection: enumerate -> filter -> read -> render
             cli: assemble root + tree + logs + contents
                 -> optional stdout preview -> clipboard -> confirmation
```

The modules traverse independently. An omitted content path can still appear in
the tree and does not prevent Git discovery. There is no shared traversal index or
streaming output pipeline.

## Directory tree

Without recursion, `tree.py` lists immediate children, including unexpanded
directories. With recursion, it constructs nested `TreeEntry` values and renders
them with tree connectors. Directories precede files; names are sorted without
case sensitivity and directories have a trailing `/`. `-r` controls expansion;
include, omit, and binary options do not affect the tree.

Directory enumeration errors are currently treated as an empty list. Directory
classification follows links, and recursive tree construction has no cycle guard.

## Content selection and reading

`selection.py` uses `iterdir()` for shallow collection and `rglob("*")` for
recursive file discovery. Patterns are matched with `fnmatch` against both the
filename and a relative path with `/` separators. Repeated/comma-separated values
are normalized by trimming whitespace and dropping empty entries. Platform
case-normalization follows `fnmatch`; matching is not Git ignore syntax.

Selection proceeds as follows:

1. If an include list exists, keep only matching files.
2. Omit matching files, even if an include or binary option would select them.
3. Classify binary content. A matching explicit include can force its inclusion;
   otherwise the binary policy must allow it. Text files do not need `-b`.
4. Sort selected files by display name without case sensitivity, then read and
   render each file.

Bare `-o` opts into the default omit set. Root variants are derived from defaults
starting with `**/`; custom patterns keep ordinary `fnmatch` behavior. For example,
custom `**/.venv/**` does not match root-level `.venv/config.txt`. `.git/**` targets
the root Git directory, not every nested repository. `.gitignore` is not loaded.

Binary detection first checks known extensions, then reads a bounded byte sample
plus one byte of lookahead. NUL bytes imply binary content. Strict incremental
UTF-8 decoding accepts a character split by sampling, but checks incomplete EOF;
on decode failure, a non-text-byte ratio heuristic decides. This is a heuristic,
not validation of the entire file. An unreadable sample is classified as binary.

Reads decode UTF-8 with replacement. Binary inclusion therefore produces decoded
text, not archive extraction or image/document interpretation. A per-file limit
uses one extra byte to detect truncation and adds `[...TRUNCATED...]`. Read errors
become `[Failed to read file: ...]` blocks; the count describes selected files,
including any failed reads.

## Git logs

Without `-r`, only the root `.git` entry is considered. Recursive mode searches
for `.git` directories and files, including worktree-style pointer files. Each
entry's parent is used as the repository root for `git -C ... log --oneline
--decorate`, with an optional count. Groups are sorted by absolute path without
case sensitivity and prefixed with the absolute `.git` path.

Missing entries produce `[No .git found]` during assembly. Empty logs and subprocess
failures produce text markers. Git must be available on PATH when logs are requested;
no Git Python library is required. Recursive discovery errors currently discard
discovered entries instead of reporting detailed traversal failures.

## Output and clipboard

`cli.py` writes the absolute root path first, outside a ten-backtick tree fence.
An empty tree uses `(empty)` instead. Optional Git groups follow, then content
blocks labelled with relative paths and ten-backtick fences. The final text ends
with one newline. The [README example](../README.md#output-format) shows this format.
Fixed fences are not escaped if a file contains the same delimiter.

`-p` prints the assembled text before copying; it is not a stdout-only mode.
Clipboard transport uses UTF-8 `pbcopy` on macOS, UTF-16LE `clip` on Windows, and
UTF-8 `xclip -selection clipboard` followed by a pyperclip fallback on other
platforms. Clipboard failures propagate; the CLI does not yet provide a dedicated
headless fallback or uniform friendly error handling. Invalid target paths print
an error and return status 2 before any copy attempt.

## Safety boundaries and current limitations

The application reads local files, runs Git and clipboard programs with argument
lists, and assembles text in memory. It does not upload data or execute collected
file contents. Copying replaces the user's clipboard contents; users decide where
to paste the result.

- There is no automatic secret detection or sensitive-file exclusion. Hidden text
  files can be collected; default omissions require bare `-o` and do not establish
  a sensitive-data boundary. Excluding content also leaves filenames in the tree.
- There is no consistent symlink containment policy. File links can expose content
  outside the selected root; directory links in the tree can escape it or loop.
  Content discovery may behave differently across Python versions. Do not claim
  that collection is confined to the root.
- There is no total output budget. Files are unlimited by default, the existing
  limit is per file, and the tree and logs are unbounded. Negative byte limits are
  not explicitly rejected. Large inputs can consume substantial memory.
- A desktop clipboard backend is required for normal use, including `-p`. Help
  and mocked tests do not need a desktop session.

These gaps remain open product work. A change addressing one must define its
behavior, update both language versions and regression coverage, and account for
the independently generated tree, logs, and contents.
