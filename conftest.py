# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Configuration file for Pytest

NOTE: DO NOT add fixtures here. It could generate problems with
      QtAwesome being called before a QApplication is created.
"""

import os
import os.path as osp
import shutil
import subprocess
import sys
import warnings


# To activate/deactivate certain things for pytest's only
# NOTE: Please leave this before any other import here!!
os.environ['SPYDER_PYTEST'] = 'True'

# Add external dependencies subrepo paths to sys.path
# NOTE: Please don't move this from here!
HERE = osp.dirname(osp.abspath(__file__))
DEPS_PATH = osp.join(HERE, 'external-deps')
i = 0
for path in os.listdir(DEPS_PATH):
    external_dep_path = osp.join(DEPS_PATH, path)
    sys.path.insert(i, external_dep_path)
    i += 1

# Install PyLS locally. This fails on Windows and our CIs
if os.name != 'nt' or os.name == 'nt' and not bool(os.environ.get('CI')):
    # Create an egg-info folder to declare the PyLS subrepo entry points.
    pyls_submodule = osp.join(DEPS_PATH, 'python-language-server')
    pyls_installation_dir = osp.join(pyls_submodule, '.installation-dir')
    pyls_installation_egg = osp.join(
        pyls_submodule, 'python_language_server.egg-info')

    # Remove previous local PyLS installation.
    if osp.exists(pyls_installation_dir) or osp.exists(pyls_installation_egg):
        shutil.rmtree(pyls_installation_dir, ignore_errors=True)
        shutil.rmtree(pyls_installation_egg, ignore_errors=True)

    subprocess.check_output(
        [sys.executable,
         '-W',
         'ignore',
         'setup.py',
         'develop',
         '--no-deps',
         '--install-dir',
         pyls_installation_dir],
        env={**os.environ, **{'PYTHONPATH': pyls_installation_dir}},
        cwd=pyls_submodule
    )

# Pytest adjustments
import pytest

# Remove temp conf_dir before starting the tests
from spyder.config.base import get_conf_path
conf_dir = get_conf_path()
if osp.isdir(conf_dir):
    shutil.rmtree(conf_dir)


def pytest_addoption(parser):
    """Add option to run slow tests."""
    parser.addoption("--run-slow", action="store_true",
                     default=False, help="Run slow tests")


def pytest_collection_modifyitems(config, items):
    """
    Decide what tests to run (slow or fast) according to the --run-slow
    option.
    """
    slow_option = config.getoption("--run-slow")
    skip_slow = pytest.mark.skip(reason="Need --run-slow option to run")
    skip_fast = pytest.mark.skip(reason="Don't need --run-slow option to run")

    for item in items:
        if slow_option:
            if "slow" not in item.keywords:
                item.add_marker(skip_fast)
        else:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)
