"""Git log collection for pylistall."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


GIT_LOG_ALL: int = -1


@dataclass(frozen=True, slots=True)
class GitLogOptions:
    """Options for git log output."""

    enabled: bool
    count: Optional[int]


@dataclass(frozen=True, slots=True)
class GitEntry:
    """A discovered .git entry."""

    git_path: Path
    is_dir: bool


def _run_git_log(repo_root: Path, count: int) -> str:
    """Run git log for a repository root."""
    cmd: list[str] = [
        "git",
        "-C",
        str(repo_root),
        "log",
        "--oneline",
        "--decorate",
    ]
    if count != GIT_LOG_ALL:
        cmd.append(f"-n{count}")

    try:
        result = subprocess.run(
            cmd,
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


def _sort_key(entry: GitEntry) -> tuple[str, int]:
    """Sort by path (case-insensitive), then dir before file."""
    return (str(entry.git_path.resolve()).lower(), 0 if entry.is_dir else 1)


def _find_git_entries(root: Path,
                      recursive: bool) -> tuple[list[GitEntry], list[str]]:
    """Find .git directories/files under root, depending on recursive mode."""
    warnings: list[str] = []
    entries: list[GitEntry] = []

    if not recursive:
        git_path = root / ".git"
        if git_path.exists():
            entries.append(GitEntry(git_path=git_path,
                                    is_dir=git_path.is_dir()))
        # Defensive: if a filesystem ever reports both, warn and treat as two
        # entries.
        if git_path.is_dir() and git_path.is_file():
            warnings.append(
                "Both '.git' directory and '.git' file "
                "appear to exist under root. "
                "They were processed separately (directory first)."
            )
            entries = [
                GitEntry(git_path=git_path, is_dir=True),
                GitEntry(git_path=git_path, is_dir=False),
            ]
        entries.sort(key=_sort_key)
        return entries, warnings

    # Recursive search: include both files and directories named '.git'
    try:
        for path in root.rglob(".git"):
            if path.exists():
                entries.append(GitEntry(git_path=path, is_dir=path.is_dir()))
    except OSError:
        entries = []

    entries.sort(key=_sort_key)
    return entries, warnings


def build_git_log_sections(
    root: Path,
    recursive: bool,
    count: Optional[int],
) -> tuple[str, list[str]]:
    """Build git log sections.

    Each section always starts with the absolute '.git' path line.
    """
    entries, warnings = _find_git_entries(root=root, recursive=recursive)
    if not entries:
        return ("", warnings)

    git_count = GIT_LOG_ALL if count is None else int(count)

    chunks: list[str] = []
    for idx, entry in enumerate(entries):
        if idx > 0:
            chunks.append("\n\n")

        git_abs = entry.git_path.resolve()
        repo_root = entry.git_path.parent
        chunks.append(f"{git_abs}\n")
        chunks.append(f"{_run_git_log(repo_root=repo_root, count=git_count)}")

    return ("".join(chunks), warnings)
