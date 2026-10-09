"""File selection and content rendering for pylistall."""

from __future__ import annotations

import base64
import codecs
import io
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator, Optional

from pylistall.patterns import (
    flatten_patterns,
    matches_name,
    omitted,
    target_omitted,
)
from pylistall.traversal import TraversalResult, scan_directory

BINARY_SAMPLE_BYTES = 8192

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


def parse_binary_policy(
    raw_binary: Optional[str],
) -> BinaryPolicy:
    """Parse '-b/--binary' policy.

    raw_binary:
    - None: binary body expansion disabled
    - ""  : binary enabled for all binaries
    - str : binary enabled with whitelist patterns
    """
    if raw_binary is None:
        return BinaryPolicy(enabled=False, patterns=tuple())

    if raw_binary == "":
        return BinaryPolicy(enabled=True, patterns=tuple())

    return BinaryPolicy(enabled=True, patterns=flatten_patterns([raw_binary]))


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


@dataclass(frozen=True)
class ReadResult:
    text: str
    encoding: str
    truncated: bool = False
    error: Optional[str] = None


def read_content(
    path: Path,
    max_bytes: Optional[int],
    check_size: Optional[Callable[[int], None]] = None,
    chunk_bytes: int = 4096,
    *,
    binary: bool = False,
    report: Optional[Callable[..., None]] = None,
) -> ReadResult:
    """Read a raw prefix; stream either UTF-8 replacement text or padded Base64."""
    decoder = io.IncrementalNewlineDecoder(
        codecs.getincrementaldecoder("utf-8")(errors="replace"), translate=True
    )
    chunks: list[str] = []
    size = consumed = 0
    carry = b""
    truncated = False
    if check_size is not None:
        check_size(0)
    try:
        with path.open("rb") as handle:
            while True:
                remaining = (
                    chunk_bytes
                    if max_bytes is None
                    else min(chunk_bytes, max_bytes - consumed)
                )
                if remaining == 0:
                    truncated = bool(handle.read(1))
                    break
                data = handle.read(remaining)
                if not data:
                    break
                consumed += len(data)
                if binary:
                    joined = carry + data
                    complete = len(joined) // 3 * 3
                    text = base64.b64encode(joined[:complete]).decode("ascii")
                    carry = joined[complete:]
                else:
                    text = decoder.decode(data, final=False)
                chunks.append(text)
                size += len(text.encode("utf-8"))
                if check_size is not None:
                    check_size(size)
                if report is not None:
                    report("files", str(path))
    except OSError as exc:
        return ReadResult(f"[Failed to read file: {exc}]", "utf-8", error=str(exc))
    tail = (
        base64.b64encode(carry).decode("ascii")
        if binary
        else decoder.decode(b"", final=True)
    )
    if truncated and not binary:
        tail += "\n\n[...TRUNCATED...]\n"
    chunks.append(tail)
    if check_size is not None:
        check_size(size + len(tail.encode("utf-8")))
    return ReadResult("".join(chunks), "Base64" if binary else "utf-8", truncated)


def read_text(
    path: Path,
    max_bytes: Optional[int],
    check_size: Optional[Callable[[int], None]] = None,
    chunk_bytes: int = 4096,
) -> str:
    """Convenience text reader backed by the single structured reading implementation."""
    return read_content(path, max_bytes, check_size, chunk_bytes).text


def _is_included(
    filename: str,
    rel_str: str,
    include_patterns: tuple[str, ...],
) -> bool:
    """Check include patterns against filename and relative path."""
    if not include_patterns:
        return True
    return matches_name(filename, rel_str, include_patterns)


def _is_omitted(
    filename: str,
    rel_str: str,
    omit_patterns: tuple[str, ...],
) -> bool:
    """Check omit patterns against filename and relative path."""
    if not omit_patterns:
        return False
    return omitted(filename, rel_str, omit_patterns)


def binary_allowed(
    filename: str,
    rel_str: str,
    policy: BinaryPolicy,
) -> bool:
    """Return True if binary is allowed by -b policy (independent of name inclusion)."""
    if not policy.enabled:
        return False
    if not policy.patterns:
        return True
    return matches_name(filename, rel_str, policy.patterns)


def iter_selected_files(
    root: Path,
    selection: SelectionOptions,
    *,
    snapshot: Optional[TraversalResult] = None,
    excluded: Optional[Path] = None,
) -> Iterator[SelectedFile]:
    """Select name-matching candidates without sampling or expanding contents."""
    if snapshot is None:
        snapshot = scan_directory(
            root, selection.recursive, selection.follow_links, omit=selection.omit
        )
    root = snapshot.root
    excluded_target = excluded.resolve() if excluded is not None else None
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
            if entry.path == excluded or file_path == excluded_target:
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
        if target_omitted(file_path, root, selection.omit):
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
    *,
    snapshot: Optional[TraversalResult] = None,
    excluded: Optional[Path] = None,
) -> list[SelectedFile]:
    """Materialize selection for callers that need the complete candidate list."""
    return list(
        iter_selected_files(root, selection, snapshot=snapshot, excluded=excluded)
    )
