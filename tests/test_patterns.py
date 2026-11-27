"""Compiled rule matching keeps fnmatch semantics on every platform."""

import fnmatch
import os
import unicodedata
from pathlib import Path

import pytest

from pylistall import patterns
from pylistall.names import visible_name

RULES = patterns.parse_omit_patterns(
    [
        "",
        "README.md",
        "src/*.py",
        "[!a]*.txt",
        "file[",
        "Docs/**",
        "*.PY",
        "a?c",
        "back\\slash",
    ]
)

TARGETS = [
    "",
    "README.md",
    "readme.md",
    "src/main.py",
    "src/deep/main.py",
    "SRC/main.py",
    "a.txt",
    "b.txt",
    "file[",
    "docs/guide.md",
    "Docs/guide.md",
    "main.py",
    "MAIN.PY",
    "abc",
    "a/c",
    ".git",
    "pkg/.git",
    "pkg/.git/HEAD",
    ".venv/",
    "x/.venv/lib",
    "node_modules",
    "web/node_modules/",
    "id_ed25519",
    "notes.key",
    ".env.local",
    "back\\slash",
    "back/slash",
    "中文🙂.txt",
]


def reference(target, rules):
    return any(fnmatch.fnmatch(target, rule) for rule in rules)


def reference_target_omitted(target, root, rules, directory=False):
    """The previous per-rule, per-ancestor implementation."""
    current, is_directory = target, directory
    while current != root and current != current.parent:
        try:
            relative = Path(os.path.relpath(current, root)).as_posix()
        except ValueError:
            relative = current.as_posix()
        if (
            reference(current.name, rules)
            or reference(relative, rules)
            or (is_directory and reference(relative + "/", rules))
        ):
            return True
        current, is_directory = current.parent, True
    return False


@pytest.mark.parametrize("target", TARGETS)
def test_compiled_rules_match_fnmatch(target):
    assert patterns.matches_any(target, RULES) == reference(target, RULES)
    for rule in RULES:
        assert patterns.matches_any(target, (rule,)) == fnmatch.fnmatch(target, rule)


def test_empty_rule_sets_match_nothing():
    assert not patterns.matches_any("anything", ())
    assert not patterns.matches_name("anything", "any/thing", ())
    assert not patterns.omitted("anything", "any/thing", (), directory=True)


@pytest.mark.parametrize(
    "relative",
    [
        "src/main.py",
        "src/deep/main.py",
        "build/lib/module.py",
        "pkg/node_modules/a.js",
        "docs/guide.md",
        "Docs/guide.md",
        "keys/server.pem",
        "plain/notes.txt",
    ],
)
@pytest.mark.parametrize("directory", [False, True])
def test_target_checks_match_previous_implementation(tmp_path, relative, directory):
    root = tmp_path / "root"
    for target in (root / relative, tmp_path / "external" / relative):
        assert patterns.target_omitted(
            target, root, RULES, directory=directory
        ) == reference_target_omitted(target, root, RULES, directory)
    assert not patterns.target_omitted(root, root, RULES, directory=True)


@pytest.mark.parametrize(
    "value", ["plain.py", "中文🙂", "a\tb", "nbsp\u00a0name", "zero\u200bwidth", "\x1b"]
)
def test_printable_fast_path_preserves_escaping(value):
    escapes = {"\n": r"\n", "\r": r"\r", "\t": r"\t", "\x1b": r"\x1b"}
    expected = "".join(
        escapes.get(char, f"\\u{ord(char):04x}")
        if unicodedata.category(char) in {"Cc", "Cf", "Cs"}
        else char
        for char in value
    )
    assert visible_name(value) == expected
