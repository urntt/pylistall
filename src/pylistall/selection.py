"""File selection and content rendering for pylistall."""

from __future__ import annotations

import codecs
import fnmatch
import io
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Iterator, Optional, Sequence

from pylistall.traversal import TraversalResult, scan_directory

BINARY_SAMPLE_BYTES = 8192

DEFAULT_OMIT_PATTERNS: tuple[str, ...] = (
    # Git
    "**/.git",
    "**/.git/**",
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
    # Additional tooling and name-based sensitive omissions.
    "**/.nox/**",
    "**/.hypothesis/**",
    "**/.ipynb_checkpoints/**",
    "**/__pypackages__/**",
    "**/.eggs/**",
    "**/htmlcov/**",
    "**/.coverage",
    "**/.coverage.*",
    "**/.next/**",
    "**/.nuxt/**",
    "**/.output/**",
    "**/.svelte-kit/**",
    "**/.turbo/**",
    "**/.parcel-cache/**",
    "**/.vite/**",
    "**/coverage/**",
    "**/.nyc_output/**",
    "**/*.tsbuildinfo",
    "**/.eslintcache",
    "**/.stylelintcache",
    "**/.cache/**",
    "**/target/**",
    "**/.gradle/**",
    "**/.vs/**",
    "**/*.swp",
    "**/*.swo",
    "**/*~",
    "**/desktop.ini",
    "**/pylistall-output-*.md",
    "**/.env",
    "**/.env.*",
    "**/.envrc",
    "**/.pypirc",
    "**/.netrc",
    "**/id_rsa",
    "**/id_dsa",
    "**/id_ecdsa",
    "**/id_ed25519",
    "**/*.key",
    "**/*.pem",
    "**/*.p12",
    "**/*.pfx",
    "**/.aws/credentials",
    "**/.streamlit/secrets.toml",
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


@dataclass(frozen=True)
class SelectionOptions:
    """Options for selecting and reading file contents."""

    recursive: bool
    include: tuple[str, ...]
    omit: tuple[str, ...]
    max_bytes: Optional[int]
    follow_links: bool = False


@dataclass(frozen=True)
class BinaryPolicy:
    """Binary inclusion policy."""

    enabled: bool
    patterns: tuple[str, ...]


@dataclass(frozen=True)
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
        # fnmatch requires a prefix for **/. Derive root variants from the
        # default rules while preserving custom pattern matching semantics.
        root_patterns = tuple(
            pattern.removeprefix("**/")
            for pattern in DEFAULT_OMIT_PATTERNS
            if pattern.startswith("**/")
        )
        return DEFAULT_OMIT_PATTERNS + root_patterns + user_patterns
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


def is_probably_binary(path: Path) -> bool:
    """Heuristically determine whether a file is binary.

    Strategy:
    - Fast check by extension.
    - Byte sampling:
      1. NUL byte check.
      2. Strict incremental UTF-8 decode check, allowing a split sample tail.
      3. Fallback non-text byte ratio check.
    """
    if path.suffix.lower() in BINARY_EXTENSIONS:
        return True

    try:
        with path.open("rb") as handle:
            data = handle.read(BINARY_SAMPLE_BYTES + 1)
    except OSError:
        # If we cannot read it safely, treat it as binary.
        return True

    sample = data[:BINARY_SAMPLE_BYTES]
    if not sample:
        return False

    if b"\x00" in sample:
        return True

    try:
        # Only defer an incomplete trailing character if there is more data.
        # At EOF, incomplete sequences must still fail strict decoding.
        decoder = codecs.getincrementaldecoder("utf-8")(errors="strict")
        decoder.decode(sample, final=len(data) <= BINARY_SAMPLE_BYTES)
        return False
    except UnicodeDecodeError:
        pass

    printable = set(range(32, 127))
    allowed_whitespace = {9, 10, 12, 13}  # \t, \n, \f, \r
    bad_count = 0

    for byte in sample:
        if byte in printable or byte in allowed_whitespace:
            continue
        bad_count += 1

    return (bad_count / max(1, len(sample))) > 0.30


def read_text(
    path: Path,
    max_bytes: Optional[int],
    check_size: Optional[Callable[[int], None]] = None,
    chunk_bytes: int = 4096,
) -> str:
    """Decode bounded chunks, retaining single-file truncation semantics."""
    decoder = io.IncrementalNewlineDecoder(
        codecs.getincrementaldecoder("utf-8")(errors="replace"), translate=True
    )
    chunks: list[str] = []
    size = 0
    consumed = 0
    truncated = False
    try:
        with path.open("rb") as handle:
            while True:
                remaining = (
                    chunk_bytes
                    if max_bytes is None
                    else min(chunk_bytes, max_bytes - consumed)
                )
                data = handle.read(remaining)
                if not data:
                    if max_bytes == 0:
                        truncated = bool(handle.read(1))
                    break
                consumed += len(data)
                text = decoder.decode(data, final=False)
                chunks.append(text)
                size += len(text.encode("utf-8"))
                if check_size is not None:
                    check_size(size)
                if max_bytes is not None and consumed == max_bytes:
                    truncated = bool(handle.read(1))
                    break
    except OSError as exc:
        return f"[Failed to read file: {exc}]"
    tail = decoder.decode(b"", final=True)
    if truncated:
        tail += "\n\n[...TRUNCATED...]\n"
    chunks.append(tail)
    if check_size is not None:
        check_size(size + len(tail.encode("utf-8")))
    return "".join(chunks)


def _is_included(
    filename: str,
    rel_str: str,
    include_patterns: tuple[str, ...],
) -> bool:
    """Check include patterns against filename and relative path."""
    if not include_patterns:
        return True
    return matches_any(filename, include_patterns) or matches_any(
        rel_str, include_patterns
    )


def _is_omitted(
    filename: str,
    rel_str: str,
    omit_patterns: tuple[str, ...],
) -> bool:
    """Check omit patterns against filename and relative path."""
    if not omit_patterns:
        return False
    return matches_any(filename, omit_patterns) or matches_any(rel_str, omit_patterns)


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
    return matches_any(filename, policy.patterns) or matches_any(
        rel_str, policy.patterns
    )


def iter_selected_files(
    root: Path,
    selection: SelectionOptions,
    binary_policy: BinaryPolicy,
    *,
    snapshot: Optional[TraversalResult] = None,
    excluded: Optional[Path] = None,
) -> Iterator[SelectedFile]:
    """Select files for content output based on -i/-o/-b and binary rules."""
    if snapshot is None:
        snapshot = scan_directory(root, selection.recursive, selection.follow_links)
    root = snapshot.root
    for entry in sorted(
        snapshot.entries,
        key=lambda item: (
            item.relative_path.as_posix().lower(),
            item.relative_path.as_posix(),
        ),
    ):
        if not entry.is_file or entry.skipped is not None:
            continue
        file_path = entry.resolved_path
        assert file_path is not None
        if excluded is not None:
            if entry.path == excluded or file_path == excluded.resolve():
                continue
            try:
                if file_path.samefile(excluded):
                    continue
            except OSError:
                pass
        rel_str = entry.relative_path.as_posix()
        filename = entry.path.name

        included = _is_included(filename, rel_str, selection.include)
        if not included:
            continue

        if _is_omitted(filename, rel_str, selection.omit):
            continue
        try:
            target_relative = Path(os.path.relpath(file_path, root)).as_posix()
        except ValueError:
            target_relative = file_path.as_posix()
        if _is_omitted(file_path.name, target_relative, selection.omit):
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
        yield SelectedFile(
            absolute_path=file_path,
            relative_path=entry.relative_path,
            display_name=display,
        )


def select_files_for_content(
    root: Path,
    selection: SelectionOptions,
    binary_policy: BinaryPolicy,
    *,
    snapshot: Optional[TraversalResult] = None,
    excluded: Optional[Path] = None,
) -> list[SelectedFile]:
    """Materialize selection for callers that need the complete candidate list."""
    return list(
        iter_selected_files(
            root, selection, binary_policy, snapshot=snapshot, excluded=excluded
        )
    )
