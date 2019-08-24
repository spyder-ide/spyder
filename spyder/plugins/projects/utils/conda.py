# -*- coding: utf-8 -*-
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Project creation dialog."""

from __future__ import print_function

# Standard library imports
import errno
import io
import json
import os
import os.path as osp
import sys

# Third party imports
import requests

# Local imports
from spyder.utils.programs import is_anaconda, find_program


# --- Helpers
# ----------------------------------------------------------------------------
def get_conda_environments():
    """Get conda environment paths."""
    envs = []
    if is_anaconda():
        envs_folder = '{0}{1}{0}'.format(os.sep, 'envs')
        if envs_folder in sys.prefix:
            anaconda_root = sys.prefix.split(envs_folder)[0]
            envs_path = osp.join(anaconda_root, 'envs')
            for env in os.listdir(envs_path):
                path = os.path.join(envs_path, env)
                if osp.isdir(path):
                    envs.append(os.path.join(envs_path, env))
    # TODO: Use envrionments.txt file on ~/.condarc

    return list(sorted(envs))


def get_conda_packages(prefix):
    packages = []
    if is_anaconda:
        if osp.isdir(prefix):
            conda_meta = osp.join(prefix, 'conda-meta')
            for file_ in os.listdir(conda_meta):
                fpath = osp.join(conda_meta, file_)
                if osp.isfile(fpath) and fpath.endswith('.json'):
                    with io.open(fpath, 'r') as fh:
                        data = fh.read()
                        data = json.loads(data)
                    packages.append(data)
    packages = sorted(packages, key=lambda x: x['name'])
    return packages


def get_pypi_packages():
    url = 'https://pypi.org/simple/'
    packages = []
    try:
        r = requests.get(url)
    except Exception as e:
        print(e)
    else:
        data = r.content
        for line in data.split('\n'):
            if 'href' in line:
                name = line.split('>')
                if name:
                    name = name[1].split('<')
                    if name:
                        packages.append(name[0])

    return packages


def get_conda_forge_packages():
    url = 'https://api.github.com/repos/conda-forge/feedstocks/contents/feedstocks?per_page=10000'
    packages= []
    try:
        r = requests.get(url)
    except Exception as e:
        print(e)
        pass
    else:
        packages = r.json()
        packages = [p['name'] for p in packages]

    return packages


def load_project_yml(path):
    """"""
    fpath = osp.join(path, 'anaconda-project.yml')
    import yaml
    with io.open(fpath, 'r') as fh:
        data = yaml.load(fh)
    return data


def get_project_environment_variables(path):
    """"""
    data = load_project_yml(path)
    variables = data.get('variables', {})
    return variables


def get_project_environment_packages(path):
    """"""
    data = load_project_yml(path)
    packages = data.get('packages', [])
    return packages


def get_project_environment_commands(path):
    """"""
    data = load_project_yml(path)
    commands = data.get('commands', [])
    return commands
