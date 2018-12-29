# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for explorer.py
"""

# Standard imports
import os
import os.path as osp

# Test library imports
import pytest

from qtpy.QtWidgets import QApplication

# Local imports
from spyder.plugins.explorer.widgets import (FileExplorerTest,
                                             ProjectExplorerTest, DirView)


@pytest.fixture
def file_explorer(qtbot):
    """Set up FileExplorerTest."""
    widget = FileExplorerTest()
    qtbot.addWidget(widget)
    return widget


@pytest.fixture
def project_explorer(qtbot):
    """Set up FileExplorerTest."""
    widget = ProjectExplorerTest()
    qtbot.addWidget(widget)
    return widget


def test_file_explorer(file_explorer):
    """Run FileExplorerTest."""
    file_explorer.resize(640, 480)
    file_explorer.show()
    assert file_explorer


def test_project_explorer(project_explorer):
    """Run ProjectExplorerTest."""
    project_explorer.resize(640, 480)
    project_explorer.show()
    assert project_explorer


def test_copy_paste_files_or_paths(qtbot, tmpdir):
    tmpdir.join('script.py').ensure()
    window = DirView()
    window.show()
    qtbot.addWidget(window)
    fnames = [osp.join(tmpdir, 'script.py')]
    window.copy_path(fnames=fnames, method='absolute')
    cb = QApplication.clipboard()
    #  test copy absolute path
    asb_path = cb.text(mode=cb.Clipboard)
    cb.clear(mode=cb.Clipboard)
    assert osp.join(tmpdir, 'script.py').replace(os.sep, "/") == asb_path
    #  test copy relative path
    window.copy_path(fnames=fnames, method='relative')
    rel_path = cb.text(mode=cb.Clipboard)
    cb.clear(mode=cb.Clipboard)
    assert 'script.py' == osp.basename(rel_path)


if __name__ == "__main__":
    pytest.main()
