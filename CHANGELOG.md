# Changelog

[中文](CHANGELOG.zh-CN.md)

Changes are grouped by the version prepared for release. Publication status and
dates are recorded in [GitHub Releases](https://github.com/urntt/pylistall/releases).
Maintainers follow the [release guide](docs/releasing.md).

## [Unreleased]

### Changed

- Share iterative discovery across the tree, file selection, and Git lookup.
- Show links without reading them by default; `-l / --follow-links` opts into
  targets inside or outside the root, with ancestor cycle detection.
- Expand opt-in default omissions for nested Git metadata, caches, generated
  output, and common credential filenames. Omitted names remain in the tree.

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
