"""Directory tree behavior, independent of content selection."""

from pylistall.tree import build_tree_text


def test_empty_tree(tmp_path):
    assert build_tree_text(tmp_path, recursive=False) == ""


def test_shallow_tree_lists_directories_without_expanding(tmp_path, write_file):
    write_file("z.txt", "last")
    write_file("A.py", "first")
    write_file("src/child.py", "nested")

    assert build_tree_text(tmp_path, recursive=False) == (
        "├── src/\n├── A.py\n└── z.txt"
    )


def test_recursive_tree_preserves_branches_and_empty_directories(tmp_path, write_file):
    (tmp_path / "empty").mkdir()
    write_file("src/main.py", "source")
    write_file("README.md", "readme")

    assert build_tree_text(tmp_path, recursive=True) == (
        "├── empty/\n├── src/\n│   └── main.py\n└── README.md"
    )
