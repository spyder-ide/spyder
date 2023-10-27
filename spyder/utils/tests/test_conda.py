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

# Local imports
from spyder.config.base import running_in_ci
from spyder.config.utils import is_anaconda
from spyder.utils.conda import (
    add_quotes, find_conda, get_conda_activation_script, get_conda_env_path,
    get_conda_root_prefix, get_list_conda_envs, get_list_conda_envs_cache,
    get_spyder_conda_channel)


if not is_anaconda():
    pytest.skip("Requires conda to be installed", allow_module_level=True)

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
    output = get_conda_activation_script()
    assert os.path.exists(output)


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


@pytest.mark.skipif(not running_in_ci(), reason="Only meant for CIs")
def test_find_conda():
    assert find_conda()


@pytest.mark.skipif(not running_in_ci(), reason="Only meant for CIs")
def test_get_list_conda_envs():
    output = get_list_conda_envs()

    expected_envs = ['base', 'jedi-test-env', 'spytest-ž', 'test']
    expected_envs = ['conda: ' + env for env in expected_envs]

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
