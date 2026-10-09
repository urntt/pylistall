"""Git log collection for pylistall."""

from __future__ import annotations

import codecs
import io
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from pylistall.traversal import TraversalResult, scan_directory

GIT_LOG_ALL: int = -1


@dataclass(frozen=True)
class GitLogOptions:
    """Options for git log output."""

    enabled: bool
    count: Optional[int]


@dataclass(frozen=True)
class GitEntry:
    """A discovered .git entry."""

    git_path: Path
    is_dir: bool


def _run_git_log(
    repo_root: Path,
    count: int,
    check_size: Optional[Callable[[int], None]] = None,
    chunk_bytes: int = 4096,
    report: Optional[Callable[..., None]] = None,
) -> str:
    """Read logs in chunks and always reap the process after an early abort."""
    if check_size is not None:
        check_size(0)
    cmd = ["git", "-C", str(repo_root), "log", "--oneline", "--decorate", "--no-color"]
    if count != GIT_LOG_ALL:
        cmd.append(f"-n{count}")
    process = None
    try:
        # A file avoids deadlock if Git writes substantial stderr while stdout
        # is being read. Diagnostics are represented by a bounded error marker.
        with tempfile.TemporaryFile() as errors:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=errors)
            assert process.stdout is not None
            decoder = io.IncrementalNewlineDecoder(
                codecs.getincrementaldecoder("utf-8")(errors="replace"), True
            )
            chunks = []
            size = 0
            pending_space = 0
            started = False
            while True:
                data = process.stdout.read1(chunk_bytes)
                if report is not None:
                    report("git", str(repo_root))
                text = decoder.decode(data, final=not data)
                chunks.append(text)
                # Ignore only outer whitespace, as the baseline Git output did.
                if not started:
                    text = text.lstrip()
                    started = bool(text)
                content = text.rstrip()
                if content:
                    size += pending_space + len(content.encode("utf-8"))
                    pending_space = len(text[len(content) :].encode("utf-8"))
                else:
                    pending_space += len(text.encode("utf-8"))
                if check_size is not None:
                    check_size(size)
                if not data:
                    break
            if process.wait() != 0:
                return f"[Failed to read git log: exit status {process.returncode}]"
            return "".join(chunks).strip() or "[No git log output]"
    except OSError as exc:
        return f"[Failed to read git log: {exc}]"
    finally:
        if process is not None:
            if process.poll() is None:
                process.kill()
            process.wait()
            if process.stdout is not None:
                process.stdout.close()


def _sort_key(entry: GitEntry) -> tuple[str, int]:
    """Sort by path (case-insensitive), then dir before file."""
    return (str(entry.git_path.resolve()).lower(), 0 if entry.is_dir else 1)


def _find_git_entries(
    root: Path,
    recursive: bool,
    follow_links: bool = False,
    *,
    snapshot: Optional[TraversalResult] = None,
) -> tuple[list[GitEntry], list[str]]:
    """Discover repositories from the same entries used by the other collectors."""
    if snapshot is None:
        snapshot = scan_directory(root, recursive, follow_links)
    entries = [
        GitEntry(entry.path, entry.is_dir)
        for entry in snapshot.git_entries
        if entry.path.name == ".git"
        and (entry.is_dir or entry.is_file)
        and entry.skipped is None
    ]
    entries.sort(key=_sort_key)
    return entries, []
