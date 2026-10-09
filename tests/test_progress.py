"""Feedback activation, safe literal rendering, cancellation, and UI isolation."""

import builtins
import io

import pytest

from pylistall import cli, progress


class Stream(io.StringIO):
    def __init__(self, tty):
        super().__init__()
        self.tty = tty

    def isatty(self):
        return self.tty


@pytest.mark.parametrize(
    "tty,term,disabled,enabled",
    [
        (True, "xterm", False, True),
        (False, "xterm", False, False),
        (True, "dumb", False, False),
        (True, "xterm", True, False),
    ],
)
def test_progress_gate_uses_stderr_only(monkeypatch, tty, term, disabled, enabled):
    monkeypatch.setattr(progress.sys, "stderr", Stream(tty))
    monkeypatch.setattr(progress.sys, "stdout", Stream(False))
    monkeypatch.setenv("TERM", term)
    with progress.CollectionProgress(disabled) as feedback:
        assert (feedback.progress is not None) == enabled
        feedback.update("scan", "[red]中文🙂\n\x1b", discovered=1)
        feedback.update("files", "file", total=2, checked=1, collected=0)
    assert feedback.progress is None


def test_missing_rich_quietly_disables_progress(monkeypatch):
    stderr = Stream(True)
    monkeypatch.setattr(progress.sys, "stderr", stderr)
    monkeypatch.setenv("TERM", "xterm")
    original = builtins.__import__

    def importing(name, *args, **kwargs):
        if name.startswith("rich"):
            raise ImportError("missing")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", importing)
    with progress.CollectionProgress() as feedback:
        feedback.update("scan", "path")
    assert feedback.progress is None and stderr.getvalue() == ""


def test_progress_configuration_and_ui_failure_cleanup(monkeypatch):
    from rich import progress as rich_progress

    configured = {}

    class Broken:
        stopped = False

        def __init__(self, *args, **kwargs):
            configured.update(kwargs)

        def start(self):
            pass

        def stop(self):
            self.stopped = True

        def add_task(self, *args, **kwargs):
            raise RuntimeError("UI failure")

    monkeypatch.setattr(rich_progress, "Progress", Broken)
    monkeypatch.setattr(progress.sys, "stderr", Stream(True))
    monkeypatch.setenv("TERM", "xterm")
    with progress.CollectionProgress() as feedback:
        renderer = feedback.progress
        feedback.update("files", "[red]", total=1)
        assert feedback.progress is None and renderer.stopped
    assert configured["refresh_per_second"] == 10
    assert not configured["redirect_stdout"] and not configured["redirect_stderr"]


def test_render_progress_uses_its_own_counts_and_literal_paths(monkeypatch):
    from rich import progress as rich_progress

    updates = []

    class Renderer:
        def __init__(self, *args, **kwargs):
            pass

        def start(self):
            pass

        def stop(self):
            pass

        def add_task(self, *args, **kwargs):
            return 0

        def remove_task(self, task):
            pass

        def update(self, task, **kwargs):
            updates.append(kwargs)

    monkeypatch.setattr(rich_progress, "Progress", Renderer)
    monkeypatch.setattr(progress.sys, "stderr", Stream(True))
    monkeypatch.setenv("TERM", "xterm")
    with progress.CollectionProgress() as feedback:
        feedback.update("files", total=602, checked=602, collected=601)
        feedback.update("render", "[red]中文🙂\n\x1b", total=603, rendered=0)
        feedback.update("render", "binary.bin", rendered=603)
    assert updates[1]["counts"] == "0/603 blocks rendered"
    assert updates[1]["completed"] == 0 and updates[1]["total"] == 603
    assert updates[1]["description"] == "render: [red]中文🙂\\n\\x1b"
    assert updates[2]["counts"] == "603/603 blocks rendered"


@pytest.mark.parametrize("options", [[], ["-f", "unused"], ["-D"], ["-c"]])
def test_progress_stops_before_delivery_and_cancellation(
    tmp_path, monkeypatch, options, capsys
):
    order = []

    class Feedback:
        def __init__(self, disabled=False):
            order.append("disabled" if disabled else "enabled")

        def __enter__(self):
            return self

        def update(self, *args, **kwargs):
            pass

        def __exit__(self, *args):
            order.append("stop")

    monkeypatch.setattr(cli, "CollectionProgress", Feedback)

    def delivered(*args, **kwargs):
        assert order[-1] == "stop"

    monkeypatch.setattr(cli, "display", delivered)
    monkeypatch.setattr(cli, "write_output", delivered)
    monkeypatch.setattr(cli, "copy_to_clipboard", delivered)
    assert cli.main([str(tmp_path), *options]) == 0
    assert order == ["enabled", "stop"]

    def interrupt(*args, **kwargs):
        raise KeyboardInterrupt()

    monkeypatch.setattr(cli, "_build_output", interrupt)
    assert cli.main([str(tmp_path), *options]) == 130
    assert order[-1] == "stop" and "Traceback" not in capsys.readouterr().err


def test_no_progress_and_no_pager_are_independent(tmp_path, monkeypatch):
    gates = []
    original = cli.CollectionProgress

    def configured(disabled):
        gates.append(disabled)
        return original(True)

    monkeypatch.setattr(cli, "CollectionProgress", configured)
    paging = []
    monkeypatch.setattr(
        cli,
        "display",
        lambda *args, **kw: paging.append((kw["no_pager"], kw["no_progress"])),
    )
    assert cli.main([str(tmp_path), "-P"]) == 0
    assert cli.main([str(tmp_path), "-n"]) == 0
    assert gates == [True, False] and paging == [(False, True), (True, False)]


def test_write_cancellation_cleans_partial_and_preserves_original(
    tmp_path, monkeypatch
):
    from pylistall import destinations

    target = tmp_path / "result"
    target.write_text("original", encoding="utf-8")

    def interrupted(*args):
        raise KeyboardInterrupt()

    monkeypatch.setattr(destinations.os, "fsync", interrupted)
    assert cli.main([str(tmp_path), "-f", str(target), "-w"]) == 130
    assert target.read_text(encoding="utf-8") == "original"
    assert list(tmp_path.iterdir()) == [target]
