"""Discover filesystem entries once, with consistent link and cycle handling."""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class FilesystemEntry:
    """A logical entry and its optional resolved, readable target."""

    path: Path
    relative_path: Path
    resolved_path: Optional[Path]
    is_dir: bool
    is_file: bool
    is_link: bool
    skipped: Optional[str] = None


@dataclass(frozen=True)
class TraversalResult:
    """Shared discovery data for the tree, selection, and Git collectors."""

    root: Path
    entries: tuple[FilesystemEntry, ...]
    warnings: tuple[str, ...]


def _identity(path: Path, info: os.stat_result) -> tuple:
    """Prefer filesystem identity, falling back to the canonical path."""
    if info.st_ino:
        return (info.st_dev, info.st_ino)
    return (os.path.normcase(str(path)),)


def _is_link(info: os.stat_result) -> bool:
    """Recognize symlinks and junctions, without excluding cloud placeholders."""
    return stat.S_ISLNK(info.st_mode) or getattr(info, "st_reparse_tag", 0) in {
        getattr(stat, "IO_REPARSE_TAG_SYMLINK", -1),
        getattr(stat, "IO_REPARSE_TAG_MOUNT_POINT", -2),
    }


def scan_directory(
    root: Path, recursive: bool, follow_links: bool = False
) -> TraversalResult:
    """Scan iteratively; only the current ancestor chain forbids aliases."""
    root = root.resolve(strict=True)
    entries: list[FilesystemEntry] = []
    warnings: list[str] = []
    pending = [(root, frozenset({_identity(root, root.stat())}))]
    while pending:
        directory, ancestors = pending.pop()
        paths: list[Path] = []
        try:
            with os.scandir(directory) as children:
                for child in children:
                    paths.append(directory / child.name)
        except OSError as exc:
            if directory == root:
                raise
            warnings.append(f"Failed to list directory {directory}: {exc}")
        descend = []
        for path in sorted(paths, key=lambda item: (item.name.lower(), item.name)):
            relative = path.relative_to(root)
            is_link = False
            try:
                info = path.lstat()
                is_link = _is_link(info)
                if is_link and not follow_links:
                    entries.append(
                        FilesystemEntry(
                            path, relative, None, False, False, True, "link"
                        )
                    )
                    continue
                target = path.resolve(strict=True)
                info = target.stat()
                is_dir = stat.S_ISDIR(info.st_mode)
                is_file = stat.S_ISREG(info.st_mode)
                identity = _identity(target, info)
                skipped = None if is_dir or is_file else "special-file"
                if recursive and is_dir and identity in ancestors:
                    skipped = "cycle"
                    warnings.append(f"Skipped directory cycle: {path}")
                entries.append(
                    FilesystemEntry(
                        path, relative, target, is_dir, is_file, is_link, skipped
                    )
                )
                if recursive and is_dir and skipped is None:
                    descend.append((path, ancestors | {identity}))
            except (OSError, RuntimeError) as exc:
                entries.append(
                    FilesystemEntry(
                        path, relative, None, False, False, is_link, "unreadable"
                    )
                )
                warnings.append(f"Failed to inspect entry {path}: {exc}")
        pending.extend(reversed(descend))
    return TraversalResult(root, tuple(entries), tuple(warnings))
