#!/usr/bin/env python3
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Helper script for installing spyder and external-deps locally in editable mode.
"""

import argparse
import os
import sys
from logging import Formatter, StreamHandler, getLogger
from pathlib import Path
from subprocess import check_output

from importlib_metadata import PackageNotFoundError, distribution
from packaging.requirements import Requirement

DEVPATH = Path(__file__).resolve().parent
DEPS_PATH = DEVPATH / 'external-deps'
BASE_COMMAND = [sys.executable, '-m', 'pip', 'install', '--no-deps']

REPOS = {}
for p in [DEVPATH] + list(DEPS_PATH.iterdir()):
    if p.name.startswith('.') or not p.is_dir() and not (
            (p / 'setup.py').exists() or (p / 'pyproject.toml').exists()):
        continue
    try:
        dist = distribution(p.name)._path
    except PackageNotFoundError:
        dist = None
        editable = None
    else:
        editable = (p == dist or p in dist.parents)

    REPOS[p.name] = {'repo': p, 'dist': dist, 'editable': editable}

# ---- Setup logger
fmt = Formatter('%(asctime)s [%(levelname)s] [%(name)s] -> %(message)s')
h = StreamHandler()
h.setFormatter(fmt)
logger = getLogger('InstallSubRepos')
logger.addHandler(h)
logger.setLevel('INFO')


def get_python_lsp_version():
    """Get current version to pass it to setuptools-scm."""
    req_file = DEVPATH / 'requirements' / 'conda.txt'
    with open(req_file, 'r', encoding='utf-8') as f:
        for line in f:
            if 'python-lsp-server' not in line:
                continue

            version = next(iter(Requirement(line).specifier)).version

            break

    return version


def install_repo(name, editable=False):
    """
    Install a single repo from source located in spyder/external-deps, ignoring
    dependencies, in standard or editable mode.

    Parameters
    ----------
    name : str
        Must be 'spyder' or the distribution name of a repo in
        spyder/external-deps.
    editable : bool (False)
        Install repo in editable mode (True) or standard mode (False).
        This uses the `-e` flag.

    """
    try:
        repo_path = REPOS[name]['repo']
    except KeyError:
        logger.warning(
            'Distribution %r not valid. Must be one of %s', name, set(REPOS.keys()))
        return

    install_cmd = BASE_COMMAND.copy()

    # PyLSP requires pretend version
    env = None
    if name == 'python-lsp-server':
        env = {**os.environ}
        env.update({'SETUPTOOLS_SCM_PRETEND_VERSION': get_python_lsp_version()})

    if editable:
        # Add edit flag to install command
        install_cmd.append('-e')
        mode = 'editable'
    else:
        mode = 'standard'

    logger.info('Installing %r from source in %s mode.', name, mode)
    install_cmd.append(repo_path.as_posix())
    check_output(install_cmd, env=env)


def main(install=tuple(REPOS.keys()), no_install=tuple(), **kwargs):
    """
    Install all subrepos from source.

    Parameters
    ----------
    install : iterable (spyder and all repos in spyder/external-deps)
        Distribution names of repos to be installed from spyder/external-deps.
    no_install : iterable ()
        Distribution names to exclude from install.
    **kwargs :
        Keyword arguments passed to `install_repo`.

    """
    _install = set(install) - set(no_install)
    for repo in _install:
        install_repo(repo, **kwargs)


if __name__ == '__main__':
    # ---- Parse command line

    parser = argparse.ArgumentParser(
        usage="python install_dev_repos.py [options]")
    parser.add_argument(
        '--install', nargs='+',
        default=REPOS.keys(),
        help="Space-separated list of distribution names to install, e.g. "
             "qtconsole spyder-kernels. If option not provided, then all of "
             "the repos in spyder/external-deps are installed"
    )
    parser.add_argument(
        '--no-install', nargs='+', default=[],
        help="Space-separated list of distribution names to exclude from "
             "install. Default is empty list."
    )
    parser.add_argument(
        '--editable', action='store_true', default=False,
        help="Install in editable mode."
    )

    args = parser.parse_args()

    # ---- Install repos locally
    main(**vars(args))
