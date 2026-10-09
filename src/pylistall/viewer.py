"""Literal terminal rendering and optional interactive pager transport."""

from __future__ import annotations

import errno
import io
import locale
import os
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from pylistall.names import visible_name
from pylistall.output import BINARY_PLACEHOLDER, GROUPS, TRUNCATED, OutputDocument

# POSIX SIGPIPE is returned either as -13 or as the shell status 128 + 13.
NORMAL_PAGER_EXIT_CODES = {0, -13, 141}


@dataclass(frozen=True)
class PagerCommand:
    args: tuple[str, ...]
    kind: str


def render_terminal(
    document: OutputDocument, *, width: int, color: bool
) -> Optional[str]:
    """Import Rich lazily; missing Rich or transitive imports silently fall back."""
    try:
        from rich.console import Console
        from rich.syntax import Syntax
        from rich.text import Text

        output = io.StringIO()
        console = Console(
            file=output,
            width=width,
            force_terminal=color,
            color_system="auto" if color else None,
            markup=False,
            highlight=False,
            emoji=False,
            legacy_windows=False,
        )
        console.print(Text(visible_name(document.project_name), style="bold cyan"))
        if document.path is not None:
            console.print(Text(visible_name(document.path)))
        if document.tree is not None:
            console.print(Text(document.tree or "(empty)"))
        console.print()
        for part, blocks in [("git", document.git), ("files", document.files)]:
            if blocks is None:
                continue
            console.rule(Text(GROUPS[part][0]), style="cyan")
            if not blocks:
                console.print(Text(GROUPS[part][1]))
            for block in blocks:
                console.print(Text(visible_name(block.title), style="bold cyan"))
                if block.text is None:
                    console.print(Text(BINARY_PLACEHOLDER))
                    console.print()
                    continue
                if block.encoding == "Base64":
                    console.print(Text("Encoding: Base64"))
                console.print(
                    Syntax(
                        block.text,
                        block.language,
                        line_numbers=False,
                        word_wrap=True,
                        background_color="default",
                        theme="ansi_dark",
                    )
                )
                if block.encoding == "Base64" and block.truncated:
                    console.print(Text(TRUNCATED))
                console.print()
        return output.getvalue()
    except ImportError:
        return None


def _command(args: list[str]) -> PagerCommand:
    basename = Path(args[0]).name.lower()
    kind = (
        "less"
        if basename in ("less", "less.exe")
        else ("more" if basename in ("more", "more.com", "more.exe") else "custom")
    )
    if kind == "less":
        args = [args[0], "-FRX", *args[1:]]
    return PagerCommand(tuple(args), kind)


def choose_pager() -> Optional[PagerCommand]:
    """Honor PAGER, then locate less (including Git for Windows), then more."""
    configured = os.environ.get("PAGER")
    if configured is not None:
        if not configured.strip():
            return None
        try:
            args = shlex.split(configured, posix=sys.platform != "win32")
            if sys.platform == "win32":
                args = [
                    a[1:-1] if len(a) > 1 and a[0] == a[-1] and a[0] in "\"'" else a
                    for a in args
                ]
            return _command(args) if args else None
        except ValueError:
            return None
    less = shutil.which("less")
    if less:
        return _command([less])
    if sys.platform == "win32":
        git = shutil.which("git")
        if git:
            for parent in list(Path(git).resolve().parents)[:3]:
                candidate = parent / "usr" / "bin" / "less.exe"
                if candidate.is_file():
                    return _command([str(candidate)])
    more = shutil.which("more")
    return _command([more]) if more else None


def _pager_encoding(kind: str) -> str:
    if kind != "more":
        return "utf-8"
    if sys.platform == "win32":
        import ctypes

        codepage = ctypes.windll.kernel32.GetConsoleOutputCP()
        if codepage:
            return f"cp{codepage}"
    return locale.getpreferredencoding(False)


def run_pager(text: str, command: PagerCommand) -> bool:
    """Fall back after failed startup; a normal quit or closed pipe is harmless."""
    environment = os.environ.copy()
    if command.kind == "less":
        environment["LESSCHARSET"] = "utf-8"
    process = None
    try:
        process = subprocess.Popen(command.args, stdin=subprocess.PIPE, env=environment)
    except OSError:
        return False
    try:
        process.communicate(
            text.encode(_pager_encoding(command.kind), errors="replace")
        )
    except BrokenPipeError:
        process.wait()
    except KeyboardInterrupt:
        process.kill()
        process.wait()
        raise
    finally:
        if process.stdin is not None:
            try:
                process.stdin.close()
            except BrokenPipeError:
                pass
    return getattr(process, "returncode", 0) in NORMAL_PAGER_EXIT_CODES


def _write_stdout(text: str) -> None:
    try:
        sys.stdout.write(text)
        sys.stdout.flush()
    except OSError as exc:
        if not isinstance(exc, BrokenPipeError) and not (
            sys.platform == "win32"
            and exc.errno == errno.EINVAL
            and not getattr(sys.stdout, "isatty", lambda: False)()
        ):
            raise
        # Prevent Python's shutdown flush from producing a second pipe error.
        try:
            descriptor = sys.stdout.fileno()
            with open(os.devnull, "w") as sink:
                os.dup2(sink.fileno(), descriptor)
        except (OSError, AttributeError, io.UnsupportedOperation):
            try:
                sys.stdout.close()
            except BrokenPipeError:
                pass


def display(document: OutputDocument, markdown: str, *, no_pager: bool = False) -> None:
    """Redirected output stays canonical Markdown and never imports Rich."""
    if not getattr(sys.stdout, "isatty", lambda: False)():
        _write_stdout(markdown)
        return
    interactive = getattr(sys.stdin, "isatty", lambda: False)()
    pager = choose_pager() if interactive and not no_pager else None
    width = shutil.get_terminal_size(fallback=(88, 24)).columns
    pretty = render_terminal(
        document, width=width, color=pager is None or pager.kind == "less"
    )
    text = markdown if pretty is None else pretty
    if pager is not None and run_pager(text, pager):
        return
    _write_stdout(text)
