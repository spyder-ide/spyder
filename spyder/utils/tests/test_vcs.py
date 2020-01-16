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
from spyder.utils.programs import run_program
from spyder.utils.vcs import (ActionToolNotFound, get_git_refs,
                              get_git_remotes, get_git_revision, get_vcs_root,
                              get_vcs_status, remote_to_url, run_vcs_tool)
from spyder.utils import programs


HERE = os.path.abspath(os.path.dirname(__file__))


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
    assert get_vcs_root(str(directory)) is None
    assert get_vcs_root(osp.dirname(__file__)) is not None


@pytest.mark.skipif(os.name == 'nt' and os.environ.get('AZURE') is not None,
                    reason="Fails on Windows/Azure")
def test_git_revision():
    root = get_vcs_root(osp.dirname(__file__))
    assert get_git_revision(osp.dirname(__file__)) == (None, None)
    assert all([isinstance(x, str) for x in get_git_revision(root)])


def test_no_git(monkeypatch):

    def mockreturn(program_name):
        return None

    monkeypatch.setattr(programs, 'find_program', mockreturn)
    branch_tags, branch, files_modified = get_git_refs(__file__)
    assert len(branch_tags) == 0
    assert branch == ''
    assert len(files_modified) == 0


def test_get_git_refs():
    branch_tags, branch, files_modified = get_git_refs(__file__)
    assert bool(branch)  # This must always return a branch_name
    assert len(files_modified) >= 0

    # It seems when Travis run tests on tags, master doesn't
    # appear among the list of git branches.
    if not os.environ.get('TRAVIS_TAG'):
        assert any(['master' in b for b in branch_tags])


def test_vcs_state(tmpdir):
    """Test the vcs state of a directory and subdirectories."""
    test_dir = os.getcwd()
    tmpdir.chdir()
    subdir = str(tmpdir.mkdir('subdir'))
    print(repr(subdir))
    proc = run_program('git', ['init'], cwd=subdir)
    proc.communicate()
    file = osp.join(subdir, 'test.py')
    open(file, 'w').close()
    assert get_vcs_status(subdir) != ({}, {})
    assert get_vcs_status(str(tmpdir)) != ({}, {})
    os.chdir(test_dir)


def test_get_git_remotes():
    remotes = get_git_remotes(HERE)
    assert 'origin' in remotes


@pytest.mark.parametrize(
    'input_text, expected_output',
    [
        ('https://github.com/neophnx/spyder.git',
         'https://github.com/neophnx/spyder'),
        ('http://github.com/neophnx/spyder.git',
         'http://github.com/neophnx/spyder'),
        ('git@github.com:goanpeca/spyder.git',
         'https://github.com/goanpeca/spyder'),
    ]
)
def test_remote_to_url(input_text, expected_output):
    output = remote_to_url(input_text)
    assert expected_output == output


if __name__ == "__main__":
    pytest.main()
