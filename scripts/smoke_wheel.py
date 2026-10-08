"""Install a built wheel in isolation and verify metadata and the CLI entry point."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from importlib.metadata import metadata
from pathlib import Path

METADATA_FIELDS = (
    "Version",
    "Requires-Python",
    "License-Expression",
    "License-File",
    "Classifier",
    "Requires-Dist",
    "Provides-Extra",
)

VERIFY_INSTALL = """
import json
import sys
from importlib.metadata import metadata
from pathlib import Path

import pylistall

expected = json.loads(sys.argv[1])
installed = metadata("pylistall")
actual = {field: installed.get_all(field, []) for field in expected}
if actual != expected:
    raise SystemExit(f"Wheel metadata mismatch: {actual!r} != {expected!r}")
module = Path(pylistall.__file__).resolve()
if Path(sys.prefix).resolve() not in module.parents:
    raise SystemExit(f"Imported pylistall outside the isolated environment: {module}")
print(f"Verified isolated wheel: {installed['Version']} ({sys.version.split()[0]})")
"""


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    artifacts = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else root / "dist"
    wheels = list(artifacts.glob("*.whl"))
    sources = list(artifacts.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sources) != 1:
        raise SystemExit("Expected exactly one wheel and one source distribution")
    uv = shutil.which("uv")
    if uv is None:
        raise SystemExit(
            "Install uv outside the project environment and add it to PATH"
        )
    project = metadata("pylistall")
    expected = {field: project.get_all(field, []) for field in METADATA_FIELDS}
    cache = root / ".pytest_cache"
    cache.mkdir(exist_ok=True)
    if root not in cache.resolve().parents:
        raise SystemExit("The smoke-test directory must stay inside the repository")
    with tempfile.TemporaryDirectory(prefix="wheel-smoke-", dir=cache) as temporary:
        directory = Path(temporary)
        environment = directory / "venv"
        subprocess.run(
            [uv, "venv", "--python", sys.executable, str(environment)], check=True
        )
        binaries = environment / ("Scripts" if os.name == "nt" else "bin")
        python = binaries / ("python.exe" if os.name == "nt" else "python")
        cli = binaries / ("pylistall.exe" if os.name == "nt" else "pylistall")
        subprocess.run(
            [uv, "pip", "install", "--python", str(python), str(wheels[0])], check=True
        )
        subprocess.run(
            [str(python), "-I", "-c", VERIFY_INSTALL, json.dumps(expected)],
            cwd=directory,
            check=True,
        )
        subprocess.run([str(cli), "--help"], cwd=directory, check=True)


if __name__ == "__main__":
    main()
