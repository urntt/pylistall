"""File selection, encoding, and read-limit behavior."""

from pathlib import Path

import pytest

from pylistall.selection import (
    SelectionOptions,
    is_probably_binary,
    parse_binary_policy,
    parse_omit_patterns,
    read_text,
    select_files_for_content,
)


def selected_names(root, *, recursive=False, include=(), omit=(), binary=None):
    """Return displayed names selected by the public selection API."""
    selection = SelectionOptions(recursive, include, omit, None)
    return [
        item.display_name
        for item in select_files_for_content(
            root, selection, parse_binary_policy(binary)
        )
    ]


def test_default_selects_only_direct_text_files(tmp_path, write_file):
    write_file("z.txt", "last")
    write_file("A.py", "first")
    write_file("image.png", b"\x89PNG\x00\xff")
    write_file("nested/child.py", "nested")

    assert selected_names(tmp_path) == ["A.py", "z.txt"]


def test_recursive_selection_uses_relative_paths(tmp_path, write_file):
    write_file("main.py", "root")
    write_file("src/utils.py", "nested")

    assert selected_names(tmp_path, recursive=True) == ["main.py", "src/utils.py"]


@pytest.mark.parametrize("pattern", ["*.py", "src/*.py"])
def test_include_matches_filename_or_relative_path(tmp_path, write_file, pattern):
    write_file("src/main.py", "included")
    write_file("README.md", "omitted")

    assert selected_names(tmp_path, recursive=True, include=(pattern,)) == [
        "src/main.py"
    ]


def test_default_omit_is_opt_in(tmp_path, write_file):
    write_file(".git/HEAD", "ref: refs/heads/main")
    write_file("main.py", "source")

    assert ".git/HEAD" in selected_names(tmp_path, recursive=True)
    assert selected_names(
        tmp_path, recursive=True, omit=parse_omit_patterns([""])
    ) == ["main.py"]


def test_default_and_custom_omit_rules_combine(tmp_path, write_file):
    write_file(".git/HEAD", "ref: refs/heads/main")
    write_file("README.md", "readme")
    write_file("test_main.py", "tests")
    write_file("main.py", "source")

    assert selected_names(
        tmp_path,
        recursive=True,
        omit=parse_omit_patterns(["", " README.md, test_* "]),
    ) == ["main.py"]


@pytest.mark.parametrize("binary", [None, "", "*.png", "*.zip"])
def test_omit_overrides_binary_and_include(tmp_path, write_file, binary):
    write_file("image.png", b"\x00\xff")

    assert selected_names(
        tmp_path, include=("*.png",), omit=("*.png",), binary=binary
    ) == []


def test_include_can_force_binary_without_binary_flag(tmp_path, write_file):
    write_file("image.png", b"\x00\xff")
    write_file("archive.zip", b"\x00\xff")

    assert selected_names(tmp_path, include=("*.png",)) == ["image.png"]


@pytest.mark.parametrize(
    ("binary", "expected"),
    [
        (None, ["main.py"]),
        ("", ["archive.zip", "image.png", "main.py"]),
        ("*.png", ["image.png", "main.py"]),
        ("*.png, *.zip", ["archive.zip", "image.png", "main.py"]),
    ],
)
def test_binary_policy_preserves_text_files(tmp_path, write_file, binary, expected):
    write_file("main.py", "source")
    write_file("image.png", b"\x00\xff")
    write_file("archive.zip", b"\x00\xff")

    assert selected_names(tmp_path, binary=binary) == expected


@pytest.mark.parametrize(
    ("name", "content", "expected"),
    [
        ("empty.txt", b"", False),
        ("plain.txt", b"hello\n", False),
        ("unicode.txt", "中文内容\n".encode("utf-8"), False),
        ("nul.txt", b"hello\x00world", True),
        ("raw.txt", b"\xff" * 20, True),
        ("image.png", b"text with a binary extension", True),
    ],
)
def test_binary_detection(name, content, expected, write_file):
    assert is_probably_binary(write_file(name, content)) is expected


@pytest.mark.parametrize("limit", [None, 5, 6])
def test_read_within_limit_is_not_truncated(write_file, limit):
    assert read_text(write_file("message.txt", "hello"), limit) == "hello"


def test_read_over_limit_is_truncated_and_marked(write_file):
    content = read_text(write_file("message.txt", "abcdef"), 3)

    assert content.startswith("abc\n")
    assert "[...TRUNCATED...]" in content
    assert "def" not in content


def test_read_replaces_invalid_utf8(write_file):
    assert read_text(write_file("message.txt", b"hello\xff"), None) == "hello\ufffd"


def test_read_failure_is_visible(tmp_path: Path):
    assert read_text(tmp_path / "missing.txt", None).startswith("[Failed to read file:")


def test_default_omit_excludes_root_tooling_files(tmp_path, write_file):
    for name in (".venv/config.txt", "node_modules/pkg/index.js", ".gitignore"):
        write_file(name, "tooling")
    write_file("main.py", "source")

    assert selected_names(
        tmp_path, recursive=True, omit=parse_omit_patterns([""])
    ) == ["main.py"]


@pytest.mark.parametrize("prefix", ["", "nested/"])
@pytest.mark.parametrize(
    "tooling_path",
    [
        ".venv/config.txt",
        "__pycache__/source.txt",
        "node_modules/pkg/index.js",
        "build/artifact.txt",
        "example.egg-info/metadata.txt",
        ".gitignore",
    ],
)
def test_default_omit_covers_root_and_nested_tooling(
    tmp_path, write_file, prefix, tooling_path
):
    write_file(prefix + tooling_path, "tooling")
    write_file("main.py", "source")

    assert selected_names(
        tmp_path, recursive=True, omit=parse_omit_patterns([""])
    ) == ["main.py"]


def test_custom_double_star_pattern_keeps_existing_matching(tmp_path, write_file):
    write_file(".venv/config.txt", "root environment")
    write_file("nested/.venv/config.txt", "nested environment")

    assert selected_names(
        tmp_path, recursive=True, omit=parse_omit_patterns(["**/.venv/**"])
    ) == [".venv/config.txt"]


@pytest.mark.parametrize(
    "content",
    [
        "中" * 3000,
        "A" + "é" * 5000,
        "A" + "😀" * 2500,
        "AA" + "😀" * 2500,
        "AAA" + "😀" * 2500,
    ],
    ids=["chinese-tail", "accent-tail", "emoji-tail-3", "emoji-tail-2", "emoji-tail-1"],
)
def test_valid_utf8_at_sample_boundary_is_text(write_file, content):
    path = write_file("unicode.txt", content)

    assert not is_probably_binary(path)


@pytest.mark.parametrize(
    "content",
    [b"\xe4\xb8", ("中" * 2730).encode("utf-8") + b"\xe4\xb8"],
    ids=["short-incomplete", "sample-size-incomplete"],
)
def test_incomplete_utf8_at_eof_is_not_accepted_as_valid_text(write_file, content):
    assert is_probably_binary(write_file("incomplete.txt", content))


def test_invalid_utf8_inside_sample_is_not_ignored(write_file):
    content = ("中" * 3000).encode("utf-8")
    content = content[:300] + b"\xff" + content[301:]

    assert is_probably_binary(write_file("invalid.txt", content))
