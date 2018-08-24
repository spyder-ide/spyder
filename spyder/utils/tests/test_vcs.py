# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for vcs.py
"""

# Standard library imports
import os.path as osp

# Test library imports
import pytest

# Local imports
from spyder.utils.vcs import get_git_revision, get_vcs_root, run_vcs_tool


def test_vcs_tool():
    root = get_vcs_root(osp.dirname(__file__))
    assert run_vcs_tool(root, 'browse')
    assert run_vcs_tool(root, 'commit')


def test_vcs_root(tmpdir):
    assert get_vcs_root(tmpdir.mkdir('foo')) == None
    assert get_vcs_root(osp.dirname(__file__)) != None


def test_git_revision():
    root = get_vcs_root(osp.dirname(__file__))
    assert get_git_revision(osp.dirname(__file__)) == (None, None)
    assert all([isinstance(x, str) for x in get_git_revision(root)])


if __name__ == "__main__":
    pytest.main()
