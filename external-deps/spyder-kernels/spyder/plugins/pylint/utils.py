# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © 2020- Spyder Project Contributors
#
# Released under the terms of the MIT License
# ----------------------------------------------------------------------------

"""Utility functions for Spyder's Pylint Static Code Analysis plugin."""


# Standard library imports
import os
import os.path as osp

# Third party imports
# This is necessary to avoid a crash at startup
# Fixes spyder-ide/spyder#20079
try:
    from pylint import config as pylint_config
except Exception:
    pylint_config = None


def _find_pylintrc_path(path):
    if pylint_config is not None:
        os.chdir(path)
        for p in pylint_config.find_default_config_files():
            # return the first config found as str
            return str(p)


def get_pylintrc_path(search_paths=None, home_path=None):
    """Get the path to the highest pylintrc file on a set of search paths."""
    current_cwd = os.getcwd()
    pylintrc_path = None
    if home_path is None:
        home_path = osp.expanduser("~")

    # Iterate through the search paths until a unique pylintrc file is found
    try:
        pylintrc_paths = [
            _find_pylintrc_path(path) for path in search_paths if path
        ]
        pylintrc_path_home = _find_pylintrc_path(home_path)

        for pylintrc_path in pylintrc_paths:
            if (
                pylintrc_path is not None
                and pylintrc_path != pylintrc_path_home
            ):
                break
    except Exception:
        # * Capturing all exceptions is necessary to solve issues such as
        # spyder-ide/spyder#21218.
        # * Ensure working directory is restored if any error occurs.
        os.chdir(current_cwd)

    return pylintrc_path
