# Architecture

[中文](architecture.zh-CN.md)

For maintainers and agents. User options belong in the [README](../README.md),
future requirements in the [vision](../VISION.md), and contributor commands in
[development](development.md).

## Modules and data flow

| Module | Responsibility |
| --- | --- |
| `cli.py` | Validate arguments, collect once and assemble `OutputResult` |
| `traversal.py` | Iterative filesystem traversal, link classification, ancestor cycles and diagnostics |
| `tree.py` | Render the shared entries independently of content filters |
| `selection.py` | Normalize patterns, select, classify and read files |
| `gitlog.py` | Find repositories in the shared entries and collect Git logs |
| `util.py` | Platform clipboard transport |

```text
arguments -> cli -> traversal: one shared index
                     |-> tree: sort and render
                     |-> gitlog (optional): discover .git -> Git -> group
                     |-> selection: filter -> sample -> read -> render
                cli: root + tree + Git + files
                     -> optional stdout preview -> clipboard -> status
```

Standalone collector calls use the same scanner. Content omissions leave tree
names visible and do not filter Git discovery. Results are assembled in memory.

## Directory tree

An explicit stack scans each expanded logical directory once. Directories precede
files, sorted by case-insensitive name with a case-sensitive tie breaker. Tree
rendering uses another stack. `-r` controls expansion; content filters do not hide
names. Links are marked `@` and skipped by default, without inspecting targets.
Only symlink and junction reparse tags are links, not every Windows reparse point.

`-l` follows file and directory links, including external targets; directories
still need `-r`. Directory identities are compared against the current ancestor
chain, stopping cycles while preserving separate non-cyclic aliases. The explicit
root is resolved even without `-l`. Broken followed links and inaccessible nested
entries remain visible with warnings. Root enumeration failures are fatal.

## Content selection and reading

Only regular files from the shared index are candidates; special files are never
opened. `fnmatch` checks filenames and logical relative paths with `/` separators.
Repeated and comma-separated patterns are trimmed; empty items are removed.
Platform case-normalization follows `fnmatch`, not Git ignore syntax.

Include patterns restrict candidates. Omit patterns take precedence over include
and binary policies, checking both logical paths and resolved target names/paths.
Bare `-o` enables defaults at the root and nested levels; custom patterns keep
ordinary `fnmatch` behavior and do not enable defaults. The [README](../README.md)
describes cache, generated-file and sensitive-name categories. `.gitignore` is not
loaded. Business logs and dependency locks remain eligible.

Binary detection checks known extensions, then a bounded sample and lookahead.
NUL implies binary. Incremental strict UTF-8 decoding tolerates a character split
at the sampling boundary but validates EOF. A non-text-byte ratio is the fallback;
an unreadable sample is binary. Explicit include can force binary inclusion;
otherwise `-b` must allow it. This heuristic does not validate an entire file.

Selected files are sorted by logical display path and decoded as UTF-8 with
replacement. A per-file byte limit uses lookahead and `[...TRUNCATED...]`; errors
become `[Failed to read file: ...]` blocks. Binary inclusion does not extract or
interpret archives, images or documents.

## Git logs

Shared entries identify `.git` directories and ordinary worktree pointer files.
Linked `.git` entries require `-l`. Without `-r`, discovery is root-only. Groups
are sorted by absolute path and run `git -C <parent> log --oneline --decorate`,
optionally with a count. Nested traversal failures retain previously found repos.
Missing Git entries, empty logs and subprocess failures use explicit markers.
Git must be on PATH when requested; no Git library is used.

## Output and clipboard

The absolute root is first, followed by the tree in a ten-backtick fence, optional
Git groups and relative-path-labelled contents in ten-backtick fences. Empty trees
use `(empty)`. Output ends with a newline. Fixed fences currently do not escape
delimiter collisions. See the [example](../README.md#output-format).

`-p` prints before copying. macOS uses UTF-8 `pbcopy`, Windows UTF-16LE `clip`, and
Linux UTF-8 `xclip -selection clipboard` or pyperclip. Invalid roots return 2;
collection errors return 1. Clipboard failures still propagate.

## Safety boundaries and current limitations

Collection is local. The program does not upload data or execute collected code.
Copying replaces the user's clipboard; users decide where to paste.

- Bare `-o` is optional name-based exclusion, not secret detection. It can exclude
  examples and public certificates and leaves tree names visible.
- Links are skipped by default; explicit `-l` permits external targets. Worktree
  pointer files may reference external Git metadata. Traversal is not an atomic
  filesystem snapshot or protection against concurrent path replacement.
- Total output is unlimited. `-m` limits individual files, not trees or Git logs;
  negative limits are not yet rejected. Large inputs can consume memory.
- Normal operation, including `-p`, needs a desktop clipboard backend. Mocked
  tests are not desktop integration checks.

Future changes must update both language versions and account for the shared
tree, Git and content result.
