"""Render the discovered tree independently from content filters."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pylistall.traversal import FilesystemEntry, TraversalResult, scan_directory


def render_tree(snapshot: TraversalResult) -> str:
    """Render iteratively, including unexpanded links and failed entries."""
    children: dict[Path, list[FilesystemEntry]] = {}
    for entry in snapshot.entries:
        children.setdefault(entry.relative_path.parent, []).append(entry)
    for siblings in children.values():
        siblings.sort(
            key=lambda entry: (
                not entry.is_dir,
                entry.path.name.lower(),
                entry.path.name,
            )
        )
    lines: list[str] = []
    stack = [
        (entry, "", index == len(children.get(Path("."), [])) - 1)
        for index, entry in reversed(list(enumerate(children.get(Path("."), []))))
    ]
    while stack:
        entry, prefix, last = stack.pop()
        name = entry.path.name + ("@" if entry.is_link else "")
        name += "/" if entry.is_dir else ""
        lines.append(f"{prefix}{'└── ' if last else '├── '}{name}")
        nested = children.get(entry.relative_path, [])
        extension = prefix + ("    " if last else "│   ")
        for index in range(len(nested) - 1, -1, -1):
            stack.append((nested[index], extension, index == len(nested) - 1))
    return "\n".join(lines)


def build_tree_text(
    root: Path,
    recursive: bool,
    follow_links: bool = False,
    *,
    snapshot: Optional[TraversalResult] = None,
) -> str:
    """Render an existing scan, or discover entries for standalone callers."""
    if snapshot is None:
        if not root.exists() or not root.is_dir():
            return ""
        snapshot = scan_directory(root, recursive, follow_links)
    return render_tree(snapshot)
