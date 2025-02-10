# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Pyenv utilities
"""

import os
import os.path as osp

from spyder.config.base import get_home_dir
from spyder.utils.programs import find_program, run_shell_command


PYENV_ENV_LIST_CACHE = {}


def get_pyenv_path(name):
    """Return the complete path of the pyenv."""
    home = get_home_dir()
    if os.name == 'nt':
        path = osp.join(
            home, '.pyenv', 'pyenv-win', 'versions', name, 'python.exe')
    elif name == '':
        path = osp.join(home, '.pyenv', 'shims', 'python')
    else:
        path = osp.join(home, '.pyenv', 'versions', name, 'bin', 'python')
    return path


def get_list_pyenv_envs():
    """Return the list of all pyenv envs found in the system."""
    global PYENV_ENV_LIST_CACHE

    env_list = {}
    pyenv = find_program('pyenv')
    if pyenv is None:
        return env_list

    cmdstr = ' '.join([pyenv, 'versions', '--bare', '--skip-aliases'])
    try:
        out, __ = run_shell_command(cmdstr, env={}).communicate()
        out = out.decode().strip()
    except Exception:
        return env_list

    out = out.split('\n') if out else []
    for env in out:
        data = env.split(osp.sep)
        path = get_pyenv_path(data[-1])

        name = f'Pyenv: {data[-1]}'
        version = f'Python {data[0]}'

        if name in env_list:
            if not (path, version) == env_list[name]:
                ant_info = env_list[name]
                ant_data = ant_info[0]
                ant_data = ant_data.split(osp.sep)
                env_list.pop(name)
                index_folder_comun = 1
                for i in range(-1, -len(data)-1, -1):
                    if data[i] == ant_data[i]:
                        index_folder_comun+=1
                    else:
                        break
                part_path = ant_data[-index_folder_comun:-1]
                ant_name = f'Pyenv: {"/".join(part_path)}'
                env_list[ant_name] = ant_info
                name = f'Pyenv: {"/".join(data[-index_folder_comun:])}'

        
        env_list[name] = (path, version)

    PYENV_ENV_LIST_CACHE = env_list
    return env_list


def get_list_pyenv_envs_cache():
    """Return a cache of envs to avoid computing them again."""
    return PYENV_ENV_LIST_CACHE
