"""Command behavior, canonical formats, and side effects under failure."""

import pytest

from pylistall import cli, selection
from pylistall.output import escape_path, render_markdown


@pytest.fixture
def copied(monkeypatch):
    texts = []
    monkeypatch.setattr(cli, "copy_to_clipboard", texts.append)
    return texts


def test_default_command_uses_current_directory(
    tmp_path, write_file, monkeypatch, copied, capsys
):
    write_file("main.py", "print('hello')")
    monkeypatch.chdir(tmp_path)
    assert cli.main([]) == 0
    captured = capsys.readouterr()
    assert copied == []
    assert captured.out.startswith(escape_path(str(tmp_path.resolve())) + "\n")
    assert "print('hello')" in captured.out
    assert captured.err == ""


def test_copy_adds_destination_without_changing_stdout(
    tmp_path, write_file, copied, capsys
):
    write_file("main.py", "source")
    assert cli.main([str(tmp_path), "-c"]) == 0
    captured = capsys.readouterr()
    assert captured.out == copied[0]
    assert "Copied to clipboard" in captured.err


@pytest.mark.parametrize("kind", ["missing", "file"])
def test_invalid_root(tmp_path, write_file, copied, capsys, kind):
    target = tmp_path / "target"
    if kind == "file":
        write_file("target", "not a directory")
    assert cli.main([str(target)]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err.startswith("Error:")
    assert not copied


def test_empty_directory_has_explicit_markers(tmp_path, copied, capsys):
    assert cli.main([str(tmp_path)]) == 0
    text = capsys.readouterr().out
    assert "(empty)" in text and "[No files selected]" in text
    assert copied == []


def test_filters_preserve_tree(tmp_path, write_file, copied):
    write_file("src/main.py", "included source")
    write_file("README.md", "excluded readme")
    write_file(".git/HEAD", "excluded git metadata")
    assert cli.main([str(tmp_path), "-r", "-i", "*.py", "-o", "-c"]) == 0
    text = copied[0]
    assert "README.md" in text and ".git/" in text
    assert "### src/main\\.py" in text
    assert "excluded readme" not in text and "excluded git metadata" not in text


def test_output_separates_tree_and_file_contents(tmp_path, write_file, copied):
    write_file("main.py", "source")
    assert cli.main([str(tmp_path), "-c"]) == 0
    assert copied == [
        escape_path(str(tmp_path.resolve())) + "\n\n## Directory tree\n\n"
        "```text\n└── main.py\n```\n\n## Files\n\n"
        "### main\\.py\n\n```python\nsource\n```\n"
    ]


@pytest.mark.parametrize(
    "patterns",
    [["-i", "*.py", "-i", "*.md"], ["-i", "*.py,*.md"], ["-i", " *.py, , *.md "]],
)
def test_include_patterns(tmp_path, write_file, copied, patterns):
    write_file("main.py", "source")
    write_file("README.md", "readme")
    write_file("notes.txt", "notes")
    assert cli.main([str(tmp_path), "-c", *patterns]) == 0
    assert "### main\\.py" in copied[0] and "### README\\.md" in copied[0]
    assert "### notes" not in copied[0]


def test_git_without_repository(tmp_path, copied):
    assert cli.main([str(tmp_path), "-g", "2", "-c"]) == 0
    assert "[No .git found]" in copied[0]


@pytest.mark.parametrize(
    "options",
    [
        ["-p"],
        ["--print"],
        ["-w"],
        ["-d", "bad"],
        ["-d", "root,tree,git,files"],
        ["-d", "root,tree,files"],
        ["-M", "0"],
        ["-M", "-1"],
        ["-m", "-1"],
        ["-g", "0"],
    ],
)
def test_parameter_errors_before_side_effects(options, copied):
    with pytest.raises(SystemExit) as caught:
        cli.parse_args(options)
    assert caught.value.code == 2 and copied == []


def test_disable_skips_sampling_reading_and_git(
    tmp_path, write_file, monkeypatch, copied
):
    write_file("source.py", "never read")

    def forbidden(*args, **kwargs):
        pytest.fail("disabled collector was called")

    monkeypatch.setattr(selection, "is_probably_binary", forbidden)
    monkeypatch.setattr(cli, "read_text", forbidden)
    monkeypatch.setattr(cli.gitlog, "_run_git_log", forbidden)
    assert cli.main([str(tmp_path), "-g", "-d", "files", "-d", "git", "-c"]) == 0
    assert "source.py" in copied[0] and "never read" not in copied[0]
    assert "## Files" not in copied[0] and "## Git log" not in copied[0]


def test_disabled_parts_match_all_destinations(tmp_path, write_file, copied, capsys):
    write_file("source.py", "source")
    target = tmp_path / "result"
    assert cli.main([str(tmp_path), "-d", "root,tree", "-c", "-f", str(target)]) == 0
    assert target.read_text(encoding="utf-8") == copied[0]
    assert copied[0].startswith("\n## Files")
    assert capsys.readouterr().out == ""


def test_exact_budget_and_dry_run(tmp_path, write_file, copied, capsys):
    write_file("source.py", "中文🙂\r\n")
    assert cli.main([str(tmp_path), "-c"]) == 0
    size = len(copied[0].encode("utf-8"))
    capsys.readouterr()
    copied.clear()
    target = tmp_path / "missing" / "output"
    assert cli.main([str(tmp_path), "-D", "-c", "-f", str(target)]) == 0
    captured = capsys.readouterr()
    assert f"{size} UTF-8 bytes" in captured.err
    assert not target.parent.exists() and copied == [] and captured.out == ""
    assert cli.main([str(tmp_path), "-M", str(size), "-c"]) == 0
    capsys.readouterr()
    copied.clear()
    assert cli.main([str(tmp_path), "-M", str(size - 1), "-c", "-f", str(target)]) == 1
    captured = capsys.readouterr()
    assert captured.out == "" and "exceeds" in captured.err
    assert not target.parent.exists() and not copied


def test_streaming_budget_stops_before_later_file(
    tmp_path, write_file, monkeypatch, copied, capsys
):
    write_file("a.txt", "x" * 100000)
    write_file("z.txt", "must not be sampled")
    sampled = []
    original = selection.is_probably_binary

    def sample(path):
        sampled.append(path.name)
        return original(path)

    monkeypatch.setattr(selection, "is_probably_binary", sample)
    assert cli.main([str(tmp_path), "-M", "1000", "-c"]) == 1
    assert sampled == ["a.txt"] and copied == []
    assert capsys.readouterr().out == ""


def test_markdown_dynamic_fences_paths_languages_and_shared_model(tmp_path, write_file):
    write_file("a[1].md", "```python\n中文🙂\n``````\n")
    write_file("unknown.xyz", "plain")
    result = cli._build_output(
        tmp_path,
        selection.SelectionOptions(False, (), (), None),
        selection.parse_binary_policy(None),
        cli.GitLogOptions(False, None),
    )
    assert render_markdown(result.document) == result.text
    assert "### a\\[1\\]\\.md" in result.text
    assert "```````markdown" in result.text
    assert result.document.files[1].language == "text"


def test_partial_destination_failure_is_reported(
    tmp_path, write_file, monkeypatch, capsys
):
    write_file("source.py", "source")
    target = tmp_path / "result"

    def fail(text):
        raise RuntimeError("synthetic clipboard failure")

    monkeypatch.setattr(cli, "copy_to_clipboard", fail)
    assert cli.main([str(tmp_path), "-f", str(target), "-c"]) == 1
    captured = capsys.readouterr()
    assert (
        target.exists()
        and "Saved:" in captured.err
        and "clipboard copy failed" in captured.err
    )
    assert captured.out == ""


def test_file_failure_still_reports_successful_copy(
    tmp_path, monkeypatch, copied, capsys
):
    def fail(*args):
        raise PermissionError("synthetic write failure")

    monkeypatch.setattr(cli, "write_output", fail)
    assert cli.main([str(tmp_path), "-f", str(tmp_path / "result"), "-c"]) == 1
    assert copied and "Copied to clipboard" in capsys.readouterr().err


def test_broken_pipe_is_normal(tmp_path, monkeypatch):
    class Closed:
        def write(self, text):
            raise BrokenPipeError()

        def close(self):
            raise BrokenPipeError()

    monkeypatch.setattr(cli.sys, "stdout", Closed())
    assert cli.main([str(tmp_path)]) == 0


@pytest.mark.parametrize(
    "short,long,value",
    [
        ("-n", "--no-pager", None),
        ("-r", "--recursive", None),
        ("-l", "--follow-links", None),
        ("-i", "--include", "*.py"),
        ("-o", "--omit", "*.txt"),
        ("-b", "--binary", "*.png"),
        ("-m", "--max-bytes", "2"),
        ("-g", "--git-log", "2"),
        ("-c", "--copy", None),
        ("-f", "--file", "custom"),
        ("-d", "--disable", "tree"),
        ("-D", "--dry-run", None),
        ("-M", "--max-output-bytes", "100"),
    ],
)
def test_short_and_long_options_agree(short, long, value):
    values = [] if value is None else [value]
    assert vars(cli.parse_args([short, *values])) == vars(
        cli.parse_args([long, *values])
    )


def test_zero_file_limit_has_truncation_marker(tmp_path, write_file, copied):
    write_file("source.py", "source")
    assert cli.main([str(tmp_path), "-m", "0", "-c"]) == 0
    assert "[...TRUNCATED...]" in copied[0] and "\nsource\n" not in copied[0]


def test_documented_markdown_example(tmp_path, write_file):
    import re
    from dataclasses import replace
    from pathlib import Path

    write_file("README.txt", "Example project.\n")
    write_file("src/main.py", 'print("Hello World!")\n')
    result = cli._build_output(
        tmp_path,
        selection.SelectionOptions(True, (), (), None),
        selection.parse_binary_policy(None),
        cli.GitLogOptions(False, None),
    )
    example = render_markdown(replace(result.document, root="/Users/example/project"))
    root = Path(__file__).resolve().parents[1]
    for name in ("README.md", "README.zh-CN.md"):
        documented = re.search(
            r"````markdown\n(.*?)````", (root / name).read_text(encoding="utf-8"), re.S
        ).group(1)
        assert documented == example
