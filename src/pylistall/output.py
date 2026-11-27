"""Canonical collection model, output formats, and exact output accounting."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Union

from pylistall.names import inline_code, visible_name

LANGUAGES = {
    ".py": "python",
    ".pyi": "python",
    ".js": "javascript",
    ".jsx": "jsx",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".json": "json",
    ".toml": "toml",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".md": "markdown",
    ".html": "html",
    ".css": "css",
    ".sh": "bash",
    ".ps1": "powershell",
    ".bat": "batch",
    ".sql": "sql",
    ".rs": "rust",
    ".go": "go",
    ".java": "java",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".xml": "xml",
    ".ini": "ini",
}


def estimate_tokens(text: str) -> int:
    """Estimate tokens as four ASCII characters or one other character each.

    The estimate is provider-neutral and rough: real tokenizers differ by model
    and content. It compares selections; byte budgets remain the exact limit.
    """
    ascii_characters = len(text.encode("ascii", "ignore"))
    return (ascii_characters + 3) // 4 + len(text) - ascii_characters


class OutputTooLarge(Exception):
    """Collection exceeded the complete Markdown delivery budget."""


@dataclass(frozen=True)
class ContentBlock:
    title: str
    text: str | None
    language: str = "text"
    encoding: str | None = None
    truncated: bool = False
    error: str | None = None


@dataclass(frozen=True)
class OutputDocument:
    project_name: str
    path: str | None
    tree: str | None
    git: tuple[ContentBlock, ...] | None
    files: tuple[ContentBlock, ...] | None
    warnings: tuple[str, ...] = ()
    skipped_count: int = 0
    discovered_count: int = 0
    candidate_count: int = 0
    checked_count: int = 0
    collected_count: int = 0


def language_for(path: str) -> str:
    """Share deterministic language detection with all renderers."""
    name = Path(path).name.lower()
    if name == "dockerfile":
        return "dockerfile"
    return LANGUAGES.get(Path(name).suffix, "text")


def fenced(text: str, language: str = "text") -> str:
    """Use a delimiter longer than every backtick run in the content."""
    length = max([2] + [len(m.group()) for m in re.finditer(r"`+", text)]) + 1
    fence = "`" * length
    return (
        f"{fence}{language}\n{text}"
        + ("" if text.endswith("\n") else "\n")
        + f"{fence}\n"
    )


BINARY_PLACEHOLDER = "[Binary content not expanded; use -b to allow Base64 output]"
TRUNCATED = "[...TRUNCATED...]"


def block_markdown(block: ContentBlock) -> str:
    header = f"\n### {inline_code(block.title)}\n\n"
    if block.text is None:
        return header + BINARY_PLACEHOLDER + "\n"
    encoding = "Encoding: Base64\n\n" if block.encoding == "Base64" else ""
    marker = (
        "\n" + TRUNCATED + "\n"
        if block.encoding == "Base64" and block.truncated
        else ""
    )
    return header + encoding + fenced(block.text, block.language) + marker


def introduction(name: str, path: str | None, tree: str | None) -> str:
    text = f"# {inline_code(name)}\n"
    lines = []
    if path is not None:
        lines.append(visible_name(path))
    if tree is not None:
        lines.append(tree or "(empty)")
    if lines:
        text += "\n" + fenced("\n".join(lines), "bash")
    return text


GROUPS = {
    "git": ("Git log", "[No .git found]"),
    "files": ("Files", "[No files selected]"),
}


def group_heading(part: str) -> str:
    return f"\n## {GROUPS[part][0]}\n"


def empty_group(part: str) -> str:
    return f"\n{GROUPS[part][1]}\n"


def _body(text: str) -> str:
    return text + ("" if text.endswith("\n") else "\n")


class MarkdownFormat:
    """The canonical Markdown sections; terminal display renders the same model."""

    name = "markdown"
    label = "Markdown"
    suffix = ".md"

    def start(self, name: str, path: str | None, tree: str | None) -> str:
        return introduction(name, path, tree)

    def group_start(self, part: str) -> str:
        return group_heading(part)

    def entry(self, part: str, block: ContentBlock, index: int) -> str:
        return block_markdown(block)

    def group_empty(self, part: str) -> str:
        return empty_group(part)

    def group_end(self, part: str, count: int) -> str:
        return ""

    def end(self) -> str:
        return ""

    def minimum_entry(
        self, part: str, title: str, language: str, encoding: str | None
    ) -> int:
        # A trailing body newline can remove one formatting byte. Longer fences
        # are checked exactly when the complete block is appended.
        block = ContentBlock(title, "", language, encoding)
        return len(block_markdown(block).encode("utf-8")) - 1


XML_TAGS = {"git": "git_log", "files": "files"}


def _attribute(value: str) -> str:
    value = visible_name(value)
    for old, new in (("&", "&amp;"), ("<", "&lt;"), (">", "&gt;"), ('"', "&quot;")):
        value = value.replace(old, new)
    return f'"{value}"'


class XmlFormat:
    """XML-style tags for prompts; bodies stay verbatim and are not escaped."""

    name = "xml"
    label = "XML output"
    suffix = ".xml"

    def start(self, name: str, path: str | None, tree: str | None) -> str:
        text = f"<project name={_attribute(name)}>\n"
        if path is not None:
            text += f"<path>{visible_name(path)}</path>\n"
        if tree is not None:
            text += f"<tree>\n{_body(tree or '(empty)')}</tree>\n"
        return text

    def group_start(self, part: str) -> str:
        return f"<{XML_TAGS[part]}>\n"

    def entry(self, part: str, block: ContentBlock, index: int) -> str:
        if part == "git":
            return (
                f"<repository path={_attribute(block.title)}>\n"
                f"{_body(block.text or '')}</repository>\n"
            )
        attributes = f"path={_attribute(block.title)}"
        if block.text is None:
            return f'<file {attributes} binary="true">\n{BINARY_PLACEHOLDER}\n</file>\n'
        if block.encoding == "Base64":
            attributes += ' encoding="base64"'
        else:
            attributes += f" language={_attribute(block.language)}"
        if block.truncated:
            attributes += ' truncated="true"'
        if block.error is not None:
            attributes += ' error="true"'
        return f"<file {attributes}>\n{_body(block.text)}</file>\n"

    def group_empty(self, part: str) -> str:
        return f"{GROUPS[part][1]}\n"

    def group_end(self, part: str, count: int) -> str:
        return f"</{XML_TAGS[part]}>\n"

    def end(self) -> str:
        return "</project>\n"

    def minimum_entry(
        self, part: str, title: str, language: str, encoding: str | None
    ) -> int:
        # As in Markdown, a body ending in a newline needs no added separator.
        block = ContentBlock(title, "", language, encoding)
        return len(self.entry(part, block, 0).encode("utf-8")) - 1


_SURROGATES = re.compile(r"[\ud800-\udfff]")


def _json(value: object) -> str:
    text = json.dumps(value, ensure_ascii=False, indent=2)
    # Emit a literal backslash in the parsed value, so readers never need to
    # accept an unpaired surrogate as a Unicode character.
    return _SURROGATES.sub(lambda match: rf"\\u{ord(match[0]):04x}", text)


class JsonFormat:
    """One UTF-8 JSON object with readable Unicode and visible surrogate escapes."""

    name = "json"
    label = "JSON output"
    suffix = ".json"

    def start(self, name: str, path: str | None, tree: str | None) -> str:
        text = '{\n  "project": ' + _json(name)
        if path is not None:
            text += ',\n  "path": ' + _json(path)
        if tree is not None:
            text += ',\n  "tree": ' + _json(tree)
        return text

    def group_start(self, part: str) -> str:
        return f',\n  "{part}": ['

    @staticmethod
    def item(part: str, block: ContentBlock) -> dict[str, object]:
        if part == "git":
            return {"path": block.title, "log": block.text}
        return {
            "path": block.title,
            "language": block.language,
            "encoding": block.encoding,
            "truncated": block.truncated,
            "error": block.error,
            "content": block.text,
        }

    def entry(self, part: str, block: ContentBlock, index: int) -> str:
        # Only structural newlines occur: JSON escapes newlines inside strings,
        # while str.splitlines() would also split on U+2028 and similar.
        nested = "\n".join(
            "    " + line for line in _json(self.item(part, block)).split("\n")
        )
        return ("," if index else "") + "\n" + nested

    def group_empty(self, part: str) -> str:
        return ""

    def group_end(self, part: str, count: int) -> str:
        return "\n  ]" if count else "]"

    def end(self) -> str:
        return "\n}\n"

    def minimum_entry(
        self, part: str, title: str, language: str, encoding: str | None
    ) -> int:
        # Escaping never shrinks a body. The smallest metadata uses true over
        # false and null for the encoding; a possible empty error string saves
        # two bytes compared with null.
        block = ContentBlock(title, "", language, None, truncated=True)
        return len(self.entry(part, block, 0).encode("utf-8")) - 2


OutputFormat = Union[MarkdownFormat, XmlFormat, JsonFormat]
MARKDOWN = MarkdownFormat()
FORMATS: dict[str, OutputFormat] = {
    fmt.name: fmt for fmt in (MARKDOWN, XmlFormat(), JsonFormat())
}


class OutputBuilder:
    """Check before accepting each complete section and each streamed body."""

    def __init__(
        self, maximum: int | None = None, output_format: OutputFormat = MARKDOWN
    ):
        self.maximum = maximum
        self.format = output_format
        self.size = 0
        self.chunks: list[str] = []

    def check(self, extra: int) -> None:
        if self.maximum is not None and self.size + extra > self.maximum:
            raise OutputTooLarge(
                f"{self.format.label} exceeds --max-output-bytes {self.maximum}"
            )

    def append(self, text: str) -> None:
        size = len(text.encode("utf-8"))
        self.check(size)
        self.size += size
        self.chunks.append(text)

    def body_checker(
        self,
        title: str,
        language: str,
        encoding: str | None = None,
        *,
        part: str = "files",
    ):
        overhead = self.format.minimum_entry(part, title, language, encoding)
        return lambda size: self.check(overhead + size)

    def text(self) -> str:
        return "".join(self.chunks)


def render(document: OutputDocument, output_format: OutputFormat = MARKDOWN) -> str:
    """Render the same pieces, in the same order, used during collection."""
    fmt = output_format
    builder = OutputBuilder(output_format=fmt)
    builder.append(fmt.start(document.project_name, document.path, document.tree))
    for part, blocks in (("git", document.git), ("files", document.files)):
        if blocks is None:
            continue
        builder.append(fmt.group_start(part))
        for index, block in enumerate(blocks):
            builder.append(fmt.entry(part, block, index))
        if not blocks:
            builder.append(fmt.group_empty(part))
        builder.append(fmt.group_end(part, len(blocks)))
    builder.append(fmt.end())
    return builder.text()


def render_markdown(document: OutputDocument) -> str:
    return render(document, MARKDOWN)
