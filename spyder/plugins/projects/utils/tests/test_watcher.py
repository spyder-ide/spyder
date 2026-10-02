# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for the project watcher.
"""

# Standard library imports
import os

# Third party imports
import pytest
from watchdog.utils.dirsnapshot import DirectorySnapshot

# Local imports
from spyder.plugins.projects.utils.watcher import ScandirFilter


def snapshot_paths(project, **kwargs):
    scandir_filter = ScandirFilter(str(project), **kwargs)
    return DirectorySnapshot(str(project), listdir=scandir_filter).paths


def relative_paths(project, paths):
    return {
        p.relative_to(project).as_posix() for p in map(type(project), paths)
    }


@pytest.mark.parametrize("parent", ["build", ".hidden", "__pycache__"])
def test_filter_ignores_names_only_inside_project(tmp_path, parent):
    """
    Entries are filtered by their own name, so a project whose path contains
    an ignored name above its root is still tracked.
    """
    project = tmp_path / parent / "project"
    (project / "pkg").mkdir(parents=True)
    (project / "pkg" / "module.py").touch()
    (project / "pkg" / "data.bin").touch()
    for ignored in [".git", "build", "__pycache__"]:
        (project / ignored).mkdir()
        (project / ignored / "ignored.py").touch()

    paths = snapshot_paths(project, follow_gitignore=False)

    assert paths == {
        str(project),
        str(project / "pkg"),
        str(project / "pkg" / "module.py"),
    }


def test_filter_extra_folders_to_ignore(tmp_path):
    project = tmp_path / "project"
    for folder in ["vendor", "src"]:
        (project / folder).mkdir(parents=True)
        (project / folder / "module.py").touch()

    paths = snapshot_paths(
        project, follow_gitignore=False, folders_to_ignore=["vendor"]
    )

    assert relative_paths(project, paths) == {".", "src", "src/module.py"}


@pytest.mark.skipif(os.name == "nt", reason="Needs symlinks")
def test_filter_symlinked_project_uses_target_repository(tmp_path):
    """
    As git does, a project reached through a symlink follows the gitignore
    files of the repository its target is in.
    """
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    (repo / ".gitignore").write_text("ignored.py\n")
    (repo / "sub").mkdir()
    for name in ["kept.py", "ignored.py"]:
        (repo / "sub" / name).touch()
    project = tmp_path / "link"
    project.symlink_to(repo / "sub")

    paths = snapshot_paths(project)

    assert relative_paths(project, paths) == {".", "kept.py"}


@pytest.mark.skipif(os.name == "nt", reason="Needs symlinks")
def test_filter_project_under_symlinked_folder(tmp_path):
    """
    Anchored patterns in the repository's info/exclude apply, while gitignore
    files outside the repository don't when the path to the project goes
    through a symlink.
    """
    repo = tmp_path / "real" / "repo"
    (repo / ".git" / "info").mkdir(parents=True)
    (repo / ".git" / "info" / "exclude").write_text("/sub/ignored.py\n")
    (tmp_path / ".gitignore").write_text("kept.py\n")
    (repo / "sub").mkdir()
    for name in ["kept.py", "ignored.py"]:
        (repo / "sub" / name).touch()
    (tmp_path / "link").symlink_to(tmp_path / "real")
    project = tmp_path / "link" / "repo" / "sub"

    paths = snapshot_paths(project)

    assert relative_paths(project, paths) == {".", "kept.py"}
