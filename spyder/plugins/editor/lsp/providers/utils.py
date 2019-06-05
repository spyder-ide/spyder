# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Spyder Language Server Protocol Client common util functions."""


import os.path as osp
from spyder.py3compat import PY2

if PY2:
    import pathlib2 as pathlib
    from urlparse import urlparse
    from urllib import url2pathname
else:
    import pathlib
    from urllib.parse import urlparse
    from urllib.request import url2pathname


def path_as_uri(path):
    return pathlib.Path(osp.abspath(path)).as_uri()


def process_uri(uri):
    uri = urlparse(uri)
    netloc, path = uri.netloc, uri.path
    # Prepend UNC share notation if we have a UNC path.
    netloc = '\\\\' + netloc if netloc else netloc
    return url2pathname(netloc + path)
