# Product vision

[中文](VISION.zh-CN.md)

This document defines product direction for maintainers and contributors. See the
[README](README.md) for usage, [architecture](docs/architecture.md) for implemented
behavior and boundaries, and [development](docs/development.md) for the workflow.

## Users and core purpose

pylistall helps developers share a small project's context with an AI assistant,
reviewer, or collaborator. One local command collects a directory tree, selected
file contents, and optional Git history into text ready to paste from the clipboard.
The recipient should be able to understand where files live and read their contents
without opening each file separately.

It also serves debugging and documentation tasks that need the same context. The
project remains a lightweight clipboard CLI, with no account, hosted service, or
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
binary inclusion, and a per-file read limit. Content filters do not hide tree
entries. The [architecture document](docs/architecture.md) describes the actual
matching, encoding, failure behavior, and current safety limitations.

The repository provides behavior tests, uv dependency locking, Ruff checks, CI for
the minimum and default Python versions on three platforms, and bilingual
contributor guidance. These foundations enable developers and agents to
continue work from a fresh checkout without relying on a previous conversation.

## Next priorities

These are future requirements, not current guarantees:

1. Build a reviewed release workflow on top of CI, with artifact verification and
   automated publishing.
2. Define and implement safer collection boundaries: sensitive-file exclusions,
   a consistent symlink policy with cycle detection, and clearer error reporting.
   Decide how filename visibility in the tree should interact with these controls.
3. Control total output volume and provide a useful preview, beyond the current
   per-file limit. Design a stdout-only mode for environments without a clipboard.
4. Refine filtering and everyday usability using real projects and regression
   evidence, with explicit migration notes for behavior changes.

A GUI, cloud synchronization, content execution, and direct AI requests are outside
the current direction. Reconsider scope only when a concrete user need justifies it.
