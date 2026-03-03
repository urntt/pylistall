"""File selection and content rendering for pylistall."""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Sequence


DEFAULT_OMIT_PATTERNS: tuple[str, ...] = (
    # Git
    ".git/**",
    # Python caches / tooling
    "**/__pycache__/**",
    "**/.pytest_cache/**",
    "**/.mypy_cache/**",
    "**/.ruff_cache/**",
    "**/.tox/**",
    # Virtual envs
    "**/.venv/**",
    "**/venv/**",
    # Build artifacts
    "**/build/**",
    "**/dist/**",
    "**/*.egg-info/**",
    # JS
    "**/node_modules/**",
    # IDE
    "**/.idea/**",
    "**/.vscode/**",
    # Common single files
    "**/.gitignore",
    "**/.DS_Store",
    "**/Thumbs.db",
)

BINARY_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".bmp",
        ".ico",
        ".pdf",
        ".zip",
        ".rar",
        ".7z",
        ".tar",
        ".gz",
        ".bz2",
        ".xz",
        ".exe",
        ".dll",
        ".so",
        ".dylib",
        ".bin",
        ".dat",
        ".class",
        ".jar",
        ".pyc",
        ".pyo",
        ".woff",
        ".woff2",
        ".ttf",
        ".otf",
        ".mp3",
        ".wav",
        ".flac",
        ".mp4",
        ".mov",
        ".mkv",
        ".avi",
        ".doc",
        ".docx",
    }
)


@dataclass(frozen=True, slots=True)
class SelectionOptions:
    """Options for selecting and reading file contents."""

    recursive: bool
    include: tuple[str, ...]
    omit: tuple[str, ...]
    max_bytes: Optional[int]


@dataclass(frozen=True, slots=True)
class BinaryPolicy:
    """Binary inclusion policy."""

    enabled: bool
    patterns: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SelectedFile:
    """Represents a file selected for content output."""

    absolute_path: Path
    relative_path: Path
    display_name: str


def flatten_patterns(items: Sequence[str]) -> tuple[str, ...]:
    """Flatten repeated and comma-separated patterns into a single tuple."""
    patterns: list[str] = []
    for item in items:
        for part in item.split(","):
            part = part.strip()
            if part:
                patterns.append(part)
    return tuple(patterns)


def parse_omit_patterns(raw_omit: Sequence[str]) -> tuple[str, ...]:
    """Parse omit patterns, supporting '-o' without a value for defaults."""
    enable_default = any(item == "" for item in raw_omit)
    user_items = [item for item in raw_omit if item != ""]
    user_patterns = flatten_patterns(user_items)

    if enable_default:
        return tuple(DEFAULT_OMIT_PATTERNS) + tuple(user_patterns)
    return tuple(user_patterns)


def parse_binary_policy(
    raw_binary: Optional[str],
) -> BinaryPolicy:
    """Parse '-b/--binary' policy.

    raw_binary:
    - None: binary disabled (except binaries forced by -i)
    - ""  : binary enabled for all binaries
    - str : binary enabled with whitelist patterns
    """
    if raw_binary is None:
        return BinaryPolicy(enabled=False, patterns=tuple())

    if raw_binary == "":
        return BinaryPolicy(enabled=True, patterns=tuple())

    return BinaryPolicy(enabled=True, patterns=flatten_patterns([raw_binary]))


def matches_any(target: str, patterns: Iterable[str]) -> bool:
    """Return True if target matches any glob pattern."""
    return any(fnmatch.fnmatch(target, pattern) for pattern in patterns)


def _rel_string(root: Path, path: Path) -> str:
    """Get a stable, posix-style relative string for matching and display."""
    return path.relative_to(root).as_posix()


def is_probably_binary(path: Path) -> bool:
    """Heuristically determine whether a file is binary.

    Strategy:
    - Fast check by extension.
    - Byte sampling: NUL byte or high ratio of non-text bytes.
    """
    if path.suffix.lower() in BINARY_EXTENSIONS:
        return True

    try:
        with path.open("rb") as handle:
            sample = handle.read(8192)
    except OSError:
        # If we cannot read it safely, treat it as binary.
        return True

    if not sample:
        return False

    if b"\x00" in sample:
        return True

    printable = set(range(32, 127))
    allowed_whitespace = {9, 10, 12, 13}  # \t, \n, \f, \r
    bad_count = 0

    for byte in sample:
        if byte in printable or byte in allowed_whitespace:
            continue
        bad_count += 1

    return (bad_count / max(1, len(sample))) > 0.30


def read_text(path: Path, max_bytes: Optional[int]) -> str:
    """Read file content as UTF-8 text, replacing undecodable bytes."""
    try:
        with path.open("rb") as handle:
            if max_bytes is None:
                data = handle.read()
            else:
                data = handle.read(max_bytes + 1)
    except OSError as exc:
        return f"[Failed to read file: {exc}]"

    truncated = False
    if max_bytes is not None and len(data) > max_bytes:
        data = data[:max_bytes]
        truncated = True

    text = data.decode("utf-8", errors="replace")
    if truncated:
        text += "\n\n[...TRUNCATED...]\n"
    return text


def iter_files(root: Path, recursive: bool) -> Iterable[Path]:
    """Iterate files under root (non-recursive by default)."""
    if recursive:
        for item in root.rglob("*"):
            if item.is_file():
                yield item
        return

    for item in root.iterdir():
        if item.is_file():
            yield item


def _is_included(
    filename: str,
    rel_str: str,
    include_patterns: tuple[str, ...],
) -> bool:
    """Check include patterns against filename and relative path."""
    if not include_patterns:
        return True
    return matches_any(filename,
                       include_patterns) or matches_any(rel_str,
                                                        include_patterns)


def _is_omitted(
    filename: str,
    rel_str: str,
    omit_patterns: tuple[str, ...],
) -> bool:
    """Check omit patterns against filename and relative path."""
    if not omit_patterns:
        return False
    return matches_any(filename,
                       omit_patterns) or matches_any(rel_str,
                                                     omit_patterns)


def _binary_allowed_by_b(
    filename: str,
    rel_str: str,
    policy: BinaryPolicy,
) -> bool:
    """Return True if binary is allowed by -b policy (excluding -i force)."""
    if not policy.enabled:
        return False
    if not policy.patterns:
        return True
    return matches_any(filename,
                       policy.patterns) or matches_any(rel_str,
                                                       policy.patterns)


def select_files_for_content(
    root: Path,
    selection: SelectionOptions,
    binary_policy: BinaryPolicy,
) -> list[SelectedFile]:
    """Select files for content output based on -i/-o/-b and binary rules."""
    selected: list[SelectedFile] = []

    for file_path in iter_files(root, selection.recursive):
        rel_str = _rel_string(root, file_path)
        filename = file_path.name

        included = _is_included(filename, rel_str, selection.include)
        if not included:
            continue

        if _is_omitted(filename, rel_str, selection.omit):
            continue

        is_binary = is_probably_binary(file_path)
        if is_binary:
            # Priority: -i can force-include binaries even without -b.
            if selection.include and included:
                pass
            else:
                if not _binary_allowed_by_b(filename, rel_str, binary_policy):
                    continue

        display = rel_str if selection.recursive else filename
        selected.append(
            SelectedFile(
                absolute_path=file_path,
                relative_path=file_path.relative_to(root),
                display_name=display,
            )
        )

    selected.sort(key=lambda item: item.display_name.lower())
    return selected


def build_content_sections(
    root: Path,
    selection: SelectionOptions,
    binary_policy: BinaryPolicy,
) -> tuple[str, int]:
    """Build file content blocks and return them with file count."""
    selected = select_files_for_content(root=root,
                                        selection=selection,
                                        binary_policy=binary_policy)
    if not selected:
        return ("", 0)

    chunks: list[str] = []
    for item in selected:
        content = read_text(item.absolute_path, max_bytes=selection.max_bytes)
        chunks.append(f"`{item.display_name}`:\n")
        chunks.append("```\n")
        chunks.append(f"{content}\n")
        chunks.append("```\n\n")

    return ("".join(chunks).rstrip() + "\n", len(selected))
