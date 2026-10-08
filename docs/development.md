# Development

[中文](development.zh-CN.md)

This is the contributor workflow for developers and agents. Start with
[AGENTS.md](../AGENTS.md), the [vision](../VISION.md), and the relevant
[architecture](architecture.md) sections. User installation and options belong
in the [README](../README.md).

## Repository layout

```text
pylistall/
├── AGENTS.md / CLAUDE.md       agent rules / import of those rules
├── README*.md                 user guides
├── CHANGELOG*.md              bilingual version changes
├── VISION*.md                 product direction
├── docs/                      development and architecture, in both languages
├── .github/                   CI workflow and bilingual pull request template
├── src/pylistall/              CLI, tree, selection, Git logs, clipboard
├── tests/                     behavior and regression tests
├── scripts/                   unified checks, CI matrix and wheel smoke test
├── pyproject.toml             metadata, dependencies, build and check configuration
├── MANIFEST.in                contributor resources included in the source package
├── uv.lock                    resolved runtime and development dependencies
└── .python-version            default development interpreter
```

## Environment setup

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) outside the
project virtual environment. This workflow was validated with uv 0.12.23. From a
fresh checkout, use the same commands in PowerShell, macOS, or Linux:

```sh
uv sync --locked
uv run --locked python --version
uv run --locked pylistall --help
```

uv creates `.venv`, installs the project in editable mode, and includes the `dev`
dependency group. Activation and manual pip installation are unnecessary. uv can
download the interpreter if it is not available locally.

[.python-version](../.python-version) pins the default development interpreter to
Python 3.14.3. Package support remains defined by `requires-python` in
[pyproject.toml](../pyproject.toml), currently Python 3.9 and above. Use compatible
syntax and standard-library APIs throughout the supported range.

The former, unpublished `dev` extra has been replaced by `[dependency-groups].dev`.
It contains pytest, Ruff, and Twine and is not exposed as an installation extra.
Ordinary users continue to install with pip; development tools are not runtime
dependencies. `uv.lock` records versions and Python/platform-specific resolutions.
`--locked` rejects a stale lock instead of silently updating it.

## Run and check changes

Run the CLI through the locked environment:

```sh
uv run --locked pylistall --help
uv run --locked pylistall . -r -o -i "*.py"
```

The second command replaces the clipboard; use a disposable fixture when checking
collected output. `-p` also requires a clipboard. See
[architecture limitations](architecture.md#safety-boundaries-and-current-limitations)
before testing against unfamiliar directories.

The required check entry point is:

```sh
uv run --locked python scripts/check.py
```

It runs Ruff lint, Ruff format verification, and pytest, in that order, with the
active Python interpreter. It stops at the first failure and returns a nonzero
status. The script locates the repository root itself; configuration lives in
`pyproject.toml`. Ruff targets Python 3.9, uses an 88-character line width, and
checks `E4`, `E7`, `E9`, `F`, and `I`, including import ordering.

Apply intentional formatting and import fixes, then rerun the entry point:

```sh
uv run --locked ruff check . --fix
uv run --locked ruff format .
uv run --locked python scripts/check.py
```

When checking Python compatibility, run the same checks on the minimum supported
version, then restore the default environment:

```sh
uv run --locked --python 3.9 python scripts/check.py
uv sync --locked
```

This temporarily changes the project's `.venv` interpreter. Tests currently cover
the CLI behavior baseline for selection, binary precedence, UTF-8 boundaries, read limits, directory
trees, CLI output and errors, Git grouping, and clipboard backend selection. They
use temporary directories and mock clipboard programs, pyperclip, and Git log
retrieval. They do not modify the real clipboard or require a desktop session.
Backend mocks verify commands and encodings, not actual OS integration.
Release tests also cover rejection of mixed artifacts, inconsistent metadata,
missing notes, invalid tags, and changed remote hashes without network uploads.

The baseline fixes include normalized include patterns, default omissions at the
root and nested levels, incremental UTF-8 sampling, and Python 3.9-compatible
dataclasses. No known-defect tests currently use `xfail`. Keep strict expected
failure handling; any temporary marker needs a reason and removal plan. New
regressions must fail normally.

## Build and verify artifacts

The build backend remains setuptools. From the repository root:

```sh
uv build
uv run --locked python -m twine check dist/*
uv run --locked python scripts/smoke_wheel.py
```

`uv build` creates both a wheel and a source distribution in `dist/`, building the
wheel from the source distribution by default. Use a new output directory for a
verification run (`uv build --out-dir dist/verify-1`) and check only its artifacts
to avoid mixing old releases. The version comes from `pyproject.toml`; validation
does not require a version bump. Isolated build dependencies follow
`[build-system].requires`; they are separate from the project dependency lock.
`MANIFEST.in` includes the contributor docs, lock, scripts, and workflow definitions
in source distributions, so the included release tests retain their dependencies.

The [wheel smoke test](../scripts/smoke_wheel.py) expects exactly one wheel and one
source distribution. It creates a temporary environment inside `.pytest_cache`,
installs the wheel, verifies that imports come from that environment, compares its
metadata with the development installation, and runs the installed CLI's help.
The environment is removed afterward. For a separate build directory, pass it as
an argument: `uv run --locked python scripts/smoke_wheel.py dist/verify-1`.

For a full repository check, repeat setup, help, unified checks, build, metadata
checks, and wheel installation in a separate fresh clone with no existing `.venv`.
Use a disposable clone to check minimum-Python compatibility too.

### Metadata and badges

The project uses an SPDX license expression and explicitly includes `LICENSE`;
the setuptools lower bound supports this metadata format on Python 3.9. Runtime
dependencies and Python support remain in `pyproject.toml`; development dependency
groups are not wheel extras.

Python classifiers list the boundary versions covered by CI, currently 3.9 and
3.14. They do not replace `requires-python`. Shields' PyPI Python-version badge
reads the classifiers of the published package, not `Requires-Python` or this
checkout. A metadata change appears there only after a release and cache refresh;
verify the badge when publishing before restoring it to the README.

## Lock maintenance

After an intentional dependency change in `pyproject.toml`:

```sh
uv lock
uv sync --locked
uv run --locked python scripts/check.py
```

Review and commit `pyproject.toml` and `uv.lock` together. To intentionally upgrade
a package, use `uv lock --upgrade-package pytest`; use `uv lock --upgrade` only
when all dependency updates are in scope. Inspect conditional versions for the
minimum Python too. `uv lock --check` verifies freshness without accepting changes.
Do not edit resolved lock entries manually or replace `--locked` with `--frozen`
to bypass an inconsistent project configuration.

## Contribution workflow

1. Reproduce the issue or define the intended behavior. Read related tests and
   authoritative documentation before changing the implementation.
2. Create a purpose-named branch under the [Git rules](../AGENTS.md#git-与提交).
   Preserve existing history, author settings, and unrelated user changes.
3. Make a focused change and add meaningful behavior coverage when needed. Update
   related English and Chinese docs in the same change. Keep configuration in its
   authoritative file and link to it elsewhere.
4. Review `git diff`, run the unified checks, and report tested interpreters,
   platform scope, and limitations. Commit using English Conventional Commits.
5. Push the authorized branch and open a pull request using the
   [template](../.github/pull_request_template.md). Review the full diff and require
   the latest revision's `CI` check to pass before merging. Humans and agents use
   the same checks; local success does not replace the GitHub result.

## Continuous integration

[The CI workflow](../.github/workflows/ci.yml) runs on pushes, pull requests, and
manual dispatches. Actions are pinned to commit SHAs and uv is pinned to the
validated tool version. Jobs start from fresh checkouts and use `uv sync --locked`.

[The matrix helper](../scripts/ci_matrix.py) reads the minimum Python from installed
project metadata and the default interpreter from `.python-version`. Each runs
CLI help and the unified checks on Windows, Linux, and macOS. If the Python support
constraint changes shape, update the parser as part of that change. Passing these
tests validates platform commands through mocks; it does not test a real desktop
clipboard.

After all six checks pass, Linux packaging jobs for both Python versions build a
wheel and source distribution, run Twine and the isolated wheel smoke test, and
retain the artifacts for seven days. They do not publish them. The final `CI` job
fails if any required job fails, is cancelled, or is skipped, giving branch
protection one stable check name.

The `main` branch requires a pull request and the `CI` check, including for admins,
with the branch current against `main`. No additional approving reviewer is required
for this single-maintainer repository. Review and merge only the tested revision;
if the branch changes or is updated against `main`, wait for its new CI run.

## Completion and release gates

A change is ready locally when relevant bilingual documents and links are correct,
the lock is current, unified checks pass, and the diff contains only intended
changes. Python compatibility changes must pass the minimum and default versions.
Packaging changes must also pass fresh-checkout setup, help, wheel/source builds,
Twine metadata checks, and isolated wheel installation. State what was verified;
do not describe mocked clipboard tests as real platform validation.

Before a release, require these checks, an intentional version decision, matching
artifact metadata, and consistent release notes and tag. Review the exact artifacts
to publish and ensure old files are not included. The latest revision must pass CI;
the [release guide](releasing.md) defines service setup, tag preparation, TestPyPI
verification, production approval, and failure handling. Version bumps, remote
pushes, release tags, and uploads are separate, explicitly authorized tasks.
