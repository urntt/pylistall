"""Command-line entry point for pylistall."""

from __future__ import annotations

import argparse
import fnmatch
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Sequence


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
    }
)

# Sentinel values for git log behavior.
GIT_LOG_DISABLED: int = 0
GIT_LOG_ALL: int = -1


@dataclass(frozen=True, slots=True)
class SelectedFile:
    """Represents a file selected for output."""

    absolute_path: Path
    relative_path: Path
    display_name: str


def flatten_patterns(items: Sequence[str]) -> list[str]:
    """Flatten repeated and comma-separated patterns into a single list."""
    patterns: list[str] = []
    for item in items:
        for part in item.split(","):
            part = part.strip()
            if part:
                patterns.append(part)
    return patterns


def matches_any(target: str, patterns: Iterable[str]) -> bool:
    """Return True if target matches any glob pattern."""
    return any(fnmatch.fnmatch(target, pattern) for pattern in patterns)


def is_probably_binary(path: Path) -> bool:
    """
    Heuristically determine whether a file is binary.

    Strategy:
    - Fast check by extension.
    - Byte sampling: NUL byte or high ratio of non-text bytes.
    """
    if path.suffix.lower() in BINARY_EXTENSIONS:
        return True

    try:
        data = path.read_bytes()
    except OSError:
        # If we cannot read it safely, treat it as binary.
        return True

    if not data:
        return False

    sample = data[:8192]
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
    data = path.read_bytes()
    truncated = False

    if max_bytes is not None and len(data) > max_bytes:
        data = data[:max_bytes]
        truncated = True

    text = data.decode("utf-8", errors="replace")
    if truncated:
        text += "\n\n[...TRUNCATED...]\n"
    return text


def copy_to_clipboard(text: str) -> None:
    """
    Copy text to the system clipboard using the most reliable method per OS.

    macOS: pbcopy
    Windows: clip
    Linux: xclip, then pyperclip
    """
    if sys.platform == "darwin":
        subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)
        return

    if sys.platform.startswith("win"):
        subprocess.run(["clip"], input=text.encode("utf-16le"), check=True)
        return

    try:
        subprocess.run(
            ["xclip", "-selection", "clipboard"],
            input=text.encode("utf-8"),
            check=True,
        )
        return
    except (OSError, subprocess.CalledProcessError):
        pass

    try:
        import pyperclip  # type: ignore

        pyperclip.copy(text)
        return
    except Exception as exc:  # pylint: disable=broad-exception-caught
        raise RuntimeError(
            "Clipboard copy failed. Install xclip or pyperclip."
        ) from exc


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


def select_files(
    root: Path,
    recursive: bool,
    include_patterns: list[str],
    omit_patterns: list[str],
    include_binary: bool,
) -> list[SelectedFile]:
    """Select files based on include/omit patterns and binary filtering."""
    selected: list[SelectedFile] = []

    for file_path in iter_files(root, recursive):
        relative = file_path.relative_to(root)
        rel_str = relative.as_posix()

        if include_patterns:
            if not (
                matches_any(file_path.name, include_patterns)
                or matches_any(rel_str, include_patterns)
            ):
                continue

        if omit_patterns:
            if matches_any(file_path.name, omit_patterns) or matches_any(
                rel_str, omit_patterns
            ):
                continue

        # Default behavior: do NOT include binary files, unless -b is provided.
        if (not include_binary) and is_probably_binary(file_path):
            continue

        display = rel_str if recursive else file_path.name
        selected.append(
            SelectedFile(
                absolute_path=file_path,
                relative_path=relative,
                display_name=display,
            )
        )

    selected.sort(key=lambda item: item.display_name.lower())
    return selected


class TreeNode:
    """A simple tree structure for rendering directory/file layout."""

    __slots__ = ("dirs", "files")

    def __init__(self) -> None:
        self.dirs: dict[str, TreeNode] = {}
        self.files: list[str] = []


def build_tree(selected: list[SelectedFile], recursive: bool) -> TreeNode:
    """
    Build a tree from the selected file list.

    Note: The tree reflects only files that will actually be output.
    """
    root = TreeNode()

    if not recursive:
        root.files = [item.display_name for item in selected]
        return root

    for item in selected:
        parts = item.relative_path.parts
        node = root
        for directory in parts[:-1]:
            node = node.dirs.setdefault(directory, TreeNode())
        node.files.append(parts[-1])

    sort_tree(root)
    return root


def sort_tree(node: TreeNode) -> None:
    """Sort directories and files in-place for stable rendering."""
    node.files.sort(key=str.lower)
    node.dirs = dict(sorted(node.dirs.items(), key=lambda kv: kv[0].lower()))
    for child in node.dirs.values():
        sort_tree(child)


def render_tree(node: TreeNode, recursive: bool) -> str:
    """Render a TreeNode as a tree-like string."""
    lines: list[str] = ["."]
    if not recursive:
        for index, filename in enumerate(node.files):
            is_last = index == (len(node.files) - 1)
            prefix = "└── " if is_last else "├── "
            lines.append(f"{prefix}{filename}")
        return "\n".join(lines)

    def walk(current: TreeNode, prefix: str) -> None:
        entries: list[tuple[str, str, Optional[TreeNode]]] = []
        for dirname, child in current.dirs.items():
            entries.append(("dir", dirname, child))
        for filename in current.files:
            entries.append(("file", filename, None))

        for idx, (kind, name, child_node) in enumerate(entries):
            is_last = idx == (len(entries) - 1)
            branch = "└── " if is_last else "├── "
            if kind == "dir":
                lines.append(f"{prefix}{branch}{name}")
                extension = "    " if is_last else "│   "
                if child_node is not None:
                    walk(child_node, prefix + extension)
                else:
                    walk(TreeNode(), prefix + extension)
            else:
                lines.append(f"{prefix}{branch}{name}")

    walk(node, "")
    return "\n".join(lines)


def git_log_requested(git_log_count: Optional[int]) -> bool:
    """Return True if user requested git log output."""
    return git_log_count is not None


def root_has_git(root: Path) -> bool:
    """Return True if ROOT contains a .git directory."""
    return (root / ".git").is_dir()


def get_git_log(root: Path, git_log_count: int) -> str:
    """
    Get git log entries from root.

    If git_log_count is -1, return all logs.
    Otherwise, return last N logs.
    """
    base_cmd: list[str] = [
        "git",
        "-C",
        str(root),
        "log",
        "--oneline",
        "--decorate",
    ]
    if git_log_count != GIT_LOG_ALL:
        base_cmd.append(f"-n{git_log_count}")

    try:
        result = subprocess.run(
            base_cmd,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        output = result.stdout.strip()
        return output if output else "[No git log output]"
    except (OSError, subprocess.CalledProcessError) as exc:
        return f"[Failed to read git log: {exc}]"


def build_output(
    root: Path,
    recursive: bool,
    include_patterns: list[str],
    omit_patterns: list[str],
    include_binary: bool,
    max_bytes: Optional[int],
    git_log_count: Optional[int],
) -> tuple[str, int]:
    """Build the final output text and return it along with file count."""
    selected = select_files(
        root=root,
        recursive=recursive,
        include_patterns=include_patterns,
        omit_patterns=omit_patterns,
        include_binary=include_binary,
    )

    tree_text = render_tree(build_tree(selected, recursive), recursive)

    chunks: list[str] = []
    chunks.append(f"ROOT: {root.resolve()}\n\n")
    chunks.append("TREE:\n")
    chunks.append(f"{tree_text}\n\n")

    if git_log_requested(git_log_count):
        chunks.append("GIT LOG:\n")
        if root_has_git(root):
            assert git_log_count is not None
            chunks.append(f"{get_git_log(root, git_log_count)}\n\n")
        else:
            chunks.append("[No .git directory found under ROOT]\n\n")

    for item in selected:
        content = read_text(item.absolute_path, max_bytes=max_bytes)
        chunks.append(f"`{item.display_name}`:\n")
        chunks.append("```\n")
        chunks.append(f"{content}\n")
        chunks.append("```\n\n")

    return ("".join(chunks).rstrip() + "\n", len(selected))


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        prog="pylistall",
        description="Copy directory file contents to " +
                    "clipboard with tree and optional git log.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Target directory (default: current directory).",
    )
    parser.add_argument(
        "-i",
        "--include",
        action="append",
        default=[],
        help="Include glob patterns (repeatable, comma-separated supported).",
    )
    parser.add_argument(
        "-o",
        "--omit",
        action="append",
        default=[],
        help="Omit glob patterns (repeatable, comma-separated supported).",
    )
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="Recurse into subdirectories (tree will include directories).",
    )

    # -b behavior:
    #   if provided, include binary files;
    #   if omitted, exclude binaries.
    parser.add_argument(
        "-b",
        "--binary",
        action="store_true",
        help="Include binary files (default: binary files are excluded).",
    )

    parser.add_argument(
        "--max-bytes",
        type=int,
        default=None,
        help="Max bytes per file to read (default: no limit).",
    )

    # -g behavior:
    #   not provided  -> None (disabled)
    #   provided w/o N -> const=-1 (all)
    #   provided with N -> int N
    parser.add_argument(
        "-g",
        "--git-log",
        nargs="?",
        const=GIT_LOG_ALL,
        default=None,
        type=int,
        metavar="N",
        help=(
            "Include git log if ROOT contains .git. "
            "Use -g for all logs, or -g N for last N entries."
        ),
    )

    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI entry point."""
    args = parse_args(argv)

    root = Path(args.path).expanduser()
    if not root.exists():
        print(f"Error: path does not exist: {root}")
        return 2
    if not root.is_dir():
        print(f"Error: path is not a directory: {root}")
        return 2

    include_patterns = flatten_patterns(args.include)
    omit_patterns = flatten_patterns(args.omit)

    output, file_count = build_output(
        root=root,
        recursive=bool(args.recursive),
        include_patterns=include_patterns,
        omit_patterns=omit_patterns,
        include_binary=bool(args.binary),
        max_bytes=args.max_bytes,
        git_log_count=args.git_log,
    )

    copy_to_clipboard(output)
    print(f"Copied to clipboard: {root.resolve()} (files: {file_count})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
