"""Regression coverage for release rejection and index verification boundaries."""

import hashlib
import importlib
import io
import json
import subprocess
import sys
import tarfile
import zipfile
from email.parser import BytesParser
from importlib.metadata import version
from pathlib import Path

import pytest


@pytest.fixture
def release_tools(monkeypatch):
    scripts = Path(__file__).resolve().parent.parent / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    return importlib.import_module("release"), importlib.import_module(
        "verify_published"
    )


@pytest.fixture
def distribution_pair(tmp_path):
    content = b"Name: pylistall\nVersion: 0.3.1\nRequires-Python: >=3.9\nLicense-Expression: MIT\n\n"
    wheel = tmp_path / "pylistall-0.3.1-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("pylistall-0.3.1.dist-info/METADATA", content)
    source = tmp_path / "pylistall-0.3.1.tar.gz"
    with tarfile.open(source, "w:gz") as archive:
        item = tarfile.TarInfo("pylistall-0.3.1/PKG-INFO")
        item.size = len(content)
        archive.addfile(item, io.BytesIO(content))
    return tmp_path, BytesParser().parsebytes(content)


def test_valid_distribution_pair_records_hashes(release_tools, distribution_pair):
    release, _ = release_tools
    directory, project = distribution_pair
    hashes = release.validate_distributions(directory, project)
    assert hashes == {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in directory.iterdir()
    }


def test_mixed_distribution_versions_are_rejected(release_tools, distribution_pair):
    release, _ = release_tools
    directory, project = distribution_pair
    project.replace_header("Version", "0.3.2")
    with pytest.raises(ValueError, match="metadata does not match"):
        release.validate_distributions(directory, project)


def test_extra_file_is_rejected_before_upload(release_tools, distribution_pair):
    release, _ = release_tools
    directory, project = distribution_pair
    (directory / "old-release.whl").write_bytes(b"old")
    with pytest.raises(ValueError, match="exactly one wheel and one sdist"):
        release.validate_distributions(directory, project)


def test_uv_ignore_marker_is_not_a_distribution(release_tools, distribution_pair):
    release, _ = release_tools
    directory, project = distribution_pair
    (directory / ".gitignore").write_text("*\n")
    assert len(release.validate_distributions(directory, project)) == 2


def test_sdist_mismatch_is_rejected(release_tools, distribution_pair):
    release, _ = release_tools
    directory, project = distribution_pair
    content = b"Name: pylistall\nVersion: 0.2.0\n\n"
    with tarfile.open(directory / "pylistall-0.3.1.tar.gz", "w:gz") as archive:
        item = tarfile.TarInfo("pylistall-0.3.1/PKG-INFO")
        item.size = len(content)
        archive.addfile(item, io.BytesIO(content))
    with pytest.raises(ValueError, match="sdist metadata does not match"):
        release.validate_distributions(directory, project)


def test_notes_select_exact_version_and_preserve_unicode(release_tools, tmp_path):
    release, _ = release_tools
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        "# Log\n\n## [0.3.10]\nWrong\n\n## [0.3.1]\n中文修复\n\n## [0.3.0]\nOld\n",
        encoding="utf-8",
    )
    assert release.release_notes(changelog, "0.3.1") == "中文修复"


@pytest.mark.parametrize(
    "content", ["## [0.3.0]\nOld", "## [0.3.1]\n", "## [0.3.1]\nOne\n## [0.3.1]\nTwo"]
)
def test_missing_empty_or_duplicate_notes_stop_release(
    release_tools, tmp_path, content
):
    release, _ = release_tools
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError):
        release.release_notes(changelog, "0.3.1")


@pytest.mark.parametrize("tag", ["v0.3.0", "v0.3.1rc1", "v0.3.1;bad"])
def test_invalid_tag_stops_before_git_or_archive_access(
    release_tools, monkeypatch, tag
):
    release, _ = release_tools
    monkeypatch.setattr(sys, "argv", ["release.py", tag])
    with pytest.raises(SystemExit) as error:
        release.main()
    assert error.value.code != 0


@pytest.mark.parametrize(
    "remote", [{}, {"pylistall.whl": "wrong"}, {"../pylistall.whl": "checked"}]
)
def test_remote_mismatch_stops_before_download_or_install(
    release_tools, tmp_path, monkeypatch, remote
):
    _, published = release_tools
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({"version": "0.3.1", "files": {"pylistall.whl": "checked"}})
    )
    monkeypatch.setattr(sys, "argv", ["verify_published.py", "testpypi", str(manifest)])
    monkeypatch.setattr(
        published,
        "published_files",
        lambda *_: {
            "urls": [
                {"filename": name, "digests": {"sha256": digest}}
                for name, digest in remote.items()
            ]
        },
    )

    def unexpected(*args, **kwargs):
        pytest.fail("Mismatched artifacts must not be downloaded or installed")

    monkeypatch.setattr(published.urllib.request, "urlopen", unexpected)
    monkeypatch.setattr(published, "verify_wheel", unexpected)
    with pytest.raises(ValueError):
        published.main()


def test_download_hash_change_stops_before_install(
    release_tools, tmp_path, monkeypatch
):
    _, published = release_tools
    digest = hashlib.sha256(b"checked bytes").hexdigest()
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({"version": "0.3.1", "files": {"pylistall.whl": digest}})
    )
    monkeypatch.setattr(sys, "argv", ["verify_published.py", "testpypi", str(manifest)])
    monkeypatch.setattr(
        published,
        "published_files",
        lambda *_: {
            "urls": [
                {
                    "filename": "pylistall.whl",
                    "url": "https://example.invalid/checked.whl",
                    "digests": {"sha256": digest},
                }
            ]
        },
    )
    monkeypatch.setattr(
        published.urllib.request,
        "urlopen",
        lambda *args, **kwargs: io.BytesIO(b"replaced bytes"),
    )
    monkeypatch.setattr(
        published,
        "verify_wheel",
        lambda *_: pytest.fail("Changed bytes must not be installed"),
    )
    with pytest.raises(ValueError, match="Downloaded file hash mismatch"):
        published.main()


def test_tag_at_a_different_commit_is_rejected(release_tools, monkeypatch):
    release, _ = release_tools
    monkeypatch.setattr(
        sys, "argv", ["release.py", f"v{version('pylistall')}", "--check-git"]
    )
    monkeypatch.setattr(
        release.subprocess,
        "check_output",
        lambda command, **kwargs: "head" if command[-1] == "HEAD" else "other",
    )
    with pytest.raises(SystemExit) as error:
        release.main()
    assert error.value.code != 0


def test_release_outside_main_history_is_rejected(release_tools, monkeypatch):
    release, _ = release_tools
    monkeypatch.setattr(
        sys, "argv", ["release.py", f"v{version('pylistall')}", "--check-git"]
    )
    monkeypatch.setattr(
        release.subprocess, "check_output", lambda *args, **kwargs: "head"
    )

    def reject(command, **kwargs):
        raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(release.subprocess, "run", reject)
    with pytest.raises(subprocess.CalledProcessError):
        release.main()


def test_checked_downloads_are_passed_to_isolated_install(
    release_tools, tmp_path, monkeypatch
):
    _, published = release_tools
    content = {"pylistall.whl": b"checked wheel", "pylistall.tar.gz": b"checked source"}
    hashes = {name: hashlib.sha256(data).hexdigest() for name, data in content.items()}
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"version": "0.3.1", "files": hashes}))
    monkeypatch.setattr(sys, "argv", ["verify_published.py", "testpypi", str(manifest)])
    monkeypatch.setattr(
        published,
        "published_files",
        lambda *_: {
            "urls": [
                {"filename": name, "url": name, "digests": {"sha256": digest}}
                for name, digest in hashes.items()
            ]
        },
    )
    monkeypatch.setattr(
        published.urllib.request,
        "urlopen",
        lambda name, **kwargs: io.BytesIO(content[name]),
    )
    installed = []

    def verify(directory):
        installed.append({path.name: path.read_bytes() for path in directory.iterdir()})

    monkeypatch.setattr(published, "verify_wheel", verify)
    published.main()
    assert installed == [content]
