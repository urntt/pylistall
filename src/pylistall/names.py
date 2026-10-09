"""Safe literal display of filesystem names, without changing their identity."""

from __future__ import annotations

import re
import unicodedata
from pathlib import PurePath, PureWindowsPath


def visible_name(value: str) -> str:
    escapes = {"\n": r"\n", "\r": r"\r", "\t": r"\t", "\x1b": r"\x1b"}
    return "".join(
        escapes.get(char, f"\\u{ord(char):04x}")
        if unicodedata.category(char) in {"Cc", "Cf", "Cs"}
        else char
        for char in value
    )


def inline_code(value: str) -> str:
    value = visible_name(value)
    ticks = "`" * (max([0] + [len(m.group()) for m in re.finditer(r"`+", value)]) + 1)
    padding = (
        " "
        if value.startswith("`")
        or value.endswith("`")
        or (value.startswith(" ") and value.endswith(" ") and value.strip())
        else ""
    )
    return f"{ticks}{padding}{value}{padding}{ticks}"


def project_name(path: PurePath) -> str:
    if path.name:
        return path.name
    if isinstance(path, PureWindowsPath) and path.drive.startswith("\\\\"):
        return path.drive.rsplit("\\", 1)[-1]
    return path.anchor
