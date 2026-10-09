"""Shared name matching, default omissions, and target subtree checks."""

from __future__ import annotations

import fnmatch
import os
from pathlib import Path
from typing import Iterable, Sequence

DEFAULT_OMIT_PATTERNS: tuple[str, ...] = (
    # Git
    "**/.git",
    "**/.git/**",
    # Python caches / tooling
    "**/__pycache__/**",
    "**/.pytest_cache/**",
    "**/.mypy_cache/**",
    "**/.ruff_cache/**",
    "**/.tox/**",
    # Virtual envs
    "**/.venv/**",
    "**/venv/**",
    # Build artifacts
    "**/build/**",
    "**/dist/**",
    "**/*.egg-info/**",
    # JS
    "**/node_modules/**",
    # IDE
    "**/.idea/**",
    "**/.vscode/**",
    # Common single files
    "**/.gitignore",
    "**/.DS_Store",
    "**/Thumbs.db",
    # Additional tooling and name-based sensitive omissions.
    "**/.nox/**",
    "**/.hypothesis/**",
    "**/.ipynb_checkpoints/**",
    "**/__pypackages__/**",
    "**/.eggs/**",
    "**/htmlcov/**",
    "**/.coverage",
    "**/.coverage.*",
    "**/.next/**",
    "**/.nuxt/**",
    "**/.output/**",
    "**/.svelte-kit/**",
    "**/.turbo/**",
    "**/.parcel-cache/**",
    "**/.vite/**",
    "**/coverage/**",
    "**/.nyc_output/**",
    "**/*.tsbuildinfo",
    "**/.eslintcache",
    "**/.stylelintcache",
    "**/.cache/**",
    "**/target/**",
    "**/.gradle/**",
    "**/.vs/**",
    "**/*.swp",
    "**/*.swo",
    "**/*~",
    "**/desktop.ini",
    "**/pylistall-output-*.md",
    "**/.env",
    "**/.env.*",
    "**/.envrc",
    "**/.pypirc",
    "**/.netrc",
    "**/id_rsa",
    "**/id_dsa",
    "**/id_ecdsa",
    "**/id_ed25519",
    "**/*.key",
    "**/*.pem",
    "**/*.p12",
    "**/*.pfx",
    "**/.aws/credentials",
    "**/.streamlit/secrets.toml",
)


def flatten_patterns(items: Sequence[str]) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            part.strip() for item in items for part in item.split(",") if part.strip()
        )
    )


def parse_omit_patterns(raw_omit: Sequence[str]) -> tuple[str, ...]:
    defaults = DEFAULT_OMIT_PATTERNS if "" in raw_omit else ()
    root_patterns = tuple(p[3:] for p in defaults if p.startswith("**/"))
    return tuple(dict.fromkeys(defaults + root_patterns + flatten_patterns(raw_omit)))


def matches_any(target: str, patterns: Iterable[str]) -> bool:
    return any(fnmatch.fnmatch(target, pattern) for pattern in patterns)


def matches_name(name: str, relative: str, patterns: tuple[str, ...]) -> bool:
    return matches_any(name, patterns) or matches_any(relative, patterns)


def omitted(
    name: str, relative: str, patterns: tuple[str, ...], *, directory: bool = False
) -> bool:
    return matches_name(name, relative, patterns) or (
        directory and matches_any(relative + "/", patterns)
    )


def target_omitted(
    target: Path, root: Path, patterns: tuple[str, ...], *, directory: bool = False
) -> bool:
    """Check the resolved entry and ancestors, exempting the collection root."""
    if not patterns:
        return False
    current = target
    is_directory = directory
    while current != root and current != current.parent:
        try:
            relative = Path(os.path.relpath(current, root)).as_posix()
        except ValueError:
            relative = current.as_posix()
        if omitted(current.name, relative, patterns, directory=is_directory):
            return True
        current = current.parent
        is_directory = True
    return False
