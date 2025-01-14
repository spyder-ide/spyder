# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""Tests for conda.py"""

# Standard library imports
import os
import sys
import time

# Third party imports
import pytest
from spyder_kernels.utils.pythonenv import is_conda_env

# Local imports
from spyder.config.base import running_in_ci
from spyder.plugins.ipythonconsole.tests.conftest import get_conda_test_env
from spyder.utils.conda import (
    find_conda,
    get_conda_root_prefix,
    get_list_conda_envs,
    get_list_conda_envs_cache,
    get_spyder_conda_channel,
)

if not is_conda_env(sys.prefix):
    pytest.skip("Requires conda to be installed", allow_module_level=True)

if os.name == 'nt':
    TEST_PYEXEC = 'c:/miniconda/envs/foobar/python.exe'
else:
    TEST_PYEXEC = '/miniconda/envs/foobar/bin/python'


def test_get_conda_root_prefix():
    output = get_conda_root_prefix(TEST_PYEXEC)
    if os.name == 'nt':
        assert output == 'c:/miniconda'
    else:
        assert output == '/miniconda'

    assert 'envs' not in get_conda_root_prefix(sys.executable)


@pytest.mark.skipif(not running_in_ci(), reason="Only meant for CIs")
def test_find_conda():
    # Standard test
    assert find_conda()

    # Test with test environment
    pyexec = get_conda_test_env()[1]

    # Temporarily remove CONDA_EXE and MAMBA_EXE, if present
    conda_exe = os.environ.pop('CONDA_EXE', None)
    mamba_exe = os.environ.pop('MAMBA_EXE', None)

    assert find_conda(pyexec)

    # Restore os.environ
    if conda_exe is not None:
        os.environ['CONDA_EXE'] = conda_exe
    if mamba_exe is not None:
        os.environ['MAMBA_EXE'] = mamba_exe


@pytest.mark.skipif(not running_in_ci(), reason="Only meant for CIs")
def test_get_list_conda_envs():
    output = get_list_conda_envs()

    expected_envs = ['base', 'jedi-test-env', 'spytest-ž', 'test']
    expected_envs = ['Conda: ' + env for env in expected_envs]

    assert set(expected_envs) == set(output.keys())


@pytest.mark.skipif(not running_in_ci(), reason="Only meant for CIs")
def test_get_list_conda_envs_cache():
    time0 = time.time()
    output = get_list_conda_envs_cache()
    time1 = time.time()

    assert output != {}
    assert (time1 - time0) < 0.01


@pytest.mark.skipif(not running_in_ci(), reason="Only meant for CIs")
def test_get_spyder_conda_channel():
    channel, channel_url = get_spyder_conda_channel()
    assert channel == "pypi"
    assert channel_url == "https://conda.anaconda.org/pypi"


if __name__ == "__main__":
    pytest.main()
