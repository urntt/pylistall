"""Destination interpretation and transactional file writes."""

import os
from datetime import datetime
from pathlib import Path

import pytest

from pylistall import cli, destinations


@pytest.fixture
def local_time(monkeypatch):
    class Clock:
        calls = 0

        @classmethod
        def now(cls):
            cls.calls += 1
            return datetime(2026, 10, 8, 9, 10, 11)

    monkeypatch.setattr(destinations, "datetime", Clock)
    return Clock


@pytest.mark.parametrize("raw", ["", ".", "folder" + os.sep, "custom", "folder/custom"])
def test_path_interpretation(tmp_path, local_time, raw):
    path = destinations.resolve_destination(raw, tmp_path)
    expected = tmp_path / (raw or ".")
    if raw in ("", ".", "folder" + os.sep):
        expected /= "pylistall-output-2026-10-08-09-10-11.md"
    assert path == expected
    assert local_time.calls == 1


def test_absolute_directory_and_tilde(tmp_path, monkeypatch, local_time):
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    assert (
        destinations.resolve_destination(str(tmp_path), Path.cwd()).parent == tmp_path
    )
    assert (
        destinations.resolve_destination("~/custom", Path.cwd()) == tmp_path / "custom"
    )


def test_bare_file_uses_invocation_directory(tmp_path, monkeypatch, local_time, capsys):
    root = tmp_path / "root"
    root.mkdir()
    monkeypatch.chdir(tmp_path)
    assert cli.main([str(root), "-f"]) == 0
    target = tmp_path / "pylistall-output-2026-10-08-09-10-11.md"
    assert target.exists() and not list(root.iterdir())
    assert capsys.readouterr().out == ""
    assert cli.main([str(root), "-f"]) == 1


def test_parent_creation_encoding_collision_and_overwrite(tmp_path):
    target = tmp_path / "new" / "custom"
    destinations.write_output(target, "中文🙂\n", False)
    assert target.read_bytes() == "中文🙂\n".encode("utf-8")
    with pytest.raises(FileExistsError):
        destinations.write_output(target, "replacement", False)
    destinations.write_output(target, "replacement\n", True)
    assert target.read_bytes() == b"replacement\n"
    assert list(target.parent.iterdir()) == [target]
    with pytest.raises(IsADirectoryError):
        destinations.write_output(target.parent, "bad", True)


@pytest.mark.parametrize("overwrite", [False, True])
def test_failed_write_cleans_partial_and_keeps_original(
    tmp_path, monkeypatch, overwrite
):
    target = tmp_path / "output"
    if overwrite:
        target.write_text("original", encoding="utf-8")

    def fail(fd):
        raise OSError("synthetic flush failure")

    monkeypatch.setattr(destinations.os, "fsync", fail)
    with pytest.raises(OSError):
        destinations.write_output(target, "new", overwrite)
    assert list(tmp_path.iterdir()) == ([target] if overwrite else [])
    if overwrite:
        assert target.read_text(encoding="utf-8") == "original"


def test_replace_failure_keeps_original(tmp_path, monkeypatch):
    target = tmp_path / "output"
    target.write_text("original", encoding="utf-8")

    def fail(*args):
        raise PermissionError("synthetic replace failure")

    monkeypatch.setattr(destinations.os, "replace", fail)
    with pytest.raises(PermissionError):
        destinations.write_output(target, "new", True)
    assert target.read_text(encoding="utf-8") == "original"
    assert list(tmp_path.iterdir()) == [target]


def test_existing_output_and_hardlink_alias_excluded(tmp_path, monkeypatch):
    target = tmp_path / "result"
    target.write_text("previous output", encoding="utf-8")
    os.link(target, tmp_path / "alias")
    (tmp_path / "source.py").write_text("source", encoding="utf-8")
    copied = []
    monkeypatch.setattr(cli, "copy_to_clipboard", copied.append)
    assert cli.main([str(tmp_path), "-f", str(target), "-w", "-c"]) == 0
    assert "previous output" not in copied[0]
    assert "result" in copied[0] and "alias" in copied[0]
    assert "### `result`" not in copied[0] and "### `alias`" not in copied[0]
