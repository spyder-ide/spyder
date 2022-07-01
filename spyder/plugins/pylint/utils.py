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
import pylint.config


def _find_pylintrc_path(path):
    os.chdir(path)
    return pylint.config.find_pylintrc()


def get_pylintrc_path(search_paths=None, home_path=None):
    """Get the path to the highest pylintrc file on a set of search paths."""
    current_cwd = os.getcwd()
    pylintrc_path = None
    if home_path is None:
        home_path = osp.expanduser("~")

    # Iterate through the search paths until a unique pylintrc file is found
    try:
        pylintrc_paths = [
            _find_pylintrc_path(path) for path in search_paths if path]
        pylintrc_path_home = _find_pylintrc_path(home_path)
        for pylintrc_path in pylintrc_paths:
            if (pylintrc_path is not None
                    and pylintrc_path != pylintrc_path_home):
                break
    finally:  # Ensure working directory is restored if any an error occurs
        os.chdir(current_cwd)

    return pylintrc_path
