# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Utilities to install/remove python-lsp-server when running our tests locally
or Spyder from bootstrap.
"""

import os
import os.path as osp
import re
import shutil
import subprocess
import sys


# ---- Constants
HERE = osp.dirname(osp.abspath(__file__))
DEPS_PATH = osp.join(HERE, 'external-deps')
SUBMODULE = osp.join(DEPS_PATH, 'python-lsp-server')
INSTALLATION_DIR = osp.join(SUBMODULE, '.installation-dir')
INSTALLATION_EGG = osp.join(SUBMODULE, 'python_lsp_server.egg-info')


# ---- Functions
def remove_installation():
    """Remove previous temporary installation."""
    if osp.exists(INSTALLATION_DIR) or osp.exists(INSTALLATION_EGG):
        shutil.rmtree(INSTALLATION_DIR, ignore_errors=True)
        shutil.rmtree(INSTALLATION_EGG, ignore_errors=True)


def get_version():
    """Get current version to pass it to setuptools-scm."""
    req_file = osp.join(HERE, 'requirements', 'conda.txt')
    with open(req_file, 'r') as f:
        lines = f.readlines()

    for line in lines:
        if 'python-lsp-server' in line:
            # Get version part of dependency line
            version = line.strip().split()[1]

            # Get lower bound
            version = version.split(',')[0]

            # Remove comparison signs and only leave version number
            version = re.search(r'\d+.*', version).group()

    return version


def install():
    """Install subrepo locally."""
    subprocess.check_output(
        [sys.executable,
         '-W',
         'ignore',
         'setup.py',
         'develop',
         '--no-deps',
         '--install-dir',
         INSTALLATION_DIR],
        env={
            **os.environ,
            **{'PYTHONPATH': INSTALLATION_DIR},
            **{'SETUPTOOLS_SCM_PRETEND_VERSION': get_version()}
        },
        cwd=SUBMODULE
    )


# This is necessary to install the subrepo on CIs
if __name__ == "__main__":
    print(get_version())
