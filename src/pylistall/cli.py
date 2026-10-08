"""Command-line entry point for pylistall."""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

from pylistall import gitlog
from pylistall.destinations import (
    resolve_destination,
    validate_destination,
    write_output,
)
from pylistall.gitlog import GitLogOptions
from pylistall.output import (
    ContentBlock,
    MarkdownBuilder,
    OutputDocument,
    OutputTooLarge,
    block_markdown,
    empty_group,
    group_heading,
    language_for,
    root_markdown,
    tree_markdown,
)
from pylistall.selection import (
    BinaryPolicy,
    SelectionOptions,
    flatten_patterns,
    iter_selected_files,
    parse_binary_policy,
    parse_omit_patterns,
    read_text,
)
from pylistall.traversal import scan_directory
from pylistall.tree import build_tree_text
from pylistall.util import copy_to_clipboard
from pylistall.viewer import display


@dataclass(frozen=True)
class OutputResult:
    """One collection, canonical Markdown, and destination-independent metadata."""

    text: str
    document: OutputDocument

    @property
    def file_count(self) -> int:
        return len(self.document.files or ())

    @property
    def warnings(self) -> tuple[str, ...]:
        return self.document.warnings


def _build_output(
    root: Path,
    selection: SelectionOptions,
    binary_policy: BinaryPolicy,
    git_options: GitLogOptions,
    *,
    disabled: tuple[str, ...] = (),
    maximum: Optional[int] = None,
    excluded: Optional[Path] = None,
) -> OutputResult:
    """Collect enabled parts once, checking budgets before any delivery."""
    root = root.resolve(strict=True)
    snapshot = scan_directory(root, selection.recursive, selection.follow_links)
    builder = MarkdownBuilder(maximum)
    root_text = str(root) if "root" not in disabled else None
    tree_text = None
    logs = None
    files = None
    if root_text is not None:
        builder.append(root_markdown(root_text))
    if "tree" not in disabled:
        tree_text = build_tree_text(root, selection.recursive, snapshot=snapshot)
        builder.append(tree_markdown(tree_text))
    chunk_bytes = min(4096, maximum + 1) if maximum is not None else 4096
    if git_options.enabled and "git" not in disabled:
        builder.append(group_heading("git"))
        logs = []
        entries, _ = gitlog._find_git_entries(
            root, selection.recursive, snapshot=snapshot
        )
        for entry in entries:
            title = str(entry.git_path.resolve())
            text = gitlog._run_git_log(
                entry.git_path.parent,
                gitlog.GIT_LOG_ALL if git_options.count is None else git_options.count,
                check_size=builder.body_checker(title, "text"),
                chunk_bytes=chunk_bytes,
            )
            block = ContentBlock(title, text)
            builder.append(block_markdown(block))
            logs.append(block)
        if not logs:
            builder.append(empty_group("git"))
    if "files" not in disabled:
        builder.append(group_heading("files"))
        files = []
        for item in iter_selected_files(
            root, selection, binary_policy, snapshot=snapshot, excluded=excluded
        ):
            language = language_for(item.display_name)
            text = read_text(
                item.absolute_path,
                selection.max_bytes,
                builder.body_checker(item.display_name, language),
                chunk_bytes,
            )
            block = ContentBlock(item.display_name, text, language)
            builder.append(block_markdown(block))
            files.append(block)
        if not files:
            builder.append(empty_group("files"))
    document = OutputDocument(
        root_text,
        tree_text,
        None if logs is None else tuple(logs),
        None if files is None else tuple(files),
        snapshot.warnings,
        sum(entry.skipped is not None for entry in snapshot.entries),
    )
    return OutputResult(builder.text(), document)


def _build_parser() -> argparse.ArgumentParser:
    """Create an argument parser."""
    parser = argparse.ArgumentParser(
        prog="pylistall",
        description=(
            "Display directory context; optionally copy Markdown or save a file."
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
        "-l",
        "--follow-links",
        action="store_true",
        help="Follow file and directory links, including targets outside the root.",
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
        "-c", "--copy", action="store_true", help="Also copy Markdown to the clipboard."
    )
    parser.add_argument(
        "-f",
        "--file",
        nargs="?",
        const="",
        default=None,
        metavar="DEST",
        help="Save Markdown to a file instead of displaying the body.",
    )
    parser.add_argument(
        "-w",
        "--overwrite",
        action="store_true",
        help="Allow replacing an output file (requires -f).",
    )
    parser.add_argument(
        "-d",
        "--disable",
        action="append",
        default=[],
        metavar="PARTS",
        help="Omit root,tree,git,files (repeatable, comma-separated).",
    )
    parser.add_argument(
        "-D",
        "--dry-run",
        action="store_true",
        help="Collect and show exact summary without copying or writing.",
    )
    parser.add_argument(
        "-M",
        "--max-output-bytes",
        type=int,
        metavar="N",
        help="Limit the complete Markdown UTF-8 byte size.",
    )
    parser.add_argument(
        "-n", "--no-pager", action="store_true", help="Disable interactive paging."
    )
    return parser


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Validate combinations before collecting any data."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    args.disable = flatten_patterns(args.disable)
    if set(args.disable) - {"root", "tree", "git", "files"}:
        parser.error("--disable accepts only root, tree, git, files")
    enabled = {"root", "tree", "files"}
    if args.git_log is not None:
        enabled.add("git")
    if not enabled - set(args.disable):
        parser.error("at least one output part must remain enabled")
    if args.overwrite and args.file is None:
        parser.error("--overwrite requires --file")
    if args.max_output_bytes is not None and args.max_output_bytes <= 0:
        parser.error("--max-output-bytes must be positive")
    if args.max_bytes is not None and args.max_bytes < 0:
        parser.error("--max-bytes must be nonnegative")
    if args.git_log is not None and args.git_log != -1 and args.git_log <= 0:
        parser.error("--git-log count must be positive")
    return args


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Collect once and independently report the outcome of each destination."""
    args = parse_args(argv)
    root = Path(args.path).expanduser()
    if not root.is_dir():
        print(f"Error: path is not a directory: {root}", file=sys.stderr)
        return 2
    destination = None
    try:
        if args.file is not None:
            destination = resolve_destination(args.file, Path.cwd())
            validate_destination(destination, args.overwrite)
        result = _build_output(
            root,
            SelectionOptions(
                bool(args.recursive),
                flatten_patterns(args.include),
                parse_omit_patterns(args.omit),
                args.max_bytes,
                args.follow_links,
            ),
            parse_binary_policy(args.binary),
            GitLogOptions(args.git_log is not None, args.git_log),
            disabled=args.disable,
            maximum=args.max_output_bytes,
            excluded=destination,
        )
    except (OSError, RuntimeError, OutputTooLarge) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    for warning in result.warnings:
        print(f"Warning: {warning}", file=sys.stderr)
    if args.dry_run:
        destinations = []
        if destination is not None:
            destinations.append(f"file: {destination}")
        else:
            destinations.append("terminal")
        if args.copy:
            destinations.append("clipboard")
        print(
            f"Dry run: {len(result.text.encode('utf-8'))} UTF-8 bytes; "
            f"files: {result.file_count}; skipped entries: {result.document.skipped_count}; "
            + "; ".join(destinations),
            file=sys.stderr,
        )
        return 0
    failed = False
    if destination is not None:
        try:
            write_output(destination, result.text, args.overwrite)
            print(f"Saved: {destination} (files: {result.file_count})", file=sys.stderr)
        except OSError as exc:
            failed = True
            print(f"Error: file output failed: {exc}", file=sys.stderr)
    else:
        display(result.document, result.text, no_pager=args.no_pager)
    if args.copy:
        try:
            copy_to_clipboard(result.text)
            print(f"Copied to clipboard (files: {result.file_count})", file=sys.stderr)
        except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
            failed = True
            print(f"Error: clipboard copy failed: {exc}", file=sys.stderr)
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
