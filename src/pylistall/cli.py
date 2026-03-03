"""Command-line entry point for pylistall."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

from pylistall.gitlog import GitLogOptions, build_git_log_sections
from pylistall.selection import (
    BinaryPolicy,
    SelectionOptions,
    build_content_sections,
    parse_binary_policy,
    parse_omit_patterns,
)
from pylistall.tree import build_tree_text
from pylistall.util import copy_to_clipboard


@dataclass(frozen=True, slots=True)
class OutputResult:
    """Represents the final output and metadata."""

    text: str
    file_count: int
    warnings: tuple[str, ...]


def _build_output(
    root: Path,
    selection: SelectionOptions,
    binary_policy: BinaryPolicy,
    git_options: GitLogOptions,
) -> OutputResult:
    """Build the final output text and return it along with file count."""
    chunks: list[str] = []

    # 1) Root + tree (tree is independent from all filters except -r)
    chunks.append(f"{root.resolve()}\n")
    tree_text = build_tree_text(root=root, recursive=selection.recursive)
    if tree_text:
        chunks.append(f"{tree_text}\n\n")
    else:
        chunks.append("(empty)\n\n")

    warnings: list[str] = []

    # 2) Git logs (always print absolute .git path before each group)
    if git_options.enabled:
        sections, git_warnings = build_git_log_sections(
            root=root,
            recursive=selection.recursive,
            count=git_options.count,
        )
        warnings.extend(git_warnings)
        if sections:
            chunks.append(sections)
            chunks.append("\n\n")
        else:
            chunks.append("[No .git found]\n\n")

    # 3) Content sections
    content_text, file_count = build_content_sections(
        root=root,
        selection=selection,
        binary_policy=binary_policy,
    )
    if content_text:
        chunks.append(content_text)

    final_text = "".join(chunks).rstrip() + "\n"
    return OutputResult(
        text=final_text,
        file_count=file_count,
        warnings=tuple(warnings),
    )


def _build_parser() -> argparse.ArgumentParser:
    """Create an argument parser."""
    parser = argparse.ArgumentParser(
        prog="pylistall",
        description=(
            "Copy directory file contents to clipboard "
            "with tree and optional git log."
        ),
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Target directory (default: current directory).",
    )

    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="Recurse into subdirectories (tree will include directories).",
    )

    parser.add_argument(
        "-i",
        "--include",
        action="append",
        default=[],
        help="Include glob patterns (repeatable, comma-separated supported).",
    )

    # -o can be passed without a value to enable default omit patterns.
    # Repeating -o merges patterns (default + user patterns).
    parser.add_argument(
        "-o",
        "--omit",
        nargs="?",
        const="",
        action="append",
        default=[],
        metavar="PATTERN",
        help=(
            "Omit glob patterns (repeatable, comma-separated supported). "
            "If provided without PATTERN, enable default omit set."
        ),
    )

    # -b can be passed without a value to include all binary files.
    # If provided with PATTERN, only that subset of binaries is enabled.
    # -i can still force-include binaries even when -b is absent.
    parser.add_argument(
        "-b",
        "--binary",
        nargs="?",
        const="",
        default=None,
        metavar="PATTERN",
        help=(
            "Include binary files. Use -b for all binaries, "
            "or -b PATTERN for a binary whitelist (comma-separated supported)."
        ),
    )

    parser.add_argument(
        "-m",
        "--max-bytes",
        type=int,
        default=None,
        help="Max bytes per file to read (default: no limit).",
    )

    parser.add_argument(
        "-g",
        "--git-log",
        nargs="?",
        const=-1,
        default=None,
        type=int,
        metavar="N",
        help=(
            "Include git log if .git exists. Use -g for all logs, "
            "or -g N for last N entries. Each group is prefixed by .git path."
        ),
    )

    parser.add_argument(
        "-p",
        "--print",
        dest="print_output",
        action="store_true",
        help="Print the output to stdout before 'Copied to clipboard...'.",
    )

    return parser


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    return _build_parser().parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI entry point."""
    args = parse_args(argv)

    root = Path(args.path).expanduser()
    if not root.exists():
        print(f"Error: path does not exist: {root}")
        return 2
    if not root.is_dir():
        print(f"Error: path is not a directory: {root}")
        return 2

    omit_patterns = parse_omit_patterns(args.omit)
    selection = SelectionOptions(
        recursive=bool(args.recursive),
        include=args.include,
        omit=omit_patterns,
        max_bytes=args.max_bytes,
    )
    binary_policy = parse_binary_policy(args.binary)

    git_options = GitLogOptions(enabled=args.git_log is not None,
                                count=args.git_log)

    result = _build_output(
        root=root,
        selection=selection,
        binary_policy=binary_policy,
        git_options=git_options,
    )

    if args.print_output:
        # Print full content first, then an empty line, then the copy message.
        print(result.text, end="")
        print("")

    copy_to_clipboard(result.text)
    print(f"Copied to clipboard: {root.resolve()} "
          f"(files: {result.file_count})")

    for warning in result.warnings:
        print(f"Warning: {warning}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
