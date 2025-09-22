# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Pythonpath manager utils.
"""

# Standard library imports
import os
import os.path as osp
import re

# Local imports
from spyder.utils.environ import envdict2listdict


def check_path(path: str) -> bool:
    """
    Check that `path` is not a [site|dist]-packages folder or a Conda
    distribution `pkgs` directory.
    """
    pattern_string = r'(ana|mini|micro)(conda|mamba|forge)\d*(/base)*/pkgs'
    if os.name == 'nt':
        path_appdata = os.getenv("APPDATA").replace('\\', '/')
        pattern_string = (
            f'.*({pattern_string}'
            r'|(l|L)ib/(site|dist)-packages.*'
            f'|(AppData|{path_appdata})/Roaming/Python).*'
        )
    else:
        pattern_string = (
            f'.*({pattern_string}'
            r'|(lib|lib64)/'
            r'(python|python\d+|python\d+\.\d+)/'
            r'(site|dist)-packages).*'
        )
    pattern = re.compile(pattern_string, re.IGNORECASE)

    path_norm = path.replace('\\', '/')
    return pattern.match(path_norm) is None


def get_system_pythonpath(env: dict) -> tuple:
    """Get paths from PYTHONPATH environment variable."""
    env = envdict2listdict(env)
    pythonpath = env.get('PYTHONPATH', [])

    if not isinstance(pythonpath, list):
        pythonpath = [pythonpath]

    # Discard removed paths and those that don't pass our check
    pythonpath = [
        path for path in pythonpath
        if (osp.isdir(path) and check_path(path))
    ]

    return tuple(pythonpath)
