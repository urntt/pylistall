"""Verify index hashes and install the published wheel with dependencies from PyPI."""

import argparse
import hashlib
import json
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

from smoke_wheel import verify_wheel

INDEXES = {"testpypi": "https://test.pypi.org", "pypi": "https://pypi.org"}
INDEX_ATTEMPTS = 6
INDEX_RETRY_SECONDS = 5


def published_files(index: str, version: str) -> dict:
    url = f"{INDEXES[index]}/pypi/pylistall/{version}/json"
    for attempt in range(INDEX_ATTEMPTS):
        try:
            with urllib.request.urlopen(url, timeout=20) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code != 404 or attempt == INDEX_ATTEMPTS - 1:
                raise
            time.sleep(INDEX_RETRY_SECONDS)
    raise RuntimeError("Package index did not expose the release")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("index", choices=INDEXES)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    release = published_files(args.index, manifest["version"])
    files = {item["filename"]: item for item in release["urls"]}
    expected = manifest["files"]
    if set(files) != set(expected):
        raise ValueError("Published files do not match the checked distribution pair")
    for name, digest in expected.items():
        if Path(name).name != name or files[name]["digests"]["sha256"] != digest:
            raise ValueError(
                f"Published file differs from the checked artifact: {name}"
            )
    root = Path(__file__).resolve().parent.parent
    cache = root / ".pytest_cache"
    cache.mkdir(exist_ok=True)
    if root not in cache.resolve().parents:
        raise ValueError("Download directory must stay inside the repository")
    with tempfile.TemporaryDirectory(prefix="published-", dir=cache) as temporary:
        directory = Path(temporary)
        for name, digest in expected.items():
            with urllib.request.urlopen(files[name]["url"], timeout=30) as response:
                data = response.read()
            if hashlib.sha256(data).hexdigest() != digest:
                raise ValueError(f"Downloaded file hash mismatch: {name}")
            (directory / name).write_bytes(data)
        verify_wheel(directory)
    print(
        f"Verified {args.index} release {manifest['version']} and both SHA-256 hashes"
    )


if __name__ == "__main__":
    main()
