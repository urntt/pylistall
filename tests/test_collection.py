"""Name views, real pruning, independent Git, and bounded binary expansion."""

import base64
import itertools
from pathlib import Path, PurePosixPath, PureWindowsPath

import pytest

from pylistall import cli, selection, traversal, viewer
from pylistall.names import inline_code, project_name, visible_name
from pylistall.output import OutputTooLarge, render_markdown
from pylistall.patterns import flatten_patterns, parse_omit_patterns
from pylistall.tree import render_tree


def collect(
    root,
    *,
    include=(),
    omit=(),
    binary=None,
    disabled=(),
    maximum=None,
    limit=None,
    git=False,
    report=None,
    follow=False,
    excluded=None,
):
    return cli._build_output(
        root,
        selection.SelectionOptions(True, include, omit, limit, follow),
        selection.parse_binary_policy(binary),
        cli.GitLogOptions(git, 2),
        disabled=disabled,
        maximum=maximum,
        report=report,
        excluded=excluded,
    )


@pytest.mark.parametrize("pattern", ["src", "src/", "src/**"])
def test_omit_prunes_before_scandir(tmp_path, write_file, monkeypatch, pattern):
    write_file("src/deep/main.py", "never enumerated")
    write_file("keep.py", "keep")
    scans = []
    original = traversal.os.scandir

    def scanned(path):
        scans.append(Path(path))
        return original(path)

    monkeypatch.setattr(traversal.os, "scandir", scanned)
    result = collect(tmp_path, include=("*.py",), omit=(pattern,))
    assert scans == [tmp_path]
    assert "src" not in result.document.tree
    assert result.document.discovered_count == 2
    assert [block.title for block in result.document.files] == ["keep.py"]


def test_include_retains_only_matching_leaves_and_ancestors(tmp_path, write_file):
    write_file("src/deep/main.py", "source")
    write_file("src/readme.txt", "readme")
    write_file("other/file.txt", "other")
    (tmp_path / "empty").mkdir()
    result = collect(tmp_path, include=("src/*.py",))
    assert result.document.tree == "└── src/\n    └── deep/\n        └── main.py"
    assert result.document.discovered_count == 7
    assert [block.title for block in result.document.files] == ["src/deep/main.py"]
    result = collect(tmp_path, omit=("src/*.py",))
    assert "src/" in result.document.tree and "readme.txt" in result.document.tree
    assert "main.py" not in result.document.tree


def test_root_exemption_and_default_venv_pruning(tmp_path, monkeypatch):
    root = tmp_path / ".venv"
    (root / ".venv").mkdir(parents=True)
    (root / ".venv" / "nested.py").write_text("nested", encoding="utf-8")
    (root / "main.py").write_text("source", encoding="utf-8")
    result = collect(root, omit=parse_omit_patterns([""]))
    assert result.document.project_name == ".venv"
    assert result.document.tree == "└── main.py"
    assert result.document.discovered_count == 2
    assert result.document.collected_count == 1


def test_pattern_normalization_and_custom_root_difference(tmp_path, write_file):
    assert flatten_patterns([" *.py, ,*.py ", "*.md"]) == ("*.py", "*.md")
    default = parse_omit_patterns(["", "*.tmp", "*.tmp"])
    assert ".venv/**" in default and "**/.venv/**" in default
    assert default.count("*.tmp") == 1
    write_file(".venv/config.txt", "root")
    write_file("nested/.venv/config.txt", "nested")
    custom = collect(tmp_path, omit=parse_omit_patterns(["**/.venv/**"]))
    assert [b.title for b in custom.document.files] == [".venv/config.txt"]
    assert "nested" in custom.document.tree
    assert collect(tmp_path, omit=default).document.files == ()


@pytest.mark.parametrize(
    "disabled", [("tree", "git", "files"), ("path", "tree", "git", "files")]
)
def test_minimal_document_does_not_scan_or_sample(tmp_path, monkeypatch, disabled):
    def forbidden(*args, **kwargs):
        pytest.fail("minimal document must not collect entries")

    monkeypatch.setattr(cli, "scan_directory", forbidden)
    monkeypatch.setattr(cli, "is_probably_binary", forbidden)
    monkeypatch.setattr(cli.gitlog, "_run_git_log", forbidden)
    result = collect(tmp_path, disabled=disabled, git=True)
    assert result.text.startswith(f"# {inline_code(tmp_path.name)}\n")
    assert result.document.discovered_count == 0
    if "path" in disabled:
        assert result.text == f"# {inline_code(tmp_path.name)}\n"


@pytest.mark.parametrize(
    "disabled",
    [
        parts
        for length in range(5)
        for parts in itertools.combinations(("path", "tree", "git", "files"), length)
    ],
)
def test_all_disable_combinations_share_canonical_document(tmp_path, disabled):
    assert cli.parse_args(["-d", ",".join(disabled)]).disable == disabled
    result = collect(tmp_path, disabled=disabled, git=True)
    assert result.text == render_markdown(result.document)
    assert ("## Files" in result.text) == ("files" not in disabled)
    assert ("## Git log" in result.text) == ("git" not in disabled)
    assert ("```bash" in result.text) == (
        "path" not in disabled or "tree" not in disabled
    )


def test_git_ignores_include_and_omitted_metadata_but_not_pruned_parent(
    tmp_path, write_file, monkeypatch
):
    write_file(".git/HEAD", "metadata")
    write_file("repo/.git", "gitdir: elsewhere")
    write_file("omitted/.git/HEAD", "metadata")
    write_file("source.py", "source")
    calls = []
    monkeypatch.setattr(
        cli.gitlog,
        "_run_git_log",
        lambda path, *args, **kwargs: calls.append(path) or "log",
    )
    result = collect(tmp_path, include=("*.py",), omit=(".git", "omitted"), git=True)
    assert calls == [tmp_path, tmp_path / "repo"]
    assert result.document.tree == "└── source.py"
    assert ".git" in result.document.git[0].title
    plain = traversal.scan_directory(tmp_path, True, collect_git=False)
    assert ".git/" in render_tree(plain)
    assert any(e.relative_path.as_posix() == ".git/HEAD" for e in plain.entries)


@pytest.mark.parametrize(
    "binary,include,expanded",
    [
        (None, ("*.png",), False),
        ("", ("*.png",), True),
        ("*.zip", ("*.png",), False),
        ("*.png", ("*.py",), False),
    ],
)
def test_binary_permission_does_not_add_candidates(
    tmp_path, write_file, binary, include, expanded
):
    write_file("image.png", b"\x00\xff")
    write_file("main.py", "source")
    result = collect(tmp_path, include=include, binary=binary)
    assert result.document.candidate_count == 1
    block = result.document.files[0]
    if include == ("*.py",):
        assert block.title == "main.py" and "image.png" not in result.document.tree
    elif expanded:
        assert (
            block.encoding == "Base64" and base64.b64decode(block.text) == b"\x00\xff"
        )
    else:
        assert block.text is None and block.error is None
        assert "### `image.png`\n\n[Binary content not expanded;" in result.text
        assert "Encoding: Base64" not in result.text
        assert result.document.collected_count == 0


@pytest.mark.parametrize("length", [0, 1, 2, 3, 4, 4095, 4096, 4097, 8195])
@pytest.mark.parametrize("limit", [None, 0, 1, 2, 3, 4096, 8195])
def test_base64_raw_prefix_and_padding(tmp_path, length, limit):
    data = bytes(range(256)) * (length // 256) + bytes(range(length % 256))
    path = tmp_path / "data.bin"
    path.write_bytes(data)
    result = collect(tmp_path, binary="", limit=limit)
    block = result.document.files[0]
    assert base64.b64decode(block.text, validate=True) == data[:limit]
    assert block.text == base64.b64encode(data[:limit]).decode("ascii")
    assert block.truncated == (limit is not None and length > limit)
    assert "\n" not in block.text and "TRUNCATED" not in block.text
    assert result.document.collected_count == 1
    assert result.text == render_markdown(result.document)
    if block.truncated:
        assert "```\n\n[...TRUNCATED...]\n" in result.text


def test_empty_text_and_unexpanded_binary_are_distinct(tmp_path, write_file):
    write_file("a.txt", "")
    write_file("b.bin", b"\x00")
    result = collect(tmp_path)
    assert result.document.files[0].text == ""
    assert result.document.files[1].text is None
    assert (result.file_count, result.document.collected_count) == (2, 1)
    assert "### `a.txt`\n\n```text\n\n```" in result.text


def test_disabled_files_still_filters_tree_without_reading(
    tmp_path, write_file, monkeypatch
):
    write_file("src/main.py", "unread")
    write_file("README.md", "unread")

    def forbidden(*args, **kwargs):
        pytest.fail("disabled Files sampled or read content")

    monkeypatch.setattr(cli, "is_probably_binary", forbidden)
    monkeypatch.setattr(cli, "read_content", forbidden)
    result = collect(tmp_path, include=("*.py",), disabled=("files",))
    assert result.document.tree == "└── src/\n    └── main.py"
    assert result.document.files is None and result.document.candidate_count == 0


def test_base64_destinations_and_dry_run_are_byte_identical(
    tmp_path, write_file, monkeypatch, capsys
):
    write_file("source.bin", b"\x00\xff\x01\x02")
    target = tmp_path / "export"
    copied = []
    monkeypatch.setattr(cli, "copy_to_clipboard", copied.append)
    options = [str(tmp_path), "-b", "-m", "2", "-d", "tree", "-f", str(target), "-c"]
    assert cli.main(options) == 0
    assert target.read_bytes() == copied[0].encode("utf-8")
    assert capsys.readouterr().out == ""
    copied.clear()
    size = target.stat().st_size
    assert cli.main([*options, "-w", "-D"]) == 0
    assert f"{size} UTF-8 bytes" in capsys.readouterr().err
    assert copied == [] and target.stat().st_size == size
    assert cli.main([*options, "-w", "-M", str(size - 1)]) == 1
    assert copied == [] and target.stat().st_size == size


def test_authorized_binary_read_failure_is_not_encoded(
    tmp_path, write_file, monkeypatch
):
    path = write_file("file.bin", b"\x00")
    original = Path.open

    def opening(self, *args, **kwargs):
        if self == path:
            raise PermissionError("synthetic failure")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", opening)
    result = collect(tmp_path, binary="")
    block = result.document.files[0]
    assert block.error and block.encoding == "utf-8"
    assert (
        "Failed to read file" in result.text and "Encoding: Base64" not in result.text
    )
    assert result.document.collected_count == 0


@pytest.mark.parametrize(
    "name,expected",
    [
        (PurePosixPath("/"), "/"),
        (PureWindowsPath("C:/"), "C:\\"),
        (PureWindowsPath("//server/share/"), "share"),
    ],
)
def test_filesystem_root_titles_without_scanning(name, expected):
    assert project_name(name) == expected


@pytest.mark.parametrize(
    "name,expected",
    [
        ("normal [a].txt", "`normal [a].txt`"),
        ("a`b", "``a`b``"),
        ("`a`", "`` `a` ``"),
        (" a ", "`  a  `"),
        ("a\n\r\t\x1bb", r"`a\n\r\t\x1bb`"),
    ],
)
def test_literal_inline_names(name, expected):
    assert inline_code(name) == expected
    assert "\x1b" not in visible_name(name)


def test_binary_exact_budget_and_early_stop(tmp_path, write_file, monkeypatch):
    write_file("a.bin", bytes(range(256)) * 50)
    write_file("z.bin", b"\x00")
    result = collect(tmp_path, binary="", limit=4)
    size = len(result.text.encode("utf-8"))
    assert collect(tmp_path, binary="", limit=4, maximum=size).text == result.text
    with pytest.raises(OutputTooLarge):
        collect(tmp_path, binary="", limit=4, maximum=size - 1)
    seen = []
    original = cli.is_probably_binary
    monkeypatch.setattr(
        cli, "is_probably_binary", lambda path: seen.append(path.name) or original(path)
    )
    with pytest.raises(OutputTooLarge):
        collect(tmp_path, binary="", maximum=500)
    assert seen == ["a.bin"]


def test_progress_callbacks_count_files_instead_of_blocks(tmp_path, write_file):
    write_file("a.bin", b"\x00" * 9000)
    write_file("b.txt", "")
    write_file("c.bin", b"\x00")
    events = []
    result = collect(
        tmp_path,
        binary="a.bin",
        report=lambda *args, **kwargs: events.append((args, kwargs)),
    )
    stages = [args[0] for args, _ in events]
    assert stages.index("scan") < stages.index("tree") < stages.index("files")
    assert events[-1][1] == {"checked": 3, "collected": 2}
    assert stages.count("files") > 6
    assert (
        result.document.candidate_count,
        result.document.checked_count,
        result.document.collected_count,
    ) == (3, 3, 2)


def test_binary_terminal_has_same_encoding_and_external_marker(tmp_path, write_file):
    write_file("image.png", b"\x00\xff\x01")
    result = collect(tmp_path, binary="", limit=2)
    text = viewer.render_terminal(result.document, width=100, color=False)
    assert "Encoding: Base64" in text and "AP8=" in text
    assert "[...TRUNCATED...]" in text and "```" not in text
