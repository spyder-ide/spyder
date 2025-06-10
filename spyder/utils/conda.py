# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Conda/anaconda utilities."""

# Standard library imports
from functools import lru_cache
from glob import glob
import json
import os
import os.path as osp
import sys

# Third-party imports
from packaging.version import parse
from spyder_kernels.utils.pythonenv import (
    add_quotes,
    get_conda_env_path,
    is_conda_env,
)

# Local imports
from spyder.utils.programs import find_program, run_program, run_shell_command
from spyder.config.base import is_conda_based_app

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


def find_conda(pyexec=None):
    """
    Find conda executable.

    `pyexec` is a python executable, the relative location from which to
    attempt to locate a conda executable.
    """
    conda = None

    # First try Spyder's conda executable
    if is_conda_based_app():
        root = osp.dirname(os.environ['CONDA_EXE'])
        conda = osp.join(root, 'conda.exe' if WINDOWS else 'conda')

    # Next try the environment variables
    if conda is None:
        conda = os.environ.get('CONDA_EXE') or os.environ.get('MAMBA_EXE')

    # Next try searching for the executable
    if conda is None:
        conda_exec = 'conda.bat' if WINDOWS else 'conda'
        extra_paths = [
            osp.join(get_conda_root_prefix(_pyexec), 'condabin')
            for _pyexec in [sys.executable, pyexec]
        ]
        conda = find_program(conda_exec, extra_paths)

    return conda


def find_pixi(pyexec=None):
    """
    Find pixi executable.

    `pyexec` is a python executable, the relative location from which to
    attempt to locate a pixi executable.
    """
    # Try the `PIXI_HOME` environment variable
    pixi = os.environ.get('PIXI_HOME', None)

    # Next try searching for the executable in default paths
    if pixi is None:
        pixi_exec = 'pixi.exe' if WINDOWS else 'pixi'
        pixi = find_program(pixi_exec)

    return pixi


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
        data = env.split(osp.sep)
        name = data[-1]
        path = osp.join(env, 'python.exe') if WINDOWS else osp.join(
            env, 'bin', 'python')

        if (
            # In case the environment doesn't have Python
            not osp.isfile(path)
            # Don't list the installers base env
            or (is_conda_based_app(pyexec=path) and name != "spyder-runtime")
        ):
            continue

        try:
            version, __ = run_program(path, ['--version']).communicate()
            version = version.decode()
        except Exception:
            version = ''

        name = ('base' if name.lower().startswith('anaconda') or
                name.lower().startswith('miniconda') else name)
        name = 'Conda: {}'.format(name)

        if name in env_list:
            if not (path, version.strip()) == env_list[name]:
                prev_info = env_list[name]
                prev_data = prev_info[0]
                prev_data = prev_data.split(osp.sep)
                env_list.pop(name)
                index_common_folder = 1
                end_path = 1
                if not WINDOWS:
                    end_path = 2
                for i in range(-1, -len(data) - 1, -1):
                    if data[i] == prev_data[i - end_path]:
                        index_common_folder += 1
                    else:
                        break
                path_part = prev_data[
                    -index_common_folder - end_path : -end_path
                ]
                prev_name = (
                    f'Conda: '
                    f'{"/".join(path_part)}'
                )
                env_list[prev_name] = prev_info
                name = f'Conda: {"/".join(data[-index_common_folder:])}'

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
        return None, None

    env = get_conda_env_path(sys.executable)
    cmdstr = ' '.join([conda, 'list', 'spyder', '--json', '--prefix', env])

    try:
        out, __ = run_shell_command(cmdstr, env=_env_for_conda()).communicate()
        out = out.decode()
        out = json.loads(out)
    except Exception:
        return None, None

    # Avoids iterating over non-dict objects
    if 'error' in out:
        return None, None

    # These variables can be unassigned after the next for, so we need to give
    # them a default value at this point.
    # Fixes spyder-ide/spyder#22054
    channel, channel_url = None, None

    for package_info in out:
        if package_info["name"] == 'spyder':
            channel = package_info["channel"]
            channel_url = package_info["base_url"]

    if channel_url is not None and "<develop>" in channel_url:
        channel_url = None

    return channel, channel_url


@lru_cache(maxsize=10)
def conda_version(conda_executable=None):
    """
    Get the conda version if available.

    Note: This function can get the version of other conda-like executables
    like mamba, micromamba or pixi, as well as any executable that provides a
    `--version` CLI argument.
    """
    version = parse('0')
    if not conda_executable:
        conda_executable = find_conda()
    if not conda_executable:
        return version
    try:
        version, __ = run_program(conda_executable, ['--version']).communicate()
        version = parse(version.decode().split()[-1].strip())
    except Exception:
        pass
    return version
