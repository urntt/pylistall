"""XML and JSON formats share collection, budgets and destinations with Markdown."""

import json
import os

import pytest

from pylistall import cli, destinations, viewer
from pylistall.output import (
    FORMATS,
    MARKDOWN,
    ContentBlock,
    OutputDocument,
    estimate_tokens,
    render,
)
from pylistall.selection import SelectedFile

JSON = FORMATS["json"]
XML = FORMATS["xml"]

# Characters that str.splitlines() treats as boundaries but JSON keeps literal.
TRICKY = 'quote " slash \\ tab \t nel \x85 ls \u2028 vt \x0b 中文🙂\n'


@pytest.fixture
def copied(monkeypatch):
    texts = []
    monkeypatch.setattr(cli, "copy_to_clipboard", texts.append)
    return texts


@pytest.fixture
def document():
    return OutputDocument(
        'proj"ect',
        "/root/proj",
        "├── a.py\n└── b.png",
        (
            ContentBlock("/root/proj/.git", "abc123 first\n"),
            ContentBlock("/x/.git", ""),
        ),
        (
            ContentBlock("a.py", TRICKY, "python", "utf-8"),
            ContentBlock("b.png", "iVBORw==", "text", "Base64", truncated=True),
            ContentBlock("c.bin", None),
            ContentBlock(
                "d.txt",
                "[Failed to read file: denied]",
                "text",
                "utf-8",
                error="denied",
            ),
            ContentBlock("e.txt", "", "text", "utf-8"),
        ),
    )


def expected_json(document):
    value = {"project": document.project_name}
    if document.path is not None:
        value["path"] = document.path
    if document.tree is not None:
        value["tree"] = document.tree
    if document.git is not None:
        value["git"] = [{"path": b.title, "log": b.text} for b in document.git]
    if document.files is not None:
        value["files"] = [
            {
                "path": b.title,
                "language": b.language,
                "encoding": b.encoding,
                "truncated": b.truncated,
                "error": b.error,
                "content": b.text,
            }
            for b in document.files
        ]
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


@pytest.mark.parametrize(
    "parts",
    [
        {},
        {"path": None, "tree": None},
        {"git": None, "files": None},
        {"git": (), "files": ()},
        {"path": None, "tree": None, "git": None, "files": None},
    ],
)
def test_json_pieces_equal_json_dumps(document, parts):
    from dataclasses import replace

    document = replace(document, **parts)
    text = render(document, JSON)
    assert text == expected_json(document)
    assert json.loads(text)["project"] == document.project_name


def test_xml_escapes_attributes_and_keeps_bodies_verbatim(document):
    from dataclasses import replace

    document = replace(
        document,
        files=(ContentBlock('a"&<>\x1b.py', "if a < b && c:\n", "python", "utf-8"),),
        git=(),
    )
    text = render(document, XML)
    assert text.startswith('<project name="proj&quot;ect">\n<path>/root/proj</path>\n')
    assert '<file path="a&quot;&amp;&lt;&gt;\\x1b.py" language="python">\n' in text
    assert "if a < b && c:\n</file>\n" in text
    assert "<git_log>\n[No .git found]\n</git_log>\n" in text
    assert text.endswith("</files>\n</project>\n")


def test_xml_marks_binary_base64_truncation_and_errors(document):
    text = render(document, XML)
    assert '<file path="b.png" encoding="base64" truncated="true">\niVBORw==\n' in text
    assert '<file path="c.bin" binary="true">\n[Binary content not expanded' in text
    assert '<file path="d.txt" language="text" error="true">\n[Failed' in text
    assert '<file path="e.txt" language="text">\n\n</file>\n' in text
    assert '<repository path="/x/.git">\n\n</repository>\n' in text


@pytest.fixture
def project(tmp_path, write_file):
    write_file("newline.py", "print(1)\n")
    write_file("no_newline.txt", "tail")
    write_file("empty.txt", "")
    write_file("quotes.json", '{"key": "\\\\ \\""}\n' + TRICKY)
    write_file("image.png", b"\x89PNG\r\n\x1a\n\x00\x00\x00" * 5)
    write_file("data.bin", bytes(range(256)))
    return tmp_path


@pytest.mark.parametrize("name", sorted(FORMATS))
@pytest.mark.parametrize(
    "options",
    [[], ["-b"], ["-b", "-m", "4"], ["-m", "2"], ["-g"], ["-d", "path,tree"]],
)
def test_incremental_output_is_exact_at_every_budget_boundary(
    project, copied, capsys, name, options
):
    base = [str(project), "-F", name, *options]
    assert cli.main([*base, "-c"]) == 0
    text = copied[0]
    copied.clear()
    size = len(text.encode("utf-8"))
    # The streamed lower bounds must never reject an output that fits exactly.
    assert cli.main([*base, "-M", str(size), "-c"]) == 0
    assert copied == [text]
    copied.clear()
    capsys.readouterr()
    assert cli.main([*base, "-M", str(size - 1), "-c"]) == 1
    label = FORMATS[name].label
    assert f"{label} exceeds --max-output-bytes {size - 1}" in capsys.readouterr().err
    assert copied == []
    if name == "json":
        json.loads(text)


def test_json_exports_surrogate_names_at_exact_budget(tmp_path, monkeypatch, capsys):
    root = tmp_path / "project"
    root.mkdir()
    source = root / "source.txt"
    source.write_text("中文🙂", encoding="utf-8")
    # Reproduce what the filesystem can return, even where creating such a
    # filename is unsupported. The CLI still reads and exports a real file.
    selected = SelectedFile(source, source.relative_to(root), "name\udcff.txt")
    monkeypatch.setattr(cli, "iter_selected_files", lambda *args, **kwargs: [selected])
    args = [str(root), "-F", "json"]

    assert cli.main(args) == 0
    exported = capsys.readouterr().out.encode("utf-8")
    entry = json.loads(exported)["files"][0]
    assert entry["path"] == r"name\udcff.txt"
    assert entry["content"] == "中文🙂"

    destination = tmp_path / "result.json"
    assert cli.main([*args, "-M", str(len(exported) - 1), "-f", str(destination)]) == 1
    assert not destination.exists()
    assert cli.main([*args, "-M", str(len(exported)), "-f", str(destination)]) == 0
    assert destination.read_bytes() == exported


@pytest.mark.parametrize("name", sorted(FORMATS))
def test_collection_text_matches_rendered_model(project, name):
    fmt = FORMATS[name]
    result = cli._build_output(
        project,
        cli.SelectionOptions(True, (), (), 3),
        cli.parse_binary_policy(""),
        cli.GitLogOptions(True, None),
        output_format=fmt,
    )
    assert result.text == render(result.document, fmt)
    assert result.output_format is fmt


@pytest.mark.parametrize("name", sorted(FORMATS))
def test_bare_file_uses_format_suffix_and_omits_previous_outputs(
    project, monkeypatch, capsys, name
):
    monkeypatch.chdir(project)
    previous = [
        project / f"pylistall-output-2000-01-01-00-00-00{suffix}"
        for suffix in (".md", ".xml", ".json")
    ]
    for path in previous:
        path.write_text("old", encoding="utf-8")
    assert cli.main([".", "-o", "-F", name, "-f"]) == 0
    created = sorted(set(project.glob("pylistall-output-*")) - set(previous))
    assert len(created) == 1 and created[0].suffix == FORMATS[name].suffix
    text = created[0].read_text(encoding="utf-8")
    assert "pylistall-output-2000" not in text
    assert capsys.readouterr().out == ""


def test_custom_file_names_keep_their_extension(tmp_path):
    assert destinations.resolve_destination("context", tmp_path, ".json") == (
        tmp_path / "context"
    )


def test_dry_run_sizes_follow_the_selected_format(project, copied, capsys):
    assert cli.main([str(project), "-F", "json", "-c"]) == 0
    text = copied[0]
    capsys.readouterr()
    assert cli.main([str(project), "-F", "json", "-D"]) == 0
    lines = capsys.readouterr().err.splitlines()
    size = len(text.encode("utf-8"))
    assert lines[0].startswith(
        f"Dry run: {size} UTF-8 bytes; ~{estimate_tokens(text)} tokens"
    )
    result = cli._build_output(
        project,
        cli.SelectionOptions(False, (), (), None),
        cli.parse_binary_policy(None),
        cli.GitLogOptions(False, None),
        output_format=JSON,
    )
    sizes = {
        block.title: len(JSON.entry("files", block, index).encode("utf-8"))
        for index, block in enumerate(result.document.files)
    }
    largest = max(sizes, key=lambda title: (sizes[title], title))
    assert lines[2].startswith(f"  {largest}: {sizes[largest]} bytes")


class Terminal:
    def __init__(self):
        self.parts = []

    def isatty(self):
        return True

    def write(self, text):
        self.parts.append(text)

    def flush(self):
        pass


def test_terminal_shows_canonical_text_for_non_markdown(document, monkeypatch):
    stdout = Terminal()
    monkeypatch.setattr(viewer.sys, "stdout", stdout)
    monkeypatch.setattr(viewer.sys, "stdin", Terminal())
    monkeypatch.setattr(viewer, "choose_pager", lambda: None)

    def forbidden(*args, **kwargs):
        pytest.fail("non-Markdown formats must not use the Rich view")

    monkeypatch.setattr(viewer, "render_terminal", forbidden)
    text = render(document, JSON)
    viewer.display(document, text, pretty=False)
    assert "".join(stdout.parts) == text


def test_markdown_remains_the_default(tmp_path, copied):
    (tmp_path / "a.py").write_text("x\n", encoding="utf-8")
    assert cli.parse_args([]).format == "markdown"
    assert cli.main([str(tmp_path), "-c"]) == 0
    assert copied[0].startswith("# ")
    assert MARKDOWN.suffix == ".md" and os.path.splitext("x.md")[1] == MARKDOWN.suffix


@pytest.mark.parametrize("name", sorted(FORMATS))
@pytest.mark.parametrize(
    ("part", "block", "checked_encoding"),
    [
        ("files", ContentBlock("a.py", "x", "python", "utf-8"), None),
        ("files", ContentBlock("a.py", "x\n", "python", "utf-8"), None),
        ("files", ContentBlock("a.py", "", "python", "utf-8"), None),
        ("files", ContentBlock("a.py", TRICKY, "python", "utf-8", True), None),
        ("files", ContentBlock("b.png", "iVBORw==", "text", "Base64"), "Base64"),
        ("files", ContentBlock("b.png", "iVBO", "text", "Base64", True), "Base64"),
        ("files", ContentBlock("c.bin", None), None),
        (
            "files",
            ContentBlock("d", "[Failed to read file: ]", "text", "utf-8", error=""),
            None,
        ),
        ("git", ContentBlock("/r/.git", "abc first\n"), None),
        ("git", ContentBlock("/r/.git", ""), None),
    ],
)
def test_minimum_entry_is_a_lower_bound(name, part, block, checked_encoding):
    fmt = FORMATS[name]
    streamed = len((block.text or "").encode("utf-8"))
    minimum = fmt.minimum_entry(part, block.title, block.language, checked_encoding)
    for index in (0, 1):
        assert minimum + streamed <= len(fmt.entry(part, block, index).encode("utf-8"))
