"""Canonical collection model, Markdown formatting, and output accounting."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

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


class OutputTooLarge(Exception):
    """Collection exceeded the complete Markdown delivery budget."""


@dataclass(frozen=True)
class ContentBlock:
    title: str
    text: Optional[str]
    language: str = "text"
    encoding: Optional[str] = None
    truncated: bool = False
    error: Optional[str] = None


@dataclass(frozen=True)
class OutputDocument:
    project_name: str
    path: Optional[str]
    tree: Optional[str]
    git: Optional[tuple[ContentBlock, ...]]
    files: Optional[tuple[ContentBlock, ...]]
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


def introduction(name: str, path: Optional[str], tree: Optional[str]) -> str:
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


class MarkdownBuilder:
    """Check before accepting each complete section and each streamed body."""

    def __init__(self, maximum: Optional[int] = None):
        self.maximum = maximum
        self.size = 0
        self.chunks: list[str] = []

    def check(self, extra: int) -> None:
        if self.maximum is not None and self.size + extra > self.maximum:
            raise OutputTooLarge(f"Markdown exceeds --max-output-bytes {self.maximum}")

    def append(self, text: str) -> None:
        size = len(text.encode("utf-8"))
        self.check(size)
        self.size += size
        self.chunks.append(text)

    def body_checker(self, title: str, language: str, encoding: Optional[str] = None):
        # A trailing body newline can remove one formatting byte. Longer fences
        # are checked exactly when the complete block is appended.
        overhead = (
            len(
                block_markdown(ContentBlock(title, "", language, encoding)).encode(
                    "utf-8"
                )
            )
            - 1
        )
        return lambda size: self.check(overhead + size)

    def text(self) -> str:
        return "".join(self.chunks)


def render_markdown(document: OutputDocument) -> str:
    """Render the same canonical sections used during collection accounting."""
    builder = MarkdownBuilder()
    builder.append(introduction(document.project_name, document.path, document.tree))
    if document.git is not None:
        builder.append(group_heading("git"))
        for block in document.git:
            builder.append(block_markdown(block))
        if not document.git:
            builder.append(empty_group("git"))
    if document.files is not None:
        builder.append(group_heading("files"))
        for block in document.files:
            builder.append(block_markdown(block))
        if not document.files:
            builder.append(empty_group("files"))
    return builder.text()
