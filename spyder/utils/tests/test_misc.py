# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for misc.py
"""

# Standard library imports
import os

# Test library imports
import pytest

# Local imports
from spyder.utils.misc import (
    get_common_path, add_pathlist_to_PYTHONPATH
)


def test_get_common_path():
    """Test getting the common path."""
    if os.name == 'nt':
        assert get_common_path([
                                'D:\\Python\\spyder-v21\\spyder\\widgets',
                                'D:\\Python\\spyder\\spyder\\utils',
                                'D:\\Python\\spyder\\spyder\\widgets',
                                'D:\\Python\\spyder-v21\\spyder\\utils',
                                ]) == 'D:\\Python'
    else:
        assert get_common_path([
                                '/Python/spyder-v21/spyder.widgets',
                                '/Python/spyder/spyder.utils',
                                '/Python/spyder/spyder.widgets',
                                '/Python/spyder-v21/spyder.utils',
                                ]) == '/Python'


@pytest.mark.parametrize("drop_env", [True, False])
def test_add_pathlist_to_PYTHONPATH(drop_env):
    """Test for add_pathlist_to_PYTHONPATH."""
    pathlist = ['test123', 'test456']

    if drop_env:
        env = []
        expected = ['PYTHONPATH=' + pathlist[0] + os.pathsep + pathlist[1]]
    else:
        env = ['PYTHONPATH=test0']
        expected = [
            'PYTHONPATH=' +
            pathlist[0] +
            os.pathsep +
            pathlist[1] +
            os.pathsep +
            'test0'
        ]

    add_pathlist_to_PYTHONPATH(env, pathlist, drop_env=drop_env)
    assert env == expected


if __name__ == "__main__":
    pytest.main()
