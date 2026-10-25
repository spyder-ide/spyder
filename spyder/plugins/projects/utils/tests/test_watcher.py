# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Tests for the project watcher."""

import os

from watchdog.utils.dirsnapshot import DirectorySnapshot

from spyder.plugins.projects.utils.watcher import filter_scandir


def test_filter_scandir(tmp_path):
    """Hidden and ignored folders are pruned, only editable files are kept."""
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "module.py").touch()
    (tmp_path / "pkg" / "data.bin").touch()
    (tmp_path / "pkg" / "__pycache__").mkdir()
    (tmp_path / "pkg" / "__pycache__" / "module.pyc").touch()
    (tmp_path / "build").mkdir()
    (tmp_path / "build" / "lib.py").touch()
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").touch()
    (tmp_path / ".hidden.py").touch()
    (tmp_path / "README.md").touch()

    snapshot = DirectorySnapshot(
        str(tmp_path), recursive=True, stat=os.stat, listdir=filter_scandir
    )
    paths = {os.path.relpath(p, tmp_path) for p in snapshot.paths}

    assert paths == {
        ".",
        "pkg",
        os.path.join("pkg", "module.py"),
        "README.md",
    }
