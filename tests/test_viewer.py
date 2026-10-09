"""TTY routing, literal rendering, pager selection and graceful transport."""

import builtins
import io

import pytest

from pylistall import viewer
from pylistall.output import ContentBlock, OutputDocument, render_markdown


class Terminal(io.StringIO):
    def __init__(self, tty=True):
        super().__init__()
        self.tty = tty

    def isatty(self):
        return self.tty


@pytest.fixture
def document():
    return OutputDocument(
        "project",
        "C:/project/[bold]🙂",
        "└── source.py",
        (),
        (ContentBlock("[red]中文.py", 'print("中文🙂")\n', "python"),),
    )


def test_rich_renders_literal_paths_without_fences_or_numbers(document):
    text = viewer.render_terminal(document, width=100, color=False)
    assert "[bold]🙂" in text and "[red]中文.py" in text
    assert 'print("中文🙂")' in text
    assert "```" not in text and "\x1b" not in text
    assert "Directory tree" not in text and "Files" in text


@pytest.mark.parametrize("missing", ["rich.console", "rich.syntax", "pygments"])
def test_import_failure_silently_falls_back(document, monkeypatch, missing):
    original = builtins.__import__

    def importing(name, *args, **kwargs):
        if name == missing or (missing == "pygments" and name == "rich.syntax"):
            raise ImportError("synthetic missing dependency")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", importing)
    stdout = Terminal()
    monkeypatch.setattr(viewer.sys, "stdout", stdout)
    monkeypatch.setattr(viewer.sys, "stdin", Terminal(False))
    viewer.display(document, render_markdown(document))
    assert stdout.getvalue() == render_markdown(document)


def test_redirected_output_never_imports_rich_or_starts_pager(document, monkeypatch):
    stdout = Terminal(False)
    monkeypatch.setattr(viewer.sys, "stdout", stdout)

    def forbidden(*args, **kwargs):
        pytest.fail("redirected output must not use terminal components")

    monkeypatch.setattr(viewer, "render_terminal", forbidden)
    monkeypatch.setattr(viewer, "choose_pager", forbidden)
    viewer.display(document, render_markdown(document))
    assert stdout.getvalue() == render_markdown(document)
    assert "\x1b" not in stdout.getvalue()


@pytest.mark.parametrize("stdin_tty,no_pager", [(False, False), (True, True)])
def test_pager_requires_both_terminals_and_can_be_disabled(
    document, monkeypatch, stdin_tty, no_pager
):
    stdout = Terminal()
    monkeypatch.setattr(viewer.sys, "stdout", stdout)
    monkeypatch.setattr(viewer.sys, "stdin", Terminal(stdin_tty))

    def forbidden():
        pytest.fail("pager must not be selected")

    monkeypatch.setattr(viewer, "choose_pager", forbidden)
    viewer.display(document, render_markdown(document), no_pager=no_pager)
    assert "Files" in stdout.getvalue()


def test_pager_quit_does_not_dump_remaining_body(document, monkeypatch):
    stdout = Terminal()
    monkeypatch.setattr(viewer.sys, "stdout", stdout)
    monkeypatch.setattr(viewer.sys, "stdin", Terminal())
    monkeypatch.setattr(
        viewer, "choose_pager", lambda: viewer.PagerCommand(("less", "-FRX"), "less")
    )
    seen = []
    monkeypatch.setattr(
        viewer, "run_pager", lambda text, command: seen.append(text) or True
    )
    viewer.display(document, render_markdown(document))
    assert seen and stdout.getvalue() == ""


def test_launch_failure_displays_directly(document, monkeypatch):
    stdout = Terminal()
    monkeypatch.setattr(viewer.sys, "stdout", stdout)
    monkeypatch.setattr(viewer.sys, "stdin", Terminal())
    monkeypatch.setattr(
        viewer, "choose_pager", lambda: viewer.PagerCommand(("missing",), "custom")
    )
    monkeypatch.setattr(viewer, "run_pager", lambda *args: False)
    viewer.display(document, render_markdown(document))
    assert "[red]中文.py" in stdout.getvalue()


@pytest.mark.parametrize(
    "configured", ["less -S", '"C:/Program Files/Git/usr/bin/less.exe" -S']
)
def test_configured_less_gets_defaults(configured, monkeypatch):
    monkeypatch.setenv("PAGER", configured)
    pager = viewer.choose_pager()
    assert pager.kind == "less" and pager.args[1:] == ("-FRX", "-S")


def test_empty_or_invalid_pager_disables(monkeypatch):
    for value in ("", "   ", '"unterminated'):
        monkeypatch.setenv("PAGER", value)
        assert viewer.choose_pager() is None


def test_path_less_precedes_more(monkeypatch):
    monkeypatch.delenv("PAGER", raising=False)
    monkeypatch.setattr(viewer.shutil, "which", lambda name: "/bin/" + name)
    assert viewer.choose_pager().args == ("/bin/less", "-FRX")


def test_git_bundled_less_on_windows(tmp_path, monkeypatch):
    monkeypatch.delenv("PAGER", raising=False)
    monkeypatch.setattr(viewer.sys, "platform", "win32")
    git = tmp_path / "Git" / "cmd" / "git.exe"
    less = tmp_path / "Git" / "usr" / "bin" / "less.exe"
    less.parent.mkdir(parents=True)
    less.write_text("fixture", encoding="utf-8")
    monkeypatch.setattr(
        viewer.shutil, "which", lambda name: str(git) if name == "git" else None
    )
    assert viewer.choose_pager().args == (str(less), "-FRX")


def test_more_fallback_or_no_pager(monkeypatch):
    monkeypatch.delenv("PAGER", raising=False)
    monkeypatch.setattr(
        viewer.shutil, "which", lambda name: "more" if name == "more" else None
    )
    assert viewer.choose_pager().kind == "more"
    monkeypatch.setattr(viewer.shutil, "which", lambda name: None)
    assert viewer.choose_pager() is None


def test_more_uses_plain_platform_encoded_input(document, monkeypatch):
    class Process:
        stdin = io.BytesIO()

        def communicate(self, data):
            self.data = data

    process = Process()
    monkeypatch.setattr(viewer.subprocess, "Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr(viewer, "_pager_encoding", lambda kind: "utf-16le")
    text = viewer.render_terminal(document, width=100, color=False)
    assert viewer.run_pager(text, viewer.PagerCommand(("more",), "more"))
    assert process.data.decode("utf-16le") == text and "\x1b" not in text


def test_pager_start_failure_is_not_an_error(monkeypatch):
    def fail(*args, **kwargs):
        raise FileNotFoundError()

    monkeypatch.setattr(viewer.subprocess, "Popen", fail)
    assert not viewer.run_pager("text", viewer.PagerCommand(("missing",), "custom"))


def test_early_pager_pipe_close_is_reaped(monkeypatch):
    class Process:
        stdin = io.BytesIO()
        waited = False

        def communicate(self, data):
            raise BrokenPipeError()

        def wait(self):
            self.waited = True

    process = Process()
    monkeypatch.setattr(viewer.subprocess, "Popen", lambda *args, **kwargs: process)
    assert viewer.run_pager("large text", viewer.PagerCommand(("less",), "less"))
    assert process.waited and process.stdin.closed


def test_failed_pager_initialization_falls_back(monkeypatch):
    class Process:
        stdin = io.BytesIO()
        returncode = 1

        def communicate(self, data):
            pass

    monkeypatch.setattr(viewer.subprocess, "Popen", lambda *args, **kwargs: Process())
    assert not viewer.run_pager("text", viewer.PagerCommand(("less",), "less"))


def test_pager_cancellation_reaps_and_propagates(monkeypatch):
    class Process:
        stdin = io.BytesIO()
        killed = waited = False

        def communicate(self, data):
            raise KeyboardInterrupt()

        def kill(self):
            self.killed = True

        def wait(self):
            self.waited = True

    process = Process()
    monkeypatch.setattr(viewer.subprocess, "Popen", lambda *args, **kwargs: process)
    with pytest.raises(KeyboardInterrupt):
        viewer.run_pager("text", viewer.PagerCommand(("less",), "less"))
    assert process.killed and process.waited and process.stdin.closed


def test_rich_color_and_no_color(document, monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("TERM", "xterm-256color")
    assert "\x1b[" in viewer.render_terminal(document, width=100, color=True)
    assert "\x1b" not in viewer.render_terminal(document, width=100, color=False)


def test_real_closed_downstream_pipe_has_no_traceback():
    import subprocess
    import sys

    code = 'from pylistall.viewer import display; from pylistall.output import OutputDocument; display(OutputDocument("project",None,None,None,None), "x"*2000000)'
    process = subprocess.Popen(
        [sys.executable, "-c", code], stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    process.stdout.close()
    process.wait(timeout=15)
    errors = process.stderr.read()
    process.stderr.close()
    assert process.returncode == 0 and not errors, errors.decode(errors="replace")
