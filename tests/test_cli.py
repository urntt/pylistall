"""End-to-end command behavior with clipboard calls captured."""

import pytest

from pylistall import cli


@pytest.fixture
def copied(monkeypatch):
    """Capture copies without touching the user's real clipboard."""
    texts = []
    monkeypatch.setattr(cli, "copy_to_clipboard", texts.append)
    return texts


def test_default_command_uses_current_directory(tmp_path, write_file, monkeypatch, copied, capsys):
    write_file("main.py", "print('hello')")
    monkeypatch.chdir(tmp_path)

    assert cli.main([]) == 0
    assert len(copied) == 1
    assert copied[0].startswith(str(tmp_path.resolve()) + "\n")
    assert "print('hello')" in copied[0]
    assert capsys.readouterr().out == (
        f"Copied to clipboard: {tmp_path.resolve()} (files: 1)\n"
    )


def test_print_preview_precedes_copy_confirmation(tmp_path, write_file, copied, capsys):
    write_file("main.py", "source")

    assert cli.main([str(tmp_path), "-p"]) == 0
    stdout = capsys.readouterr().out
    assert stdout.startswith(copied[0] + "\n")
    assert stdout.endswith(f"Copied to clipboard: {tmp_path.resolve()} (files: 1)\n")


@pytest.mark.parametrize("kind", ["missing", "file"])
def test_invalid_target_returns_error_without_copy(tmp_path, write_file, copied, capsys, kind):
    target = tmp_path / "target"
    if kind == "file":
        write_file("target", "not a directory")

    assert cli.main([str(target)]) == 2
    assert copied == []
    assert capsys.readouterr().out.startswith("Error:")


def test_empty_directory_has_explicit_marker(tmp_path, copied):
    assert cli.main([str(tmp_path)]) == 0
    assert copied == [f"{tmp_path.resolve()}\n(empty)\n"]


def test_filters_change_contents_and_preserve_real_tree(tmp_path, write_file, copied):
    write_file("src/main.py", "included source")
    write_file("README.md", "excluded readme")
    write_file(".git/HEAD", "excluded git metadata")

    assert cli.main([str(tmp_path), "-r", "-i", "*.py", "-o"]) == 0
    output = copied[0]
    assert "README.md" in output and ".git/" in output
    assert "`src/main.py`:" in output
    assert "excluded readme" not in output
    assert "excluded git metadata" not in output


def test_output_separates_tree_and_file_contents(tmp_path, write_file, copied):
    write_file("main.py", "source")

    assert cli.main([str(tmp_path)]) == 0
    fence = "`" * 10
    assert copied == [
        f"{tmp_path.resolve()}\n{fence}\n└── main.py\n{fence}\n\n"
        f"`main.py`:\n{fence}\nsource\n{fence}\n"
    ]


def test_repeated_include_selects_both_types(tmp_path, write_file, copied):
    write_file("main.py", "source")
    write_file("README.md", "readme")
    write_file("notes.txt", "notes")

    assert cli.main([str(tmp_path), "-i", "*.py", "-i", "*.md"]) == 0
    assert "`main.py`:" in copied[0]
    assert "`README.md`:" in copied[0]
    assert "`notes.txt`:" not in copied[0]


def test_git_log_without_repository_has_explicit_marker(tmp_path, copied):
    assert cli.main([str(tmp_path), "-g", "2"]) == 0
    assert "[No .git found]" in copied[0]


def test_git_warnings_are_printed(tmp_path, monkeypatch, copied, capsys):
    monkeypatch.setattr(
        cli,
        "build_git_log_sections",
        lambda **kwargs: ("example git log", ["example warning"]),
    )

    assert cli.main([str(tmp_path), "-g"]) == 0
    assert "example git log" in copied[0]
    assert "Warning: example warning\n" in capsys.readouterr().out


@pytest.mark.parametrize(
    "include_args",
    [
        ["-i", "*.py,*.md"],
        ["-i", " *.py, , *.md "],
        ["-i", "*.py,*.txt", "-i", "*.md"],
    ],
)
def test_comma_separated_include_selects_both_types(
    tmp_path, write_file, copied, include_args
):
    write_file("main.py", "source")
    write_file("README.md", "readme")

    assert cli.main([str(tmp_path), *include_args]) == 0
    assert "`main.py`:" in copied[0]
    assert "`README.md`:" in copied[0]
