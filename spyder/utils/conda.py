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


def _env_for_conda():
    """
    Required environment variables for Conda to work as expected.

    Notes
    -----
    This is needed on Windows since Conda 23.9.0
    """
    env = {}
    if os.name == 'nt':
        env_vars = [("HOMEDRIVE", "C:"), ("HOMEPATH", "\\Users\\xxxxx")]
        for var, default in env_vars:
            value = os.environ.get(var, default)
            env[var] = value

    return env


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


def get_list_conda_envs():
    """Return the list of all conda envs found in the system."""
    global CONDA_ENV_LIST_CACHE

    env_list = {}
    conda = find_conda()
    if conda is None:
        return env_list

    cmdstr = ' '.join([conda, 'env', 'list', '--json'])

    try:
        out, __ = run_shell_command(cmdstr, env=_env_for_conda()).communicate()
        out = out.decode()
        out = json.loads(out)
    except Exception:
        out = {'envs': []}

    for env in out['envs']:
        name = env.split(osp.sep)[-1]
        path = osp.join(env, 'python.exe') if WINDOWS else osp.join(
            env, 'bin', 'python')

        # In case the environment doesn't have Python
        if not osp.isfile(path):
            continue

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
        if glob(f"{conda_meta}{os.sep}anaconda-[0-9]*.json"):
            return True

    return False


def get_spyder_conda_channel():
    """Get the conda channel from which Spyder was installed."""
    conda = find_conda()

    if conda is None:
        return None

    env = get_conda_env_path(sys.executable)
    cmdstr = ' '.join([conda, 'list', 'spyder', '--json', '--prefix', env])

    try:
        out, __ = run_shell_command(cmdstr, env=_env_for_conda()).communicate()
        out = out.decode()
        out = json.loads(out)
    except Exception:
        return None

    for package_info in out:
        if package_info["name"] == 'spyder':
            channel = package_info["channel"]
            channel_url = package_info["base_url"]

    if "<develop>" in channel_url:
        channel_url = None

    return channel, channel_url
