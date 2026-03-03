"""Utility helpers for pylistall."""

from __future__ import annotations

import subprocess
import sys
import pyperclip


def copy_to_clipboard(text: str) -> None:
    """Copy text to the system clipboard using the most reliable method per OS.

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
        pyperclip.copy(text)
        return
    except Exception as exc:  # pylint: disable=broad-exception-caught
        raise RuntimeError("Clipboard copy failed. "
                           "Install xclip or pyperclip.") from exc
