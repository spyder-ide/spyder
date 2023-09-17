# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Conda/anaconda utilities."""

# Standard library imports
from glob import glob
import json
import os
import os.path as osp
import sys

from spyder_kernels_server.conda_utils import (
    get_conda_env_path, add_quotes, find_conda, is_conda_env
)
from spyder.utils.programs import run_program, run_shell_command

WINDOWS = os.name == 'nt'
CONDA_ENV_LIST_CACHE = {}


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


def get_list_conda_envs():
    """Return the list of all conda envs found in the system."""
    global CONDA_ENV_LIST_CACHE

    env_list = {}
    conda = find_conda()
    if conda is None:
        return env_list

    cmdstr = ' '.join([conda, 'env', 'list', '--json'])
    try:
        out, __ = run_shell_command(cmdstr, env={}).communicate()
        out = out.decode()
        out = json.loads(out)
    except Exception:
        out = {'envs': []}

    for env in out['envs']:
        name = env.split(osp.sep)[-1]
        path = osp.join(env, 'python.exe') if WINDOWS else osp.join(
            env, 'bin', 'python')

        try:
            version, __ = run_program(path, ['--version']).communicate()
            version = version.decode()
        except Exception:
            version = ''

        name = ('base' if name.lower().startswith('anaconda') or
                name.lower().startswith('miniconda') else name)
        name = 'conda: {}'.format(name)
        env_list[name] = (path, version.strip())

    CONDA_ENV_LIST_CACHE = env_list
    return env_list


def get_list_conda_envs_cache():
    """Return a cache of envs to avoid computing them again."""
    return CONDA_ENV_LIST_CACHE


def is_anaconda_pkg(prefix=sys.prefix):
    """Detect if the anaconda meta package is installed."""
    if is_conda_env(prefix):
        conda_meta = osp.join(prefix, "conda-meta")
        if glob("anaconda-[0-9]*.json", root_dir=conda_meta):
            return True

    return False
