"""Read the CI Python versions from the installed project and development pin."""

import json
import re
from importlib.metadata import metadata
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    requirement = metadata("pylistall")["Requires-Python"]
    minimum = re.fullmatch(r">=(\d+\.\d+(?:\.\d+)?)", requirement or "")
    if minimum is None:
        raise SystemExit(
            "Update the CI matrix parser for the new Requires-Python range"
        )
    versions = [minimum.group(1), root.joinpath(".python-version").read_text().strip()]
    matrix = {
        "os": ["ubuntu-latest", "windows-latest", "macos-latest"],
        "python": versions,
    }
    print(f"checks={json.dumps(matrix)}")
    print(f"python={json.dumps(versions)}")
    print(f"default_python={versions[1]}")


if __name__ == "__main__":
    main()
