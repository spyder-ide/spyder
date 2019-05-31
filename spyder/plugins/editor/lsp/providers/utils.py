# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Spyder Language Server Protocol Client common util functions."""


import os.path as osp
from spyder.py3compat import PY2

if PY2:
    import pathlib2 as pathlib
else:
    import pathlib


def path_as_uri(path):
    return pathlib.Path(osp.abspath(path)).as_uri()
