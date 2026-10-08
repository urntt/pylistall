"""Resolve output destinations and write complete UTF-8 files safely."""

from __future__ import annotations

import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional


def resolve_destination(raw: Optional[str], cwd: Path) -> Path:
    """Calculate one local timestamp and interpret relative paths from cwd."""
    name = datetime.now().strftime("pylistall-output-%Y-%m-%d-%H-%M-%S.md")
    path = Path(raw or ".").expanduser()
    if not path.is_absolute():
        path = cwd / path
    separators = tuple(s for s in (os.sep, os.altsep) if s)
    if not raw or path.is_dir() or raw.endswith(separators):
        path /= name
    return path.parent.resolve() / path.name


def validate_destination(path: Path, overwrite: bool) -> None:
    """Reject directories and existing names, including dangling symlinks."""
    if path.is_dir():
        raise IsADirectoryError(f"Output destination is a directory: {path}")
    if os.path.lexists(path) and not overwrite:
        raise FileExistsError(f"Output already exists: {path}; use -w to overwrite")


def write_output(path: Path, text: str, overwrite: bool) -> None:
    """Clean incomplete new files; atomically replace only completed overwrites."""
    validate_destination(path, overwrite)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not overwrite:
        created = False
        try:
            with path.open("xb") as handle:
                created = True
                handle.write(text.encode("utf-8"))
                handle.flush()
                os.fsync(handle.fileno())
        except BaseException:
            if created:
                path.unlink(missing_ok=True)
            raise
        return
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=path.parent, prefix=".pylistall-", delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write(text.encode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())
        validate_destination(path, True)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
