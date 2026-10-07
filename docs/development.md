# Development

[中文](development.zh-CN.md)

This guide covers local setup and behavior tests. User-facing
usage belongs in [README.md](../README.md). Agent instructions belong in
[AGENTS.md](../AGENTS.md).

## Local setup

Use a Python version supported by `requires-python` in [pyproject.toml](../pyproject.toml).
The implementation preserves the declared Python 3.9 compatibility by using
dataclasses without the Python 3.10-only `slots` option. When checking support,
run the suite on the declared minimum version as well as the current development
interpreter.

Create an isolated environment from the repository root:

```sh
python -m venv .venv
```

On Windows PowerShell, activation is optional. Run the environment's interpreter
directly to avoid execution-policy configuration:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
```

On macOS or Linux:

```sh
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest
```

The editable install uses this checkout. The `dev` extra installs pytest; normal
package installation does not add testing dependencies. Dependency locking and
automated CI are subsequent workflow steps.

## Test boundaries

Tests live in `tests/` and create isolated temporary directories. They cover file
selection, binary inclusion precedence, UTF-8 detection, read limits, directory
trees, CLI output and errors, Git log grouping, and clipboard backend selection.

CLI tests capture clipboard calls. Clipboard backend tests mock external programs
and pyperclip, and Git grouping tests substitute log retrieval. The suite never
changes the real clipboard or requires desktop clipboard software. Backend mocks
verify command selection and encoding, not real operating-system integration.

The tests describe intended observable behavior, including the existing choice to
show the real filesystem tree independently of content filters. Exact output
assertions are limited to small examples where formatting is the behavior under
test.

## Regression coverage

The three defects identified in the initial baseline are fixed. Their temporary
`xfail` markers have been removed, and the tests now pass normally:

- Repeated and comma-separated `-i` values use the same pattern normalization as
  the other filtering options, including trimming whitespace and empty entries.
- Default omit patterns also cover tooling files at the directory root. Root
  variants are derived from the existing default patterns; custom pattern
  matching and tree output retain their existing behavior.
- UTF-8 sampling uses strict incremental decoding. A byte of lookahead determines
  whether a trailing partial character came from sampling or from an incomplete
  file. The sample size remains bounded; invalid bytes inside the sample still
  reach the binary heuristic.

No known-defect tests currently use `xfail`. Keep `xfail_strict` enabled so any
future temporary marker requires removal when its underlying defect is fixed.
New regressions must fail normally and be addressed at their cause.
