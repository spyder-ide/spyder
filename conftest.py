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

import math
import os
import os.path as osp
import shutil
import subprocess
import sys
import warnings


# ---- To activate/deactivate certain things for pytest's only
# NOTE: Please leave this before any other import here!!
os.environ['SPYDER_PYTEST'] = 'True'


# ---- Detect if we're running in CI
# Note: Don't import from spyder to keep this file free from local
# imports.
running_in_ci = bool(os.environ.get('CI'))


# ---- Handle subrepos
# NOTE: Please don't move this from here!
# Add subrepo paths to sys.path locally. When running in CI, subrepos
# are installed to the env.
if not running_in_ci:
    HERE = osp.dirname(osp.abspath(__file__))
    DEPS_PATH = osp.join(HERE, 'external-deps')
    i = 0
    for path in os.listdir(DEPS_PATH):
        external_dep_path = osp.join(DEPS_PATH, path)
        sys.path.insert(i, external_dep_path)
        i += 1


# ---- Install PyLS locally when not running in CI
if not running_in_ci:
    # Create an egg-info folder to declare the PyLS subrepo entry points.
    pyls_submodule = osp.join(DEPS_PATH, 'python-lsp-server')
    pyls_installation_dir = osp.join(pyls_submodule, '.installation-dir')
    pyls_installation_egg = osp.join(
        pyls_submodule, 'python_lsp_server.egg-info')

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


# ---- Auxiliary functions
def get_group_size(total_items, total_groups):
    """Return the group size."""
    return int(math.ceil(float(total_items) / total_groups))


def get_group(items, group_size, group_id):
    """Get the items from the passed in group based on group size."""
    start = group_size * (group_id - 1)
    end = start + group_size

    if start >= len(items) or start < 0:
        raise ValueError("Invalid group argument")

    return items[start:end]


# ---- Pytest adjustments
import pytest

def pytest_addoption(parser):
    """Add option to run slow tests."""
    parser.addoption("--run-slow", action="store_true", default=False,
                     dest="run-slow", help="Run slow tests")
    parser.addoption('--group-count', dest='group-count', type=int,
                    help='The number of groups to split the tests into')
    parser.addoption("--group", type=int, dest="group",
                     help="The group of tests that should be executed'")


def pytest_collection_modifyitems(config, items):
    """
    Decide what tests to run (slow or fast) according to the --run-slow
    option.
    """
    slow_option = config.getoption("run-slow")
    group_count_option = config.getoption("group-count")
    group_option = config.getoption("group")

    tests_to_run = []
    for item in items:
        if slow_option:
            if "slow" in item.keywords:
                tests_to_run.append(item)
        else:
            if "slow" not in item.keywords:
                tests_to_run.append(item)

    if group_count_option and group_option:
        group_size = get_group_size(len(tests_to_run), group_count_option)
        tests_to_run = get_group(tests_to_run, group_size, group_option)

    items[:] = tests_to_run


@pytest.fixture(autouse=True)
def reset_conf_before_test():
    from spyder.config.manager import CONF
    CONF.reset_to_defaults(notification=False)

    from spyder.plugins.completion.api import COMPLETION_ENTRYPOINT
    from spyder.plugins.completion.plugin import CompletionPlugin

    # Restore completion clients default settings, since they
    # don't have default values on the configuration.
    from pkg_resources import iter_entry_points

    provider_configurations = {}
    for entry_point in iter_entry_points(COMPLETION_ENTRYPOINT):
        Provider = entry_point.resolve()
        provider_name = Provider.COMPLETION_PROVIDER_NAME

        (provider_conf_version,
         current_conf_values,
         provider_defaults) = CompletionPlugin._merge_default_configurations(
            Provider, provider_name, provider_configurations)

        new_provider_config = {
            'version': provider_conf_version,
            'values': current_conf_values,
            'defaults': provider_defaults
        }
        provider_configurations[provider_name] = new_provider_config

    CONF.set('completions', 'provider_configuration', provider_configurations,
             notification=False)
