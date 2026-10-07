"""Clipboard backend selection and encoding without external programs."""

import subprocess

import pytest

from pylistall import util


@pytest.mark.parametrize(
    ("platform", "command", "encoding"),
    [
        ("win32", ["clip"], "utf-16le"),
        ("darwin", ["pbcopy"], "utf-8"),
        ("linux", ["xclip", "-selection", "clipboard"], "utf-8"),
    ],
)
def test_platform_backend_receives_unicode(monkeypatch, platform, command, encoding):
    calls = []
    monkeypatch.setattr(util.sys, "platform", platform)

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))

    monkeypatch.setattr(util.subprocess, "run", fake_run)

    util.copy_to_clipboard("hello 中文")
    assert calls == [(command, {"input": "hello 中文".encode(encoding), "check": True})]


@pytest.mark.parametrize(
    "error", [FileNotFoundError("xclip missing"), subprocess.CalledProcessError(1, "xclip")]
)
def test_linux_falls_back_when_xclip_fails(monkeypatch, error):
    copied = []
    monkeypatch.setattr(util.sys, "platform", "linux")

    def failing_run(*args, **kwargs):
        raise error

    monkeypatch.setattr(util.subprocess, "run", failing_run)
    monkeypatch.setattr(util.pyperclip, "copy", copied.append)

    util.copy_to_clipboard("hello 中文")
    assert copied == ["hello 中文"]


def test_linux_backend_failure_has_actionable_error(monkeypatch):
    monkeypatch.setattr(util.sys, "platform", "linux")

    def failing_run(*args, **kwargs):
        raise FileNotFoundError("xclip missing")

    def failing_copy(text):
        raise RuntimeError("no clipboard backend")

    monkeypatch.setattr(util.subprocess, "run", failing_run)
    monkeypatch.setattr(util.pyperclip, "copy", failing_copy)

    with pytest.raises(RuntimeError, match="Clipboard copy failed") as error:
        util.copy_to_clipboard("hello")
    assert str(error.value.__cause__) == "no clipboard backend"
