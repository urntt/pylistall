# Product vision

[中文](VISION.zh-CN.md)

This document defines product direction for maintainers and contributors. See the
[README](README.md) for usage, [architecture](docs/architecture.md) for implemented
behavior and boundaries, and [development](docs/development.md) for the workflow.

## Users and core purpose

pylistall helps developers share a small project's context with an AI assistant,
reviewer, or collaborator. One local command collects a directory tree, selected
file contents, and optional Git history into Markdown ready to inspect, save or copy.
The recipient should be able to understand where files live and read their contents
without opening each file separately.

It also serves debugging and documentation tasks that need the same context. The
project remains a lightweight local context CLI, with no account, hosted service, or
AI provider integration required.

## Design principles

- Keep the common workflow short, with explicit options for recursion, filtering,
  binary inclusion, and history.
- Make selection and output understandable. Preserve observable behavior through
  regression tests and document deliberate changes.
- Keep collection local. Improve control over what users share without promising
  protections the implementation does not provide.
- Support the declared Python range and platform clipboard backends, with few
  runtime dependencies and a reproducible contributor environment.
- Maintain small modules with clear responsibilities. Add abstractions and tools
  when they solve a demonstrated need.

## Present scope

The CLI already produces an absolute root path, filesystem tree, file content
blocks, and optional Git log groups. It supports include/omit patterns, explicit
binary inclusion, a per-file read limit, enabled-part controls, dry-run summaries and exact total Markdown budgets. Content filters do not hide tree
entries. The [architecture document](docs/architecture.md) describes the actual
matching, encoding, failure behavior, and current safety limitations.

Tree, content, and Git discovery share an iterative scan. Links are displayed
without being followed by default; explicit following permits external targets
and detects ancestor cycles. Bare `-o` adds common sensitive filenames to its
omissions, while retaining names in the tree; this is not automatic secret detection.

The repository provides behavior tests, uv dependency locking, Ruff checks, CI for
the minimum and default Python versions on three platforms, and bilingual
contributor guidance. These foundations enable developers and agents to
continue work from a fresh checkout without relying on a previous conversation.
The release workflow has completed a real release through TestPyPI, PyPI, and
GitHub Releases, including index hash and installation verification. Service
configuration and future releases follow the [release guide](docs/releasing.md).

## Next priorities

These are future requirements, not current guarantees:

1. Refine omissions and diagnostics using real collection cases; keep the limits
   of name-based sensitive-file filtering explicit.
2. Improve interactive terminal presentation and paging while retaining canonical
   Markdown for sharing and headless operation.
3. Refine filtering and everyday usability using real projects and regression
   evidence, with explicit migration notes for behavior changes.

A GUI, cloud synchronization, content execution, and direct AI requests are outside
the current direction. Reconsider scope only when a concrete user need justifies it.
