"""Canonical collection model, Markdown formatting, and output accounting."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

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
    text: str
    language: str = "text"


@dataclass(frozen=True)
class OutputDocument:
    root: Optional[str]
    tree: Optional[str]
    git: Optional[tuple[ContentBlock, ...]]
    files: Optional[tuple[ContentBlock, ...]]
    warnings: tuple[str, ...] = ()
    skipped_count: int = 0


def language_for(path: str) -> str:
    """Share deterministic language detection with all renderers."""
    name = Path(path).name.lower()
    if name == "dockerfile":
        return "dockerfile"
    return LANGUAGES.get(Path(name).suffix, "text")


def escape_path(path: str) -> str:
    """Prevent a literal filename from becoming Markdown syntax."""
    path = path.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    path = path.replace("\r", "&#13;").replace("\n", "&#10;")
    return re.sub(r"([\\`*_{}\[\]()#+.!|~])", r"\\\1", path)


def fenced(text: str, language: str = "text") -> str:
    """Use a delimiter longer than every backtick run in the content."""
    length = max([2] + [len(m.group()) for m in re.finditer(r"`+", text)]) + 1
    fence = "`" * length
    return (
        f"{fence}{language}\n{text}"
        + ("" if text.endswith("\n") else "\n")
        + f"{fence}\n"
    )


def block_markdown(block: ContentBlock) -> str:
    return f"\n### {escape_path(block.title)}\n\n{fenced(block.text, block.language)}"


def root_markdown(root: str) -> str:
    return escape_path(root) + "\n"


def tree_markdown(tree: str) -> str:
    return "\n## Directory tree\n\n" + fenced(tree or "(empty)")


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

    def body_checker(self, title: str, language: str):
        # A trailing body newline can remove one formatting byte. Longer fences
        # are checked exactly when the complete block is appended.
        overhead = (
            len(block_markdown(ContentBlock(title, "", language)).encode("utf-8")) - 1
        )
        return lambda size: self.check(overhead + size)

    def text(self) -> str:
        return "".join(self.chunks)


def render_markdown(document: OutputDocument) -> str:
    """Render the same canonical sections used during collection accounting."""
    builder = MarkdownBuilder()
    if document.root is not None:
        builder.append(root_markdown(document.root))
    if document.tree is not None:
        builder.append(tree_markdown(document.tree))
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
