# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Pythonpath manager utils.
"""

import os
import os.path as osp
import re

from spyder.utils.environ import get_user_env


def check_path(path):
    """Check that `path` is not a [site|dist]-packages folder."""
    if os.name == 'nt':
        pattern = re.compile(r'.*(l|L)ib/(site|dist)-packages.*')
    else:
        pattern = re.compile(
            r'.*(lib|lib64)/'
            '(python|python\d+|python\d+\.\d+)/'
            '(site|dist)-packages.*'
        )

    path_norm = path.replace('\\', '/')
    return pattern.match(path_norm) is None


def get_system_pythonpath():
    """Get paths from PYTHONPATH environment variable."""
    env = get_user_env()
    pythonpath = env.get('PYTHONPATH', [])

    if not isinstance(pythonpath, list):
        pythonpath = [pythonpath]

    # Discard removed paths and those that don't pass our check
    pythonpath = [
        path for path in pythonpath
        if (osp.isdir(path) and check_path(path))
    ]

    return tuple(pythonpath)
