# Architecture

[中文](architecture.zh-CN.md)

For maintainers and agents. User options belong in the [README](../README.md),
future requirements in the [vision](../VISION.md), and contributor commands in
[development](development.md).

## Modules and data flow

| Module | Responsibility |
| --- | --- |
| `cli.py` | Validate arguments, orchestrate one collection and independent destinations |
| `patterns.py` | Default omissions, pattern normalization, name and target subtree matching |
| `traversal.py` | Iterative discovery, early pruning, private Git markers, link cycles and diagnostics |
| `tree.py` | Name-filtered tree and connecting ancestors, without content reads |
| `selection.py` | Metadata candidates, one binary classification, structured chunked reads |
| `names.py` | Visible control characters, inline code delimiters and project names |
| `gitlog.py` | Consume private Git entries and stream subprocess output |
| `output.py` | Structured result, language identifiers, Markdown and exact budget |
| `progress.py` | Optional isolated Rich collection and terminal formatting feedback |
| `destinations.py` | Resolve file destinations and perform transactional writes |
| `viewer.py` | Literal Rich rendering from the model and pager transport |
| `util.py` | Platform clipboard transport |

```text
arguments -> shared patterns -> one traversal (omit pruning)
                                  |-> tree name view (include + ancestors)
                                  |-> private Git markers -> Git chunks
                                  |-> metadata candidates -> classification -> read chunks
             optional callbacks -> progress on stderr
             cli -> project + path/tree + Git + Files -> model / Markdown budget
             stop progress -> warnings -> summary or display/file/copy
```

Results remain in memory. Standalone collectors use the same scanner. Title-only
and title/path-only documents validate the root but do not enumerate directories.

## Discovery, filtering and links

The explicit resolved root is exempt from include/omit matching. Children are
matched by name and `/`-separated logical relative path using platform `fnmatch`.
Repeated/comma-separated rules are trimmed and deduplicated. Only bare `-o` enables
defaults; mixing bare and custom omissions takes the union. Default `**/` rules
also derive root variants; custom rules do not. `*.py` matches names at every
level; `src/*.py` can match deeper paths. This is not Git ignore syntax.

Logical omission precedes target checks. A directory's name, relative path or
relative path with trailing `/` can prune it. `src/**` and `src/` prune `src`,
while `src/*.py` does not. Omitted nodes count as discovered; unvisited descendants
do not. `.git` has no permanent hiding rule when omissions are absent.

Include filters file leaves and retains their connecting directories; it neither
prunes scanning nor grants binary permission. With no include rules, all unomitted
structure remains. Tree order is directories first, case-insensitive name with a
case-sensitive tie breaker; Files order uses logical relative paths in the same
case ordering. The tree does not depend on readability or binary expansion.

Links are marked `@` and not inspected beyond link metadata by default. Junctions
are recognized without treating every Windows reparse point as a link. Unfollowed,
broken or uninspectable entries use logical names for tree inclusion. `-l` follows
inside/outside targets; directory expansion still needs `-r`. Ancestor directory
identities cut cycles, while non-cyclic aliases remain distinct logical entries.
Followed targets and omitted directory ancestors are checked against root-relative
paths (absolute on cross-drive targets). This prevents file aliases into omitted
subtrees. An explicitly supplied root link is resolved without `-l`.

## Content and encoding

Candidates are ordinary readable-target files after name filtering and output
identity exclusion, before binary classification. Output targets and symbolic or
hard-link aliases are excluded only from contents, so existing names can remain
in the tree. Files disabled means no sampling or reading.

The extension/NUL/incremental UTF-8/byte-ratio heuristic is preserved. Text expands
normally. Binary expansion needs bare `-b` or a matching binary permission rule;
`-i` cannot grant permission and `-b` cannot add candidates. Unexpanded binaries
retain their heading and a placeholder. Structured blocks distinguish `None`
(unexpanded) from `""` (successfully read empty), encoding, truncation and errors.

The single chunked reader returns an explicit read result. Text uses UTF-8
replacement decoding, LF normalization and the existing in-body truncation marker.
Binary uses standard Base64 with carry across three-byte groups, padding and no
inserted line breaks. `-m` limits original bytes before encoding; the resulting
prefix is decodable and the truncation marker is outside its fence. Failed reads
are visible error blocks, never encoded as binary data. No extraction, decompression
or file format interpretation is performed.

## Git logs

The same scan privately records `.git` directories and ordinary worktree pointers
in visited, unpruned directories. Explicit Git collection can inspect omitted
`.git` metadata without displaying or expanding it. Entire omitted parent subtrees
are not searched. Include and binary permission do not filter Git discovery.
Non-recursive collection checks only the root; recursion allows nested repositories.
Linked markers retain the link policy. Groups sort by resolved absolute `.git`
path and run `git -C <parent> log --oneline --decorate --no-color`, with optional
count. Absent repositories, empty logs and failures retain explicit markers.
No `-g` or disabled Git means no Git subprocess.

## Output and clipboard

`OutputDocument` always has `project_name`; `path/tree/git/files` are optional.
All parts may be disabled. `root` is rejected as a disable name. Project names are
resolved basenames; filesystem roots use `/`, a Windows drive anchor, or UNC share
name. Markdown uses a dynamic inline code title, one combined `bash` path/tree
block, optional `## Git log`, then `## Files`. Enabled empty trees use `(empty)`;
Files always has a heading when enabled, and no candidates use `[No files selected]`.
Git/file subheadings use inline code. Normal characters are literal; control
characters have visible escapes. Delimiters grow beyond backtick runs and use
padding when needed. Body fences are at least three backticks and avoid collisions.
Base64 blocks have an encoding label. Sections use consistent blank lines and LF.

`MarkdownBuilder` counts final UTF-8 bytes, including titles, labels, dynamic fences
and truncation. File/Base64/Git chunks check conservative lower bounds, followed
by exact complete block checks. Excess aborts later processing, closes files and
kills/waits/closes Git. No destination receives a partial body. Dry-run uses the
same collection/accounting, reporting only counts, bytes and destinations.

Rich consumes the model directly, without rereading or parsing Markdown, and
shares language tags. Missing Rich silently falls back. Redirection is ANSI-free
Markdown written to the binary stdout stream as UTF-8/no BOM/LF, independent of
the Python text wrapper's encoding and newline handling; text-only capture streams
receive the same Markdown string. Shell decoding/re-encoding is outside this
transport. Paging requires stdin/stdout TTY and honors `-n`/`PAGER`; less uses `-FRX`
and UTF-8, more uses plain platform encoding. Startup failure displays directly;
normal quit and downstream pipe closure return 0.

File destinations use invocation cwd and one local timestamp, support `~`, preserve
custom names and reject collisions without `-w`. Collection/budget passes before
creating parents or writing UTF-8/no BOM/LF. Exclusive creation cleans failures;
overwrites finish a same-directory temporary file before replacing the original.
A failing destination returns 1 and reports already completed operations without
rolling them back. Only `-c` uses clipboard: UTF-8 pbcopy on macOS, UTF-16LE clip
on Windows, UTF-8 xclip or pyperclip on Linux.

## Progress and cancellation

Feedback is enabled only on stderr TTY, non-dumb TERM and without `-P`; stdout
redirection or `-f/-c/-D` does not disable it. Lazy Rich spinner stages cover scan,
tree and Git with no invented percentages. Files show checked/candidate and
collected counts. Literal paths are clipped; refresh is at most 10 Hz and Rich
stream redirection is disabled. Optional callbacks reuse the index and classification;
feedback adds no scan, sample or read. UI failures disable feedback independently.
Collection feedback stops before warnings and destinations. Interactive display
starts a separate `render` stage while Rich builds the terminal text, reporting the
current path and completed/total blocks (one path/tree introduction plus each Git
and Files entry, including placeholders). It uses the same gates and refresh limit,
performs no collection reads and stops before stdout delivery or pager startup,
including on formatting failure or cancellation. Redirection skips this stage.

- Discovered: enumerated logical children, including omitted nodes, excluding root.
- Candidates: name/link/identity-filtered regular files before binary checks.
- Checked: fully processed candidates including placeholders and failures.
- Collected: successful bodies, including empty files and bounded prefixes.

Aliases count separately. Summary `files` means Files entries, not successful reads;
`collected` reports the latter. Argument/root errors return 2; budget/destination
failures 1; Ctrl+C 130 without traceback. Cancellation cleans progress, readers,
Git and incomplete writes, preserving existing files. Ordinary content failures
remain error blocks rather than global failures.

## Safety boundaries and current limitations

Collection stays local, without uploads or executing collected code. Explicit copy
replaces the clipboard; `-w` permits replacement. Name-based defaults are not secret
detection, exclude some examples/public certificates, and never load `.gitignore`.
Following permits external targets and worktree pointers may reference external
metadata. Traversal is not an atomic snapshot or defense against concurrent path
replacement. Base64 expands size and does not compress or interpret a file.
`-M` limits Markdown rather than total memory or index size; defaults are unlimited.
Git has no runtime timeout. Writes depend on local filesystem semantics. Real
terminal and clipboard integration cannot be inferred from simulated tests.
