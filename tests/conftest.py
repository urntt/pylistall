"""Shared filesystem fixtures for behavior tests."""

from pathlib import Path
from typing import Callable, Union

import pytest


@pytest.fixture
def write_file(tmp_path: Path) -> Callable[[str, Union[str, bytes]], Path]:
    """Create a file relative to the isolated project root."""
    def write(relative_path: str, content: Union[str, bytes] = "") -> Path:
        path = tmp_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
        return path

    return write
