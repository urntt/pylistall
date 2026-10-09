"""Discover filesystem entries once, with consistent link and cycle handling."""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from pylistall.names import visible_name
from pylistall.patterns import omitted, target_omitted


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
    git_entries: tuple[FilesystemEntry, ...] = ()
    discovered_count: int = 0


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
    root: Path,
    recursive: bool,
    follow_links: bool = False,
    *,
    omit: tuple[str, ...] = (),
    collect_git: bool = True,
    report: Optional[Callable[..., None]] = None,
) -> TraversalResult:
    """Scan iteratively; only the current ancestor chain forbids aliases."""
    root = root.resolve(strict=True)
    entries: list[FilesystemEntry] = []
    warnings: list[str] = []
    git_entries: list[FilesystemEntry] = []
    discovered = 0
    pending = [(root, frozenset({_identity(root, root.stat())}))]
    while pending:
        directory, ancestors = pending.pop()
        if report is not None:
            report("scan", str(directory), discovered=discovered)
        paths: list[Path] = []
        try:
            with os.scandir(directory) as children:
                for child in children:
                    paths.append(directory / child.name)
                    discovered += 1
                    if report is not None:
                        report(
                            "scan", str(directory / child.name), discovered=discovered
                        )
        except OSError as exc:
            if directory == root:
                raise
            warnings.append(
                f"Failed to list directory {visible_name(str(directory))}: {exc}"
            )
        descend = []
        for path in sorted(paths, key=lambda item: (item.name.lower(), item.name)):
            if report is not None:
                report("scan", str(path), discovered=discovered)
            relative = path.relative_to(root)
            rel_str = relative.as_posix()
            logical_omit = omitted(path.name, rel_str, omit)
            git_marker = collect_git and path.name == ".git"
            if logical_omit and not git_marker:
                continue
            is_link = False
            try:
                info = path.lstat()
                is_link = _is_link(info)
                logical_omit = logical_omit or omitted(
                    path.name, rel_str, omit, directory=stat.S_ISDIR(info.st_mode)
                )
                if logical_omit and not git_marker:
                    continue
                if is_link and not follow_links:
                    if not logical_omit:
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
                if follow_links and target_omitted(
                    target, root, omit, directory=is_dir
                ):
                    if not git_marker or target_omitted(
                        target.parent, root, omit, directory=True
                    ):
                        continue
                    # Explicit Git collection is allowed to inspect omitted metadata.
                    logical_omit = True
                logical_omit = logical_omit or omitted(
                    path.name, rel_str, omit, directory=is_dir
                )
                identity = _identity(target, info)
                skipped = None if is_dir or is_file else "special-file"
                if recursive and is_dir and identity in ancestors:
                    skipped = "cycle"
                    warnings.append(
                        f"Skipped directory cycle: {visible_name(str(path))}"
                    )
                entry = FilesystemEntry(
                    path, relative, target, is_dir, is_file, is_link, skipped
                )
                if git_marker and skipped is None:
                    git_entries.append(entry)
                if not logical_omit:
                    entries.append(entry)
                if recursive and is_dir and skipped is None and not logical_omit:
                    descend.append((path, ancestors | {identity}))
            except (OSError, RuntimeError) as exc:
                if not logical_omit:
                    entries.append(
                        FilesystemEntry(
                            path, relative, None, False, False, is_link, "unreadable"
                        )
                    )
                if not logical_omit:
                    warnings.append(
                        f"Failed to inspect entry {visible_name(str(path))}: {exc}"
                    )
        pending.extend(reversed(descend))
    return TraversalResult(
        root, tuple(entries), tuple(warnings), tuple(git_entries), discovered
    )
