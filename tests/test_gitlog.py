"""Repository discovery, grouped output, and bounded subprocess cleanup."""

import io
import subprocess

import pytest

from pylistall import cli, gitlog
from pylistall.output import OutputTooLarge
from pylistall.selection import SelectionOptions, parse_binary_policy


def collect(root, recursive, count):
    return cli._build_output(
        root,
        SelectionOptions(recursive, (), (), None),
        parse_binary_policy(None),
        gitlog.GitLogOptions(True, count),
    ).document.git


def test_missing_repository_has_no_log(tmp_path):
    assert collect(tmp_path, True, 2) == ()


def test_nonrecursive_search_only_reads_root(tmp_path, write_file, monkeypatch):
    (tmp_path / ".git").mkdir()
    write_file("child/.git", "gitdir: elsewhere")
    calls = []

    def fake(repo_root, count, **kwargs):
        calls.append((repo_root, count))
        return "a1b2c3d example commit"

    monkeypatch.setattr(gitlog, "_run_git_log", fake)
    logs = collect(tmp_path, False, 2)
    assert calls == [(tmp_path, 2)]
    assert logs[0].title == str((tmp_path / ".git").resolve())
    assert logs[0].text == "a1b2c3d example commit"


def test_recursive_groups_directories_and_worktree_pointers(
    tmp_path, write_file, monkeypatch
):
    (tmp_path / "Z-repo" / ".git").mkdir(parents=True)
    write_file("a-repo/.git", "gitdir: elsewhere")
    calls = []

    def fake(repo_root, count, **kwargs):
        calls.append((repo_root.name, count))
        return f"commit for {repo_root.name}"

    monkeypatch.setattr(gitlog, "_run_git_log", fake)
    logs = collect(tmp_path, True, -1)
    assert calls == [("a-repo", -1), ("Z-repo", -1)]
    assert [log.text for log in logs] == ["commit for a-repo", "commit for Z-repo"]


def test_over_budget_git_is_killed_and_reaped(tmp_path, monkeypatch):
    class Process:
        def __init__(self):
            self.stdout = io.BytesIO(b"x" * 100000)
            self.returncode = None
            self.killed = False
            self.waited = False

        def poll(self):
            return self.returncode

        def kill(self):
            self.killed = True
            self.returncode = -1

        def wait(self):
            self.waited = True
            return self.returncode

    process = Process()
    monkeypatch.setattr(gitlog.subprocess, "Popen", lambda *args, **kwargs: process)

    def budget(size):
        if size > 100:
            raise OutputTooLarge("too large")

    with pytest.raises(OutputTooLarge):
        gitlog._run_git_log(tmp_path, -1, budget, 101)
    assert process.killed and process.waited and process.stdout.closed


def test_real_git_worktree_log_utf8(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(tmp_path),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-q",
            "--allow-empty",
            "-m",
            "中文🙂",
        ],
        check=True,
    )
    assert "中文🙂" in gitlog._run_git_log(tmp_path, 1)


def test_cancelled_git_is_killed_and_reaped(tmp_path, monkeypatch):
    class Stream(io.BytesIO):
        def read1(self, amount):
            raise KeyboardInterrupt()

    class Process:
        stdout = Stream()
        returncode = None
        killed = waited = False

        def poll(self):
            return self.returncode

        def kill(self):
            self.killed = True
            self.returncode = -1

        def wait(self):
            self.waited = True
            return self.returncode

    process = Process()
    monkeypatch.setattr(gitlog.subprocess, "Popen", lambda *args, **kwargs: process)
    with pytest.raises(KeyboardInterrupt):
        gitlog._run_git_log(tmp_path, 1)
    assert process.killed and process.waited and process.stdout.closed
