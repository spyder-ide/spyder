# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Conda/anaconda utilities."""

# Standard library imports
import os
import sys


def add_quotes(path):
    """Return quotes if needed for spaces on path."""
    quotes = '"' if ' ' in path and '"' not in path else ''
    return '{quotes}{path}{quotes}'.format(quotes=quotes, path=path)


def is_conda_env(prefix=None, pyexec=None):
    """Check if prefix or python executable are in a conda environment."""
    if pyexec is not None:
        pyexec = pyexec.replace('\\', '/')

    if (prefix is None and pyexec is None) or (prefix and pyexec):
        raise ValueError('Only `prefix` or `pyexec` should be provided!')

    if pyexec and prefix is None:
        prefix = get_conda_env_path(pyexec).replace('\\', '/')

    return os.path.exists(os.path.join(prefix, 'conda-meta'))


def get_conda_root_prefix(pyexec=None, quote=False):
    """
    Return conda prefix from pyexec path

    If `quote` is True, then quotes are added if spaces are found in the path.
    """
    if pyexec is None:
        conda_env_prefix = sys.prefix
    else:
        conda_env_prefix = get_conda_env_path(pyexec)

    conda_env_prefix = conda_env_prefix.replace('\\', '/')
    env_key = '/envs/'

    if conda_env_prefix.rfind(env_key) != -1:
        root_prefix = conda_env_prefix.split(env_key)[0]
    else:
        root_prefix = conda_env_prefix

    if quote:
        root_prefix = add_quotes(root_prefix)

    return root_prefix


def get_conda_activation_script(pyexec=None, quote=False):
    """
    Return full path to conda activation script.

    If `quote` is True, then quotes are added if spaces are found in the path.
    """
    if os.name == 'nt':
        activate = 'Scripts/activate'
    else:
        activate = 'bin/activate'

    script_path = os.path.join(get_conda_root_prefix(pyexec, quote=False),
                               activate).replace('\\', '/')

    if quote:
        script_path = add_quotes(script_path)

    return script_path


def get_conda_env_path(pyexec, quote=False):
    """
    Return the full path to the conda environment from give python executable.

    If `quote` is True, then quotes are added if spaces are found in the path.
    """
    pyexec = pyexec.replace('\\', '/')
    if os.name == 'nt':
        conda_env = os.path.dirname(pyexec)
    else:
        conda_env = os.path.dirname(os.path.dirname(pyexec))

    if quote:
        conda_env = add_quotes(conda_env)

    return conda_env
