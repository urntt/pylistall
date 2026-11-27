"""Command-line entry point for pylistall."""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path
from typing import Callable

from pylistall import gitlog
from pylistall.destinations import (
    resolve_destination,
    validate_destination,
    write_output,
)
from pylistall.gitlog import GitLogOptions
from pylistall.names import project_name, visible_name
from pylistall.output import (
    FORMATS,
    MARKDOWN,
    ContentBlock,
    OutputBuilder,
    OutputDocument,
    OutputFormat,
    OutputTooLarge,
    estimate_tokens,
    language_for,
)
from pylistall.patterns import flatten_patterns, parse_omit_patterns
from pylistall.progress import CollectionProgress
from pylistall.selection import (
    BinaryPolicy,
    SelectionOptions,
    binary_allowed,
    is_probably_binary,
    iter_selected_files,
    parse_binary_policy,
    read_content,
)
from pylistall.traversal import TraversalResult, scan_directory
from pylistall.tree import build_tree_text
from pylistall.util import copy_to_clipboard
from pylistall.viewer import display

# Dry runs list this many of the largest Files entries.
LARGEST_ENTRIES = 5


@dataclass(frozen=True)
class OutputResult:
    """One collection, its canonical text, and destination-independent metadata."""

    text: str
    document: OutputDocument
    output_format: OutputFormat = MARKDOWN

    @property
    def file_count(self) -> int:
        return len(self.document.files or ())

    @property
    def warnings(self) -> tuple[str, ...]:
        return self.document.warnings

    def counts(self) -> str:
        return (
            f"files: {self.file_count}; collected: {self.document.collected_count}; "
            f"~{estimate_tokens(self.text)} tokens (estimate)"
        )


def _largest_entries(
    document: OutputDocument, total: int, output_format: OutputFormat = MARKDOWN
) -> list[str]:
    """Describe the Files entries that contribute the most output."""
    sized = sorted(
        (
            (len(text.encode("utf-8")), estimate_tokens(text), block.title)
            for index, block in enumerate(document.files or ())
            for text in (output_format.entry("files", block, index),)
        ),
        key=lambda item: (-item[0], item[2]),
    )
    return [
        f"  {visible_name(title)}: {size} bytes ({size / total:.1%}), ~{tokens} tokens"
        for size, tokens, title in sized[:LARGEST_ENTRIES]
    ]


def _report_dry_run(result: OutputResult, destination: Path | None, copy: bool) -> None:
    destinations = [f"file: {destination}" if destination is not None else "terminal"]
    if copy:
        destinations.append("clipboard")
    size = len(result.text.encode("utf-8"))
    document = result.document
    print(
        f"Dry run: {size} UTF-8 bytes; ~{estimate_tokens(result.text)} tokens "
        f"(estimate); files: {result.file_count}; "
        f"collected: {document.collected_count}; "
        f"discovered: {document.discovered_count}; "
        f"skipped entries: {document.skipped_count}; " + "; ".join(destinations),
        file=sys.stderr,
    )
    largest = _largest_entries(document, size, result.output_format)
    if largest:
        print("Largest Files entries:", *largest, sep="\n", file=sys.stderr)


def _build_output(
    root: Path,
    selection: SelectionOptions,
    binary_policy: BinaryPolicy,
    git_options: GitLogOptions,
    *,
    disabled: tuple[str, ...] = (),
    maximum: int | None = None,
    excluded: Path | None = None,
    report: Callable[..., None] | None = None,
    output_format: OutputFormat = MARKDOWN,
) -> OutputResult:
    """Collect enabled parts once, checking budgets before any delivery."""
    fmt = output_format
    root = root.resolve(strict=True)
    name = project_name(root)
    builder = OutputBuilder(maximum, fmt)
    path_text = str(root) if "path" not in disabled else None
    # Reject an impossible title budget before enumerating the filesystem.
    builder.check(len((fmt.start(name, path_text, None) + fmt.end()).encode("utf-8")))
    collect_git = git_options.enabled and "git" not in disabled
    need_scan = "tree" not in disabled or "files" not in disabled or collect_git
    snapshot = (
        scan_directory(
            root,
            selection.recursive,
            selection.follow_links,
            omit=selection.omit,
            collect_git=collect_git,
            report=report,
        )
        if need_scan
        else TraversalResult(root, (), ())
    )
    tree_text = None
    logs = None
    files = None
    checked = collected = candidate_count = 0
    if "tree" not in disabled:
        if report is not None:
            report("tree", str(root))
        tree_text = build_tree_text(
            root,
            selection.recursive,
            snapshot=snapshot,
            include=selection.include,
            report=report,
        )
    builder.append(fmt.start(name, path_text, tree_text))
    chunk_bytes = min(4096, maximum + 1) if maximum is not None else 4096
    if collect_git:
        if report is not None:
            report("git", str(root))
        builder.append(fmt.group_start("git"))
        logs = []
        entries, _ = gitlog._find_git_entries(
            root, selection.recursive, snapshot=snapshot
        )
        for entry in entries:
            title = str(entry.git_path.resolve())
            if report is not None:
                report("git", title)
            text = gitlog._run_git_log(
                entry.git_path.parent,
                gitlog.GIT_LOG_ALL if git_options.count is None else git_options.count,
                check_size=builder.body_checker(title, "text", part="git"),
                chunk_bytes=chunk_bytes,
                report=report,
            )
            block = ContentBlock(title, text)
            builder.append(fmt.entry("git", block, len(logs)))
            logs.append(block)
        if not logs:
            builder.append(fmt.group_empty("git"))
        builder.append(fmt.group_end("git", len(logs)))
    if "files" not in disabled:
        builder.append(fmt.group_start("files"))
        files = []
        candidates = list(
            iter_selected_files(root, selection, snapshot=snapshot, excluded=excluded)
        )
        candidate_count = len(candidates)
        if report is not None:
            report("files", str(root), total=candidate_count, checked=0, collected=0)
        for item in candidates:
            if report is not None:
                report("files", str(item.absolute_path))
            # Check minimum metadata before sampling or starting the next file.
            builder.body_checker(item.display_name, "text")(0)
            binary = is_probably_binary(item.absolute_path)
            allowed = not binary or binary_allowed(
                item.relative_path.name, item.relative_path.as_posix(), binary_policy
            )
            if not allowed:
                block = ContentBlock(item.display_name, None)
            else:
                language = "text" if binary else language_for(item.display_name)
                result = read_content(
                    item.absolute_path,
                    selection.max_bytes,
                    builder.body_checker(
                        item.display_name, language, "Base64" if binary else None
                    ),
                    chunk_bytes,
                    binary=binary,
                    report=report,
                )
                block = ContentBlock(
                    item.display_name,
                    result.text,
                    language,
                    result.encoding,
                    result.truncated,
                    result.error,
                )
                collected += int(result.error is None)
            builder.append(fmt.entry("files", block, len(files)))
            files.append(block)
            checked += 1
            if report is not None:
                report(
                    "files",
                    str(item.absolute_path),
                    checked=checked,
                    collected=collected,
                )
        if not files:
            builder.append(fmt.group_empty("files"))
        builder.append(fmt.group_end("files", len(files)))
    builder.append(fmt.end())
    document = OutputDocument(
        project_name=name,
        path=path_text,
        tree=tree_text,
        git=None if logs is None else tuple(logs),
        files=None if files is None else tuple(files),
        warnings=snapshot.warnings,
        skipped_count=sum(entry.skipped is not None for entry in snapshot.entries),
        discovered_count=snapshot.discovered_count,
        candidate_count=candidate_count,
        checked_count=checked,
        collected_count=collected,
    )
    return OutputResult(builder.text(), document, fmt)


def _build_parser() -> argparse.ArgumentParser:
    """Create an argument parser."""
    parser = argparse.ArgumentParser(
        prog="pylistall",
        description=(
            "Display directory context; optionally copy or save Markdown, XML or JSON."
        ),
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {version('pylistall')}",
        help="Show the installed version and exit.",
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
        help="Filter file names in tree and Files (repeatable, comma-separated).",
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
            "Omit names and prune directories (repeatable, comma-separated). "
            "If provided without PATTERN, enable default omit set."
        ),
    )

    # -b can be passed without a value to include all binary files.
    # If provided with PATTERN, only that subset of binaries is enabled.
    parser.add_argument(
        "-b",
        "--binary",
        nargs="?",
        const="",
        default=None,
        metavar="PATTERN",
        help=(
            "Expand candidate binaries as Base64. Use -b for all binaries, "
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
        "-c",
        "--copy",
        action="store_true",
        help="Also copy the output to the clipboard.",
    )
    parser.add_argument(
        "-f",
        "--file",
        nargs="?",
        const="",
        default=None,
        metavar="DEST",
        help="Save the output to a file instead of displaying the body.",
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
        help="Omit path,tree,git,files (repeatable, comma-separated).",
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
        help="Limit the complete output UTF-8 byte size.",
    )
    parser.add_argument(
        "-F",
        "--format",
        choices=tuple(FORMATS),
        default=MARKDOWN.name,
        help="Output format for every destination (default: markdown).",
    )
    parser.add_argument(
        "-n", "--no-pager", action="store_true", help="Disable interactive paging."
    )
    parser.add_argument(
        "-P", "--no-progress", action="store_true", help="Disable progress feedback."
    )
    return parser


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Validate combinations before collecting any data."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    args.disable = flatten_patterns(args.disable)
    if set(args.disable) - {"path", "tree", "git", "files"}:
        parser.error("--disable accepts only path, tree, git, files")
    if args.overwrite and args.file is None:
        parser.error("--overwrite requires --file")
    if args.max_output_bytes is not None and args.max_output_bytes <= 0:
        parser.error("--max-output-bytes must be positive")
    if args.max_bytes is not None and args.max_bytes < 0:
        parser.error("--max-bytes must be nonnegative")
    if args.git_log is not None and args.git_log != -1 and args.git_log <= 0:
        parser.error("--git-log count must be positive")
    return args


def _main(argv: Sequence[str] | None = None) -> int:
    """Collect once and independently report the outcome of each destination."""
    args = parse_args(argv)
    root = Path(args.path).expanduser()
    try:
        root = root.resolve(strict=True)
        if not root.is_dir():
            raise NotADirectoryError(str(root))
    except (OSError, RuntimeError) as exc:
        print(f"Error: path is not a directory: {root} ({exc})", file=sys.stderr)
        return 2
    destination = None
    try:
        if args.file is not None:
            destination = resolve_destination(
                args.file, Path.cwd(), FORMATS[args.format].suffix
            )
            validate_destination(destination, args.overwrite)
        with CollectionProgress(args.no_progress) as progress:
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
                report=progress.update,
                output_format=FORMATS[args.format],
            )
    except (OSError, RuntimeError, OutputTooLarge) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    for warning in result.warnings:
        print(f"Warning: {warning}", file=sys.stderr)
    if args.dry_run:
        _report_dry_run(result, destination, args.copy)
        return 0
    failed = False
    if destination is not None:
        try:
            write_output(destination, result.text, args.overwrite)
            print(f"Saved: {destination} ({result.counts()})", file=sys.stderr)
        except OSError as exc:
            failed = True
            print(f"Error: file output failed: {exc}", file=sys.stderr)
    else:
        display(
            result.document,
            result.text,
            no_pager=args.no_pager,
            no_progress=args.no_progress,
            pretty=result.output_format is MARKDOWN,
        )
    if args.copy:
        try:
            copy_to_clipboard(result.text)
            print(f"Copied to clipboard ({result.counts()})", file=sys.stderr)
        except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
            failed = True
            print(f"Error: clipboard copy failed: {exc}", file=sys.stderr)
    return int(failed)


def main(argv: Sequence[str] | None = None) -> int:
    """Translate cancellation into the conventional status after resource cleanup."""
    try:
        return _main(argv)
    except KeyboardInterrupt:
        print("Cancelled", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
