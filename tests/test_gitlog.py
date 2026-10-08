"""Repository discovery and grouped log behavior."""

from pylistall import gitlog


def test_missing_repository_has_no_log(tmp_path):
    assert gitlog.build_git_log_sections(tmp_path, recursive=True, count=2) == ("", [])


def test_nonrecursive_search_only_reads_root_repository(
    tmp_path, write_file, monkeypatch
):
    (tmp_path / ".git").mkdir()
    write_file("child/.git", "gitdir: elsewhere")
    calls = []

    def fake_log(repo_root, count):
        calls.append((repo_root, count))
        return "a1b2c3d example commit"

    monkeypatch.setattr(gitlog, "_run_git_log", fake_log)

    text, warnings = gitlog.build_git_log_sections(tmp_path, recursive=False, count=2)
    assert calls == [(tmp_path, 2)]
    assert text == f"{(tmp_path / '.git').resolve()}\na1b2c3d example commit"
    assert warnings == []


def test_recursive_logs_group_git_directories_and_files(
    tmp_path, write_file, monkeypatch
):
    (tmp_path / "Z-repo" / ".git").mkdir(parents=True)
    write_file("a-repo/.git", "gitdir: elsewhere")
    calls = []

    def fake_log(repo_root, count):
        calls.append((repo_root.name, count))
        return f"commit for {repo_root.name}"

    monkeypatch.setattr(gitlog, "_run_git_log", fake_log)

    text, warnings = gitlog.build_git_log_sections(tmp_path, recursive=True, count=None)
    assert calls == [("a-repo", -1), ("Z-repo", -1)]
    assert text == (
        f"{(tmp_path / 'a-repo' / '.git').resolve()}\ncommit for a-repo\n\n"
        f"{(tmp_path / 'Z-repo' / '.git').resolve()}\ncommit for Z-repo"
    )
    assert warnings == []
