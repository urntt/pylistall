"""Shared name matching, default omissions, and target subtree checks."""

from __future__ import annotations

import fnmatch
import functools
import os
import re
from pathlib import Path
from typing import Iterable, Optional, Sequence

# Characters that give fnmatch patterns a meaning beyond exact equality.
GLOB_CHARACTERS = frozenset("*?[")

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


class PatternMatcher:
    """Match like ``any(fnmatch.fnmatch(target, p) for p in patterns)``, once.

    Patterns and targets are normalized with ``os.path.normcase`` exactly as
    ``fnmatch.fnmatch`` does. Exact names use a set lookup; the remaining globs
    share one compiled alternation of ``fnmatch.translate`` expressions.
    """

    __slots__ = ("literals", "expression")

    def __init__(self, patterns: tuple[str, ...]):
        normalized = [os.path.normcase(pattern) for pattern in patterns]
        globs = [p for p in normalized if GLOB_CHARACTERS.intersection(p)]
        self.literals = frozenset(normalized).difference(globs)
        self.expression: Optional[re.Pattern[str]] = (
            re.compile("|".join(f"(?:{fnmatch.translate(p)})" for p in globs))
            if globs
            else None
        )

    def __call__(self, target: str) -> bool:
        target = os.path.normcase(target)
        return target in self.literals or (
            self.expression is not None and self.expression.match(target) is not None
        )


@functools.lru_cache(maxsize=256)
def compiled(patterns: tuple[str, ...]) -> PatternMatcher:
    """Reuse one matcher for each distinct rule set during a collection."""
    return PatternMatcher(patterns)


def matches_any(target: str, patterns: Iterable[str]) -> bool:
    patterns = tuple(patterns)
    return bool(patterns) and compiled(patterns)(target)


def matches_name(name: str, relative: str, patterns: tuple[str, ...]) -> bool:
    if not patterns:
        return False
    matcher = compiled(patterns)
    return matcher(name) or matcher(relative)


def omitted(
    name: str, relative: str, patterns: tuple[str, ...], *, directory: bool = False
) -> bool:
    if not patterns:
        return False
    matcher = compiled(patterns)
    return matcher(name) or matcher(relative) or (directory and matcher(relative + "/"))


def _relative_to_root(path: Path, root: Path) -> str:
    try:
        return Path(os.path.relpath(path, root)).as_posix()
    except ValueError:
        return path.as_posix()


@functools.lru_cache(maxsize=4096)
def _directory_chain_omitted(
    directory: Path, root: Path, patterns: tuple[str, ...]
) -> bool:
    """Check a directory and its ancestors up to the root; shared by siblings."""
    if directory == root or directory == directory.parent:
        return False
    if omitted(
        directory.name,
        _relative_to_root(directory, root),
        patterns,
        directory=True,
    ):
        return True
    return _directory_chain_omitted(directory.parent, root, patterns)


def target_omitted(
    target: Path, root: Path, patterns: tuple[str, ...], *, directory: bool = False
) -> bool:
    """Check the resolved entry and ancestors, exempting the collection root."""
    if not patterns or target == root or target == target.parent:
        return False
    if omitted(
        target.name, _relative_to_root(target, root), patterns, directory=directory
    ):
        return True
    return _directory_chain_omitted(target.parent, root, patterns)
