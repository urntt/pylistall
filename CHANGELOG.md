# Changelog

[中文](CHANGELOG.zh-CN.md)

Changes are grouped by the version prepared for release. Publication status and
dates are recorded in [GitHub Releases](https://github.com/urntt/pylistall/releases).
Maintainers follow the [release guide](docs/releasing.md).

## [Unreleased]

### Changed

- Filter both tree names and Files with `-i/-o`; prune omitted directories before
  scanning. The explicit root is exempt. Preserve `fnmatch` and bare/custom omission rules.
- Discover Git independently of includes and omitted metadata, within unpruned directories.
- Separate binary name selection from body permission: `-i` no longer grants binary
  expansion. Unexpanded binaries retain a heading and placeholder; authorized
  bytes use padded Base64, with raw-byte limits and an external truncation marker.
- Always show an inline-code project title; combine path/tree in a `bash` block.
  Use dynamic inline code for paths and visible control characters.
- Rename disable part `root` to `path` and permit disabling all four parts.
- Add `-P --no-progress`, stderr collection stages and accurate file counters,
  without changing paging. Clean cancellation returns 130.

### Fixed

- Write redirected Markdown as UTF-8/LF even with GBK or ASCII Python stdio,
  preventing Unicode/emoji crashes and preserving bytes before shell processing.
- Show terminal formatting progress during syntax highlighting instead of leaving
  a blank wait after collection; clear it before display/paging and honor `-P`.

### Migration from 1.0.0

- Replace `-d root` with `-d path`; old `root` is an argument error. Disabling all
  parts now emits just the project title without scanning.
- Includes now hide unrelated tree names; omissions hide/prune matching entries.
  A deep include cannot restore an omitted parent. Bare `-o` prunes root/nested `.venv`.
- Add `-b` when binary bodies are required, even with `-i`. Binary candidates no
  longer disappear silently; expect headings/placeholders and Base64 rather than
  UTF-8 replacement bytes. Binary truncation markers are outside the encoded block.
- Update Markdown consumers for project title, combined path/tree and inline-code
  names. Progress is on stderr; use `-P` to suppress it independently of `-n`.
- Summary `files` counts Files entries; `collected` counts successful bodies.

Version and dependencies remain unchanged; these changes are not yet released.

## [1.0.0]

### Added

- Add `-c --copy` for explicit clipboard copying and `-f --file [DEST]` for
  UTF-8/LF file export. Resolve relative destinations from the invocation
  directory, generate local-time filenames, and exclude the output and its aliases
  from content collection. Reject existing files unless `-w --overwrite` is set;
  failed overwrites preserve the original.
- Add `-d --disable` to omit root, tree, Git, or files across every destination.
  Disabled file contents and Git logs are not read.
- Add `-D --dry-run` summaries and exact Markdown byte limits with
  `-M --max-output-bytes`. Stream file and Git reads, stop on overflow, and deliver
  no partial result.
- Add Rich terminal headings and syntax highlighting, with literal paths and
  content. Missing Rich silently falls back to Markdown.
- Add `-n --no-pager` and interactive pagination through `PAGER`, less, Git bundled
  less on Windows, or more. Handle Unicode, normal pager exit, and closed pipes.
- Promote the already locked Rich 15.0.0 to a runtime dependency without upgrading
  other packages.

### Changed

- Display results by default instead of copying them. Interactive terminals use
  the styled viewer; redirection, file export, and copying use Markdown.
- Generate grouped Markdown from one structured result, with language identifiers,
  escaped paths, and fences longer than any backtick sequence in the content.
- Share iterative discovery across the tree, file selection, and Git lookup.
- Show links without reading them by default; `-l / --follow-links` opts into
  targets inside or outside the root, with ancestor cycle detection.
- Expand opt-in default omissions for nested Git metadata, caches, generated
  output, and common credential filenames. Omitted names remain in the tree.

### Removed

- Remove `-p --print`; displaying results is now the default.

### Migration from 0.3.1

- Add `-c` to commands that should continue copying. Omit the old `-p` to display
  results, or replace it with `-c` to display and copy:

  ```bash
  # 0.3.1: display and copy
  pylistall . -r -o -p
  # 1.0.0: display and copy
  pylistall . -r -o -c
  ```

- Use `-f` to save the complete Markdown instead of displaying the terminal body;
  combine it with `-c` to save and copy. Use `-d files` to suppress file headings
  and contents while retaining the other enabled sections. `-h` remains help.
- Update consumers of Markdown to account for section headings, escaped paths,
  language identifiers, and dynamic fences.
- Links are now shown with `@` and skipped by default. Add `-l` to read linked
  targets, including targets outside the root; linked directories also require
  `-r` to expand.
- Review the expanded bare `-o` defaults if collecting examples or public
  certificates. Custom `-o PATTERN` still replaces the default omissions. The
  defaults cannot detect arbitrary secrets and do not load `.gitignore`.

## [0.3.1]

### Fixed

- Normalize comma-separated and repeated include patterns, including whitespace.
- Apply default omissions to root-level directories as well as nested directories.
- Recognize valid UTF-8 when the binary-detection sample ends inside a character.
- Restore the declared Python 3.9 compatibility by removing dataclass slots.

### Changed

- Use longer Markdown fences for directory trees, file contents, and Git logs.
- Use SPDX license metadata and list the Python boundary versions checked by CI.

### Development

- Add regression tests, uv locking, Ruff checks, and bilingual agent and contributor
  documentation.
- Add three-platform CI, PR templates, protected merges, and a release workflow
  that verifies the same artifacts through TestPyPI before PyPI.

## [0.3.0] - 2026-03-03

- Split the CLI into tree, selection, Git-log, and clipboard modules.
- Show the real filesystem tree independently of content filtering, with `/` on
  directory names.
- Add default omissions, binary whitelists, `-p`, and the `-m` alias.
- Clarify omit/include/binary precedence and group logs by absolute `.git` paths.

## [0.2.1] - 2026-02-22

- Combine root-path and directory-tree output into one structure.
- Improve the message when Git logs are requested without a `.git` entry.

## [0.2.0]

- Initial public release: clipboard collection, directory trees, recursive
  traversal, content filters, binary inclusion, and optional Git logs.
