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
    """Check if it is a conda environment, if it is run activation script."""
    if (prefix is None and pyexec is None) or (prefix and pyexec):
         raise ValueError('Only prefix or pyexec should be provided!')

    if pyexec and prefix is None:
        prefix = get_conda_env_path(pyexec)

    return os.path.exists(os.path.join(prefix, 'conda-meta'))
    

def get_conda_root_prefix(quote=False):
    """
    Return conda prefix from sys.prefix.

    If `quote` is True, then quotes are added if spaces are found in the path.
    """
    env_key = '{0}envs{0}'.format(os.sep)
    if sys.prefix.rfind(env_key) != -1:
        root_prefix = sys.prefix.split(env_key)[0]
    else:
        root_prefix = sys.prefix

    if quote:
        root_prefix = add_quotes(root_prefix)

    return root_prefix


def get_conda_activation_script(quote=False):
    """
    Return full path to conda activation script.

    If `quote` is True, then quotes are added if spaces are found in the path.
    """
    if os.name == 'nt':
        activate = 'Scripts\\activate'
    else:
        activate = 'bin/activate'

    script_path = os.path.join(get_conda_root_prefix(quote=False), activate)

    if quote:
        script_path = add_quotes(script_path)

    return script_path


def get_conda_env_path(pyexec, quote=False):
    """
    Return the full path to the conda environment from give python executable.

    If `quote` is True, then quotes are added if spaces are found in the path.
    """
    if os.name == 'nt':
        conda_env = os.path.dirname(pyexec)
    else:
        conda_env = os.path.dirname(os.path.dirname(pyexec))

    if quote:
        conda_env = add_quotes(conda_env)

    return conda_env
