# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for vcs.py
"""

# Standard library imports
import os
import os.path as osp
import sys

# Test library imports
import pytest

# Local imports
from spyder.utils.vcs import (ActionToolNotFound, get_git_revision,
                              get_vcs_root, run_vcs_tool)


@pytest.mark.skipif(os.environ.get('CI', None) is None,
                    reason="Not to be run outside of CIs")
def test_vcs_tool():
    if sys.platform.startswith('linux'):
        with pytest.raises(ActionToolNotFound):
            run_vcs_tool(osp.dirname(__file__), 'browse')
    else:
        assert run_vcs_tool(osp.dirname(__file__), 'browse')
        assert run_vcs_tool(osp.dirname(__file__), 'commit')


def test_vcs_root(tmpdir):
    directory = tmpdir.mkdir('foo')
    assert get_vcs_root(str(directory)) == None
    assert get_vcs_root(osp.dirname(__file__)) != None


@pytest.mark.skipif(os.name == 'nt' and os.environ.get('AZURE') is not None,
                    reason="Fails on Windows/Azure")
def test_git_revision():
    root = get_vcs_root(osp.dirname(__file__))
    assert get_git_revision(osp.dirname(__file__)) == (None, None)
    assert all([isinstance(x, str) for x in get_git_revision(root)])


if __name__ == "__main__":
    pytest.main()
