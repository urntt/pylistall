# Architecture

[中文](architecture.zh-CN.md)

For maintainers and agents. User options belong in the [README](../README.md),
future requirements in the [vision](../VISION.md), and contributor commands in
[development](development.md).

## Modules and data flow

| Module | Responsibility |
| --- | --- |
| `cli.py` | Validate arguments, collect once and deliver `OutputResult` |
| `traversal.py` | Iterative filesystem traversal, link classification, ancestor cycles and diagnostics |
| `tree.py` | Render the shared entries independently of content filters |
| `selection.py` | Normalize patterns, select, classify and read files |
| `gitlog.py` | Find repositories in the shared entries and collect Git logs |
| `output.py` | Structured model, Markdown and total budget |
| `destinations.py` | File paths and transactional writes |
| `viewer.py` | Literal Rich terminal rendering and pager transport |
| `util.py` | Platform clipboard transport |

```text
arguments -> cli -> traversal: one shared index
                     |-> tree: sort and render
                     |-> gitlog (optional): discover .git -> Git -> group
                     |-> selection: filter -> sample -> read -> render
                cli: root + tree + Git + files
                     -> Markdown display / file / optional copy -> stderr status
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

`OutputDocument` holds optional root/tree/Git/file blocks, warnings and skip counts.
`output.py` owns language identification, path escaping and canonical formatting.
Fences are at least three backticks and longer than any content run. The root is
first; tree, Git and files have group headings and paths have subheadings. LF
normalization and truncation markers are shared; destinations never reread files.

`MarkdownBuilder` counts canonical UTF-8 bytes. File and Git reads decode chunks,
check a conservative body lower bound, then exactly check complete dynamic fences.
On excess, collection aborts; Git is killed, waited on and its pipe closed. Delivery
only begins after the whole budget passes. Total size is unlimited by default.
Disabled files avoid sampling/reading; disabled Git avoids subprocesses. Dry-run
collects exactly and reports size, skips and destinations on stderr without writes.

Default display uses Rich on a TTY and Markdown on redirection; `-c` additionally
copies Markdown and `-f` suppresses the body. `viewer.py` consumes the same model
and language tags, lazily imports Rich and silently falls back on ImportError.
Text/Syntax render literal data, with no line numbers or Markdown fences.
Paging requires both streams to be terminals and honors `-n` and `PAGER`.
Less defaults to `-FRX` and UTF-8; system more uses plain platform-encoded text.
Pager startup failures display directly; normal quits and closed pipes are harmless.
`destinations.py` calculates one local timestamp per invocation, resolves relative
paths from invocation cwd and excludes the target and symbolic/hard-link aliases.
New files use exclusive creation and cleanup on failure; overwrites complete a
same-directory temporary before replacement, preserving originals on failure.
Output is UTF-8 without BOM and LF. Parents are created after collection/budget
validation. Directories cannot be overwritten as files. Each destination reports
completed operations on stderr; any failed destination returns 1.

Only copying needs desktop transport: UTF-8 pbcopy on macOS, UTF-16LE clip on
Windows, UTF-8 xclip or pyperclip on Linux. Argument/root errors return 2 and budget
or delivery errors return 1. Closed downstream pipes exit normally. See the
[migration](../README.md#migration-from-031) for removal of `-p`.

## Safety boundaries and current limitations

Collection is local, without uploading data or executing collected code. Copying
replaces the clipboard; explicit `-w` permits file replacement. Default display
and export work headlessly. Clipboard tests still use mocks.

- Bare `-o` is name-based omission, not secret detection; it excludes some examples
  and public certificates while tree names remain visible.
- `-l` allows external targets; worktree pointers can reference external metadata.
  Traversal is not an atomic snapshot or protection against concurrent replacement.
- `-M` limits final Markdown, not the directory index or total memory. Defaults
  remain unlimited; `-m` applies to individual files only.
- Git execution has no time limit. Unreadable contents use error markers. Concurrent
  filesystem changes can alter subsequent commands; temporary writes and replacement
  depend on local filesystem semantics.
