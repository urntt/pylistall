"""Create disposable Unicode fixtures for manual progress and pager acceptance."""

from pathlib import Path

DIRECTORIES = 30
FILES_PER_DIRECTORY = 20
LINES_PER_FILE = 100


def main() -> int:
    """Recreate a missing sample without replacing an existing directory."""
    root = Path(__file__).resolve().parent.parent
    sample = root / ".pytest_cache" / "manual-progress" / "sample"
    if root not in sample.resolve().parents:
        raise SystemExit("The sample directory must stay inside the repository")
    if sample.exists():
        raise SystemExit("Sample already exists; use it for the manual checks")
    sample.mkdir(parents=True)
    source = 'print("中文🙂")\n' * LINES_PER_FILE
    for directory in range(DIRECTORIES):
        folder = sample / f"中文🙂-{directory}" / ("long-path-" * 6)
        folder.mkdir(parents=True)
        for number in range(FILES_PER_DIRECTORY):
            with (folder / f"file-{number}.py").open(
                "x", encoding="utf-8", newline="\n"
            ) as output:
                output.write(source)
    (sample / "image.bin").write_bytes(bytes(range(256)) * 10)
    (sample / "empty.txt").touch()
    python_files = DIRECTORIES * FILES_PER_DIRECTORY
    print(f"Created: {sample.relative_to(root).as_posix()}")
    print(
        f"Expected dry run: files: {python_files + 2}; "
        f"collected: {python_files + 1}; "
        f"discovered: {python_files + 2 + DIRECTORIES * 2}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
