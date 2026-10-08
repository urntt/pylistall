"""Validate a release tag, bilingual notes, and the exact distribution pair."""

import argparse
import hashlib
import json
import re
import subprocess
import tarfile
import zipfile
from email.parser import BytesParser
from importlib.metadata import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def release_notes(path: Path, version: str) -> str:
    """Extract one version section without duplicating release text."""
    sections = re.split(r"(?m)^## ", path.read_text(encoding="utf-8"))
    matches = [
        section for section in sections[1:] if section.startswith(f"[{version}]")
    ]
    if len(matches) != 1:
        raise ValueError(f"Expected one [{version}] section in {path.name}")
    _, separator, notes = matches[0].partition("\n")
    if not separator or not notes.strip():
        raise ValueError(f"Missing release notes in {path.name}")
    return notes.strip()


def validate_distributions(directory: Path, project) -> dict[str, str]:
    """Reject mixed versions, extra files, or inconsistent package metadata."""
    # uv creates this ignore marker alongside the distributions.
    files = sorted(path for path in directory.iterdir() if path.name != ".gitignore")
    wheels = [path for path in files if path.suffix == ".whl"]
    sources = [path for path in files if path.name.endswith(".tar.gz")]
    if len(files) != 2 or len(wheels) != 1 or len(sources) != 1:
        raise ValueError(
            "Release directory must contain exactly one wheel and one sdist"
        )
    with zipfile.ZipFile(wheels[0]) as archive:
        names = [
            name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
        ]
        if len(names) != 1:
            raise ValueError("Wheel must contain exactly one package metadata file")
        wheel = BytesParser().parsebytes(archive.read(names[0]))
    with tarfile.open(sources[0], "r:gz") as archive:
        names = [
            item
            for item in archive.getmembers()
            if item.name.count("/") == 1 and item.name.endswith("/PKG-INFO")
        ]
        if len(names) != 1:
            raise ValueError("Source distribution must contain one root PKG-INFO")
        handle = archive.extractfile(names[0])
        if handle is None:
            raise ValueError("Source metadata must be a regular file")
        with handle:
            source = BytesParser().parsebytes(handle.read())
    fields = (
        "Name",
        "Version",
        "Requires-Python",
        "License-Expression",
        "License-File",
        "Classifier",
        "Requires-Dist",
        "Provides-Extra",
    )
    expected = {field: project.get_all(field, []) for field in fields}
    for label, package in (("wheel", wheel), ("sdist", source)):
        actual = {field: package.get_all(field, []) for field in fields}
        if actual != expected:
            raise ValueError(f"{label} metadata does not match the installed project")
    return {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in files}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tag", help="Stable release tag, for example v0.3.1")
    parser.add_argument("--dist-dir", type=Path, default=ROOT / "dist")
    parser.add_argument(
        "--check-git",
        action="store_true",
        help="Require the tag at HEAD and an ancestor of origin/main",
    )
    args = parser.parse_args()
    project = metadata("pylistall")
    version = project["Version"]
    if not re.fullmatch(r"v\d+\.\d+\.\d+", args.tag) or args.tag != f"v{version}":
        parser.error("Tag must be a stable vX.Y.Z matching the project version")
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    if args.check_git:
        tagged = subprocess.check_output(
            ["git", "rev-parse", f"refs/tags/{args.tag}^{{commit}}"],
            cwd=ROOT,
            text=True,
        ).strip()
        if tagged != commit:
            parser.error("Release tag does not point to the checked-out commit")
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", "HEAD", "origin/main"],
            cwd=ROOT,
            check=True,
        )
    english = release_notes(ROOT / "CHANGELOG.md", version)
    chinese = release_notes(ROOT / "CHANGELOG.zh-CN.md", version)
    files = validate_distributions(args.dist_dir.resolve(), project)
    output = ROOT / ".pytest_cache" / "release"
    output.mkdir(parents=True, exist_ok=True)
    manifest = {"version": version, "tag": args.tag, "commit": commit, "files": files}
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    (output / "release-notes.md").write_text(
        f"## English\n\n{english}\n\n## 中文\n\n{chinese}\n", encoding="utf-8"
    )
    print(f"Validated {args.tag} at {commit}: {', '.join(files)}")


if __name__ == "__main__":
    main()
