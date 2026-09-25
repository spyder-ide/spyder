# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for gitignore pattern matching.

The expected results were produced with git check-ignore.
"""

# Standard library imports
import os
import time

# Third party imports
import pytest
from watchdog.utils.dirsnapshot import DirectorySnapshot

# Local imports
from spyder.plugins.projects.utils.gitignore import (
    GitignoreRules, parse_gitignore)
from spyder.plugins.projects.utils.watcher import ScandirFilter


ROOT_GITIGNORE = r"""
# comment
*.gen.py
/top_only.py
out/
docs/**/draft.py
**/cache
lib/**
!lib/keep.py
sub/nested.py
[abc]x.py
[!abc]y.py
q?.py
\#hash.py
\!bang.py
trailing.py
"""

PKG_GITIGNORE = """
!keep.gen.py
*.tmp.py
/local.py
"""

FILES = [
    "main.py", "a.gen.py", "pkg/b.gen.py", "pkg/keep.gen.py",
    "top_only.py", "pkg/top_only.py",
    "out/c.py", "pkg/out/d.py", "pkg/out.py",
    "docs/draft.py", "docs/x/draft.py", "docs/x/y/draft.py", "docs/final.py",
    "cache/e.py", "pkg/cache/f.py", "pkg/deep/cache/g.py",
    "lib/h.py", "lib/keep.py", "lib/sub/i.py",
    "sub/nested.py", "pkg/sub/nested.py",
    "ax.py", "dx.py", "ay.py", "dy.py", "q1.py", "q12.py",
    "#hash.py", "!bang.py", "trailing.py",
    "pkg/j.tmp.py", "pkg/local.py", "pkg/inner/local.py",
]


GIT_IGNORED = {
    "!bang.py", "#hash.py", "a.gen.py", "ax.py", "cache", "cache/e.py",
    "docs/draft.py", "docs/x/draft.py", "docs/x/y/draft.py", "dy.py",
    "lib/h.py", "lib/sub", "lib/sub/i.py", "out", "out/c.py",
    "pkg/b.gen.py", "pkg/cache", "pkg/cache/f.py", "pkg/deep/cache",
    "pkg/deep/cache/g.py", "pkg/j.tmp.py", "pkg/local.py", "pkg/out",
    "pkg/out/d.py", "q1.py", "sub/nested.py", "top_only.py", "trailing.py",
}


def make_tree(root, files, gitignores):
    for file in files:
        path = root / file
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
    for folder, text in gitignores.items():
        (root / folder / ".gitignore").write_text(text)


def all_paths(root):
    """Relative paths of all files and folders in `root` except .git."""
    return {
        str(p.relative_to(root)).replace("\\", "/")
        for p in root.rglob("*")
        if ".git" not in p.relative_to(root).parts
        and p.name != ".gitignore"
    }


def relative_paths(root, paths):
    return {
        str(type(root)(p).relative_to(root)).replace("\\", "/")
        for p in paths
    } - {"."}


def watched_paths(root, **kwargs):
    scandir_filter = ScandirFilter(str(root), **kwargs)
    paths = DirectorySnapshot(str(root), listdir=scandir_filter).paths
    return relative_paths(root, paths)


def test_matches_git(tmp_path):
    """Test that the watcher drops exactly the paths git ignores."""
    root = tmp_path / "project"
    make_tree(root, FILES, {".": ROOT_GITIGNORE, "pkg": PKG_GITIGNORE})
    (root / ".git").mkdir()

    assert watched_paths(root) == all_paths(root) - GIT_IGNORED


def test_matches_git_in_repository_subfolder(tmp_path):
    """
    Test that the .gitignore files between the project and the repository
    root, and the repository's info/exclude file are followed.
    """
    repo = tmp_path / "repo"
    root = repo / "sub" / "project"
    make_tree(root, ["main.py", "a.skip.py", "b.excluded.py", "c.mid.py",
                     "d/e.py"], {})
    (repo / ".git" / "info").mkdir(parents=True)
    (repo / ".gitignore").write_text("*.skip.py\n/sub/project/d/\n")
    (repo / "sub" / ".gitignore").write_text("*.mid.py\n")
    (repo / ".git" / "info" / "exclude").write_text("*.excluded.py\n")

    # git check-ignore ignores all paths in the project except main.py
    assert watched_paths(root) == {"main.py"}


def test_gitignore_edits_apply_on_next_snapshot(tmp_path):
    root = tmp_path / "project"
    make_tree(root, ["main.py", "pkg/module.py"], {".": "*.gen.py\n"})
    scandir_filter = ScandirFilter(str(root))

    def paths():
        return DirectorySnapshot(str(root), listdir=scandir_filter).paths

    assert str(root / "pkg") in paths()

    with open(root / ".gitignore", "a") as f:
        f.write("pkg/\n")
    assert str(root / "pkg") not in paths()


def test_follow_gitignore_disabled(tmp_path):
    root = tmp_path / "project"
    make_tree(root, ["main.py", "a.gen.py"], {".": "*.gen.py\n"})

    assert watched_paths(root, follow_gitignore=False) == {
        "main.py", "a.gen.py"
    }


@pytest.mark.parametrize(
    "pattern, path, is_dir, ignored",
    [("foo/", "foo", True, True),
     ("foo/", "foo", False, False),
     ("*.py", "a/b.py", False, True),
     ("a/*.py", "a/b/c.py", False, False),
     ("a/**/c.py", "a/c.py", False, True),
     ("a/**/c.py", "a/b/d/c.py", False, True),
     ("**", "a/b", False, True)]
)
def test_rules(pattern, path, is_dir, ignored):
    rules = GitignoreRules(parse_gitignore([pattern]))
    assert rules.ignores(path, is_dir) == ignored


def test_rules_last_pattern_wins():
    rules = GitignoreRules(parse_gitignore(["*.py", "!keep.py"]))
    assert rules.ignores("a.py", False)
    assert not rules.ignores("keep.py", False)

    rules = rules.extended(parse_gitignore(["keep.py"]))
    assert rules.ignores("keep.py", False)


@pytest.mark.parametrize(
    "pattern, path, ignored",
    [("x[!-a]", "x5", True),
     ("x[!-a]", "x-", False),
     (r"x[a\]b]", "x]", True),
     (r"x[a\]b]", "xb", True),
     (r"x[a\]b]", "xab]", False),
     ("foo\\\\ ", "foo\\", True),
     ("foo\\ ", "foo ", True),
     ("x[a", "x[a", False),
     ("a\\", "a\\", False)]
)
def test_rules_edge_cases(pattern, path, ignored):
    """Results checked with git check-ignore."""
    rules = GitignoreRules(parse_gitignore([pattern]))
    assert rules.ignores(path, False) == ignored


def test_gitignore_with_bom(tmp_path):
    root = tmp_path / "project"
    make_tree(root, ["main.py", "secret.py"], {})
    (root / ".gitignore").write_bytes(b"\xef\xbb\xbfsecret.py\n")

    assert watched_paths(root) == {"main.py"}


@pytest.mark.skipif(os.name == "nt", reason="Needs symlinks")
def test_symlink_to_folder_is_not_a_folder(tmp_path):
    """Git doesn't match symlinks with patterns for folders."""
    root = tmp_path / "project"
    make_tree(root, ["real/a.py"], {".": "link/\n"})
    (root / "link").symlink_to(root / "real")

    assert watched_paths(root) == {"real", "real/a.py", "link", "link/a.py"}


@pytest.mark.parametrize(
    "pattern, path",
    [("*a*a*a*a*a*b", "a" * 60),
     ("x/" + "**/" * 8 + "b", "x/" + "a/" * 40 + "c")]
)
def test_rules_match_in_polynomial_time(pattern, path):
    rules = GitignoreRules(parse_gitignore([pattern]))

    start = time.perf_counter()
    assert not rules.ignores(path, False)
    assert time.perf_counter() - start < 0.5


@pytest.mark.parametrize(
    "pattern, path, ignored",
    [("a*b*c", "abxbc", True),
     ("a*b*c", "abcx", False),
     ("*x*", "axbxc", True),
     ("a/**/b/**/c", "a/b/x/b/c", True),
     ("a/**/b/**/c", "a/b/c/b", False),
     ("a/**/b*/c", "a/x/b1/y/b2/c", True),
     ("**/a/**", "x/a/y", True),
     ("a/**/**/b", "a/b", True)]
)
def test_rules_with_several_stars(pattern, path, ignored):
    """Results checked with git check-ignore."""
    rules = GitignoreRules(parse_gitignore([pattern]))
    assert rules.ignores(path, False) == ignored


def test_warning_when_root_is_ignored(tmp_path, caplog):
    repo = tmp_path / "home"
    root = repo / "project"
    make_tree(root, ["main.py"], {".": "*\n"})
    (repo / ".git").mkdir()
    (repo / ".gitignore").write_text("*\n")
    (root / ".gitignore").unlink()

    with caplog.at_level("WARNING"):
        assert watched_paths(root) == set()
    assert "are ignored by .gitignore files" in caplog.text


def test_decisions_are_cached_until_gitignore_changes(tmp_path, mocker):
    root = tmp_path / "project"
    make_tree(root, ["main.py", "a.gen.py", "pkg/b.py"], {".": "*.gen.py\n"})
    scandir_filter = ScandirFilter(str(root))
    ignores = mocker.spy(GitignoreRules, "ignores")

    def paths():
        snapshot = DirectorySnapshot(str(root), listdir=scandir_filter)
        return relative_paths(root, snapshot.paths)

    assert paths() == {"main.py", "pkg", "pkg/b.py"}
    calls = ignores.call_count

    assert paths() == {"main.py", "pkg", "pkg/b.py"}
    assert ignores.call_count == calls

    (root / "c.gen.py").touch()
    assert paths() == {"main.py", "pkg", "pkg/b.py"}
    assert ignores.call_count == calls + 1

    with open(root / ".gitignore", "a") as f:
        f.write("pkg/\n")
    assert paths() == {"main.py"}
