"""Run the repository checks with the active development interpreter."""

import subprocess
import sys
from pathlib import Path


def main() -> int:
    """Stop at the first failed check and preserve its exit status."""
    root = Path(__file__).resolve().parent.parent
    commands = (
        ("ruff", "check", "."),
        ("ruff", "format", "--check", "."),
        ("pytest",),
    )
    for command in commands:
        print(f"Running: {' '.join(command)}", flush=True)
        result = subprocess.run([sys.executable, "-m", *command], cwd=root)
        if result.returncode:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
