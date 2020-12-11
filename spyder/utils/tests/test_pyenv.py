# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""Tests for pyenv.py"""

import os
import time

import pytest

from spyder.utils.pyenv import (
    get_list_pyenv_envs, get_list_pyenv_envs_cache
)


@pytest.mark.skipif(not bool(os.environ.get('CI')),
                    reason="Only meant for CIs")
@pytest.mark.skipif(os.name == 'nt', reason="Doesn't work on Windows")
def test_get_list_pyenv_envs():
    output = get_list_pyenv_envs()
    expected_envs = ['pyenv: 3.8.1']
    assert set(expected_envs) == set(output.keys())


@pytest.mark.skipif(not bool(os.environ.get('CI')),
                    reason="Only meant for CIs")
@pytest.mark.skipif(os.name == 'nt', reason="Doesn't work on Windows")
def test_get_list_pyenv_envs_cache():
    time0 = time.time()
    output = get_list_pyenv_envs_cache()
    time1 = time.time()

    assert output != {}
    assert (time1 - time0) < 0.01
