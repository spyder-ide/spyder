# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""Tests for pyenv.py"""

import sys
import time

import pytest

from spyder.config.base import running_in_ci
from spyder.utils.programs import find_program
from spyder.utils.pyenv import get_list_pyenv_envs, get_list_pyenv_envs_cache


if not find_program('pyenv'):
    pytest.skip("Requires pyenv to be installed", allow_module_level=True)


@pytest.mark.skipif(not running_in_ci(), reason="Only meant for CIs")
@pytest.mark.skipif(not sys.platform.startswith('linux'),
                    reason="Only runs on Linux")
def test_get_list_pyenv_envs():
    output = get_list_pyenv_envs()
    expected_envs = ['pyenv: 3.8.1']
    assert set(expected_envs) == set(output.keys())


@pytest.mark.skipif(not running_in_ci(), reason="Only meant for CIs")
@pytest.mark.skipif(not sys.platform.startswith('linux'),
                    reason="Only runs on Linux")
def test_get_list_pyenv_envs_cache():
    time0 = time.time()
    output = get_list_pyenv_envs_cache()
    time1 = time.time()

    assert output != {}
    assert (time1 - time0) < 0.01
