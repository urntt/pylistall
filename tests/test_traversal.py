"""Real filesystem links, consistent discovery, and recoverable scan failures."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from pylistall import cli, gitlog, traversal
from pylistall.patterns import parse_omit_patterns
from pylistall.selection import (
    SelectionOptions,
    select_files_for_content,
)
from pylistall.tree import render_tree


@pytest.fixture
def link_factory():
    """Only skip Windows symlinks when the OS explicitly denies the privilege."""

    def create(path, target, directory=False):
        try:
            path.symlink_to(target, target_is_directory=directory)
        except OSError as exc:
            if sys.platform == "win32" and getattr(exc, "winerror", None) == 1314:
                pytest.skip("Windows does not grant symbolic-link creation privileges")
            raise
        return path

    return create


def names(snapshot, *, omit=(), include=()):
    return [
        item.display_name
        for item in select_files_for_content(
            snapshot.root,
            SelectionOptions(True, include, omit, None),
            snapshot=snapshot,
        )
    ]


def test_default_links_are_visible_but_never_read(tmp_path, link_factory):
    root = tmp_path / "project"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / ".git").mkdir()
    (outside / "source.py").write_text("external", encoding="utf-8")
    link_factory(root / "folder", outside, True)
    link_factory(root / "file.py", outside / "source.py")
    snapshot = traversal.scan_directory(root, True)
    assert render_tree(snapshot) == "├── file.py@\n└── folder@"
    assert names(snapshot) == []
    assert gitlog._find_git_entries(root, True, snapshot=snapshot) == ([], [])
    assert snapshot.warnings == ()


def test_follow_external_directory_preserves_alias_and_finds_git(
    tmp_path, link_factory
):
    root = tmp_path / "project"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / ".git").write_text("gitdir: elsewhere", encoding="utf-8")
    (outside / "source.py").write_text("external", encoding="utf-8")
    link_factory(root / "alias", outside, True)
    snapshot = traversal.scan_directory(root, True, True)
    assert "alias@/" in render_tree(snapshot)
    assert names(snapshot, omit=(".git",)) == ["alias/source.py"]
    entries, warnings = gitlog._find_git_entries(root, True, snapshot=snapshot)
    assert [entry.git_path for entry in entries] == [root / "alias" / ".git"]
    assert warnings == []


def test_cycle_is_cut_but_noncyclic_aliases_are_preserved(tmp_path, link_factory):
    (tmp_path / "real").mkdir()
    (tmp_path / "real" / "source.py").write_text("source", encoding="utf-8")
    link_factory(tmp_path / "real" / "loop", tmp_path, True)
    link_factory(tmp_path / "alias", tmp_path / "real", True)
    snapshot = traversal.scan_directory(tmp_path, True, True)
    assert names(snapshot) == ["alias/source.py", "real/source.py"]
    assert len([entry for entry in snapshot.entries if entry.skipped == "cycle"]) == 2
    assert len(snapshot.warnings) == 2
    assert len(render_tree(snapshot).splitlines()) == 6


def test_dangling_link_survives_tree_and_reports_only_when_followed(
    tmp_path, link_factory
):
    link_factory(tmp_path / "dangling", tmp_path / "missing")
    ignored = traversal.scan_directory(tmp_path, True)
    followed = traversal.scan_directory(tmp_path, True, True)
    assert render_tree(ignored) == render_tree(followed) == "└── dangling@"
    assert ignored.warnings == ()
    assert names(followed) == []
    assert "Failed to inspect entry" in followed.warnings[0]


def test_omit_checks_real_target_behind_innocent_alias(tmp_path, link_factory):
    (tmp_path / ".env").write_text("synthetic secret", encoding="utf-8")
    link_factory(tmp_path / "innocent.py", tmp_path / ".env")
    snapshot = traversal.scan_directory(tmp_path, True, True)
    assert names(snapshot, omit=parse_omit_patterns([""]), include=("*.py",)) == []
    assert "innocent.py@" in render_tree(snapshot)


def test_explicit_root_link_is_resolved(tmp_path, link_factory):
    target = tmp_path / "real"
    target.mkdir()
    (target / "source.py").write_text("source", encoding="utf-8")
    alias = link_factory(tmp_path / "root", target, True)
    snapshot = traversal.scan_directory(alias, True)
    assert snapshot.root == target.resolve()
    assert names(snapshot) == ["source.py"]


def test_cli_uses_one_scan_for_tree_content_and_git(tmp_path, write_file, monkeypatch):
    write_file("src/main.py", "source")
    (tmp_path / ".git").mkdir()
    scans = []
    original = traversal.os.scandir

    def counted(path):
        scans.append(Path(path))
        return original(path)

    monkeypatch.setattr(traversal.os, "scandir", counted)
    monkeypatch.setattr(cli, "copy_to_clipboard", lambda text: None)
    monkeypatch.setattr(gitlog, "_run_git_log", lambda *args, **kwargs: "synthetic log")
    assert cli.main([str(tmp_path), "-r", "-g", "2"]) == 0
    assert sorted(scans) == sorted([tmp_path, tmp_path / ".git", tmp_path / "src"])


def test_nested_directory_error_preserves_other_entries(
    tmp_path, write_file, monkeypatch
):
    write_file("blocked/file.py", "unread")
    write_file("source.py", "retained")
    original = traversal.os.scandir

    def failing(path):
        if Path(path).name == "blocked":
            raise PermissionError("synthetic access denial")
        return original(path)

    monkeypatch.setattr(traversal.os, "scandir", failing)
    snapshot = traversal.scan_directory(tmp_path, True)
    assert names(snapshot) == ["source.py"]
    assert "blocked/" in render_tree(snapshot)
    assert "Failed to list directory" in snapshot.warnings[0]


@pytest.mark.skipif(sys.platform != "win32", reason="Windows junction integration")
def test_windows_junction_is_not_followed_by_default(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    target = tmp_path / "target"
    target.mkdir()
    (target / "source.py").write_text("external", encoding="utf-8")
    result = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(root / "junction"), str(target)],
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr.decode(errors="replace")
    ignored = traversal.scan_directory(root, True)
    followed = traversal.scan_directory(root, True, True)
    assert render_tree(ignored) == "└── junction@"
    assert names(ignored) == []
    assert names(followed) == ["junction/source.py"]


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="POSIX named-pipe integration")
def test_special_files_are_not_opened(tmp_path):
    os.mkfifo(tmp_path / "fifo")
    snapshot = traversal.scan_directory(tmp_path, True)
    assert render_tree(snapshot) == "└── fifo"
    assert names(snapshot) == []


def test_output_symlink_target_excluded_before_sampling(
    tmp_path, link_factory, monkeypatch
):
    from pylistall import selection

    target = tmp_path / "result"
    target.write_text("previous output", encoding="utf-8")
    link_factory(tmp_path / "alias.py", target)
    snapshot = traversal.scan_directory(tmp_path, True, True)

    def forbidden(path):
        pytest.fail("output target was sampled")

    monkeypatch.setattr(selection, "is_probably_binary", forbidden)
    assert (
        selection.select_files_for_content(
            tmp_path,
            SelectionOptions(True, (), (), None, True),
            snapshot=snapshot,
            excluded=target,
        )
        == []
    )


def test_followed_alias_cannot_bypass_omitted_target_subtree(tmp_path, link_factory):
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "main.py").write_text("synthetic", encoding="utf-8")
    link_factory(tmp_path / "innocent.py", tmp_path / ".venv" / "main.py")
    link_factory(tmp_path / "alias", tmp_path / ".venv", True)
    snapshot = traversal.scan_directory(tmp_path, True, True, omit=(".venv",))
    assert snapshot.entries == ()
    assert snapshot.discovered_count == 3


def test_include_dangling_and_unfollowed_links_by_logical_name(tmp_path, link_factory):
    link_factory(tmp_path / "match.py", tmp_path / "missing")
    link_factory(tmp_path / "other.txt", tmp_path / "missing")
    snapshot = traversal.scan_directory(tmp_path, True)
    assert render_tree(snapshot, ("*.py",)) == "└── match.py@"
    assert names(snapshot, include=("*.py",)) == []
