# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""Tests for conda.py"""

# Standard library imports
import os
import sys

# Third party imports
import pytest

# Local imports
from spyder.utils.conda import (add_quotes, get_conda_activation_script,
                                get_conda_env_path, get_conda_root_prefix)


if os.name == 'nt':
    TEST_PYEXEC = 'c:/miniconda/envs/foobar/python.exe'
else:
    TEST_PYEXEC = '/miniconda/envs/foobar/bin/python'


def test_add_quotes():
    output = add_quotes('/some path/with spaces')
    assert output == '"/some path/with spaces"'

    output = add_quotes('/some-path/with-no-spaces')
    assert output == '/some-path/with-no-spaces'


def test_get_conda_activation_script():
    output = get_conda_activation_script(TEST_PYEXEC)
    if os.name == 'nt':
        assert output == 'c:/miniconda/Scripts/activate'
    else:
        assert output == '/miniconda/bin/activate'


def test_get_conda_env_path():
    output = get_conda_env_path(TEST_PYEXEC)
    if os.name == 'nt':
        assert output == 'c:/miniconda/envs/foobar'
    else:
        assert output == '/miniconda/envs/foobar'


def test_get_conda_root_prefix():
    output = get_conda_root_prefix(TEST_PYEXEC)
    if os.name == 'nt':
        assert output == 'c:/miniconda'
    else:
        assert output == '/miniconda'

    assert 'envs' not in get_conda_root_prefix(sys.executable)


if __name__ == "__main__":
    pytest.main()
