"""Tree building and rendering for pylistall.

The tree output is intentionally independent from selection filters:
- It always reflects the filesystem under the target root.
- Only -r/--recursive affects whether directories are expanded.
- Directory names are suffixed with '/'.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class TreeEntry:
    """Represents a filesystem entry for tree rendering."""

    name: str
    is_dir: bool
    children: tuple["TreeEntry", ...]


def _sort_key(entry: TreeEntry) -> tuple[int, str]:
    """Sort directories first, then files, case-insensitive by name."""
    return (0 if entry.is_dir else 1, entry.name.lower())


def _list_children(path: Path) -> list[TreeEntry]:
    """List direct children of a directory."""
    entries: list[TreeEntry] = []
    try:
        for item in path.iterdir():
            is_dir = item.is_dir()
            name = item.name + ("/" if is_dir else "")
            entries.append(TreeEntry(name=name,
                                     is_dir=is_dir,
                                     children=tuple()))
    except OSError:
        # If the directory cannot be read, treat it as empty.
        return []
    entries.sort(key=_sort_key)
    return entries


def _build_entry(path: Path, recursive: bool) -> TreeEntry:
    """Build a TreeEntry from a path."""
    is_dir = path.is_dir()
    name = path.name + ("/" if is_dir else "")

    if (not recursive) or (not is_dir):
        return TreeEntry(name=name, is_dir=is_dir, children=tuple())

    children: list[TreeEntry] = []
    try:
        for child in path.iterdir():
            children.append(_build_entry(child, recursive=True))
    except OSError:
        children = []

    children.sort(key=_sort_key)
    return TreeEntry(name=name, is_dir=is_dir, children=tuple(children))


def _render(entries: tuple[TreeEntry, ...], prefix: str) -> list[str]:
    """Render a list of entries with a given prefix."""
    lines: list[str] = []
    for idx, entry in enumerate(entries):
        is_last = idx == (len(entries) - 1)
        branch = "└── " if is_last else "├── "
        lines.append(f"{prefix}{branch}{entry.name}")

        if entry.is_dir and entry.children:
            extension = "    " if is_last else "│   "
            lines.extend(_render(entry.children, prefix + extension))
    return lines


def build_tree_text(root: Path, recursive: bool) -> str:
    """Build and render a tree text from filesystem under root."""
    if not root.exists() or not root.is_dir():
        return ""

    if not recursive:
        children = _list_children(root)
        if not children:
            return ""
        lines = _render(tuple(children), prefix="")
        return "\n".join(lines)

    # Recursive tree: build entries for all direct children and expand
    # directories.
    top_children: list[TreeEntry] = []
    try:
        for item in root.iterdir():
            top_children.append(_build_entry(item, recursive=True))
    except OSError:
        top_children = []

    top_children.sort(key=_sort_key)
    if not top_children:
        return ""
    lines = _render(tuple(top_children), prefix="")
    return "\n".join(lines)
