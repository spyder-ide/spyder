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


def match_path_to_folder(folders, path):
    # folders = [pathlib.Path(folder).parts for folder in folders]
    max_len, chosen_folder = -1, None
    path = pathlib.Path(path).parts
    for folder in folders:
        folder_parts = pathlib.Path(folder).parts
        if len(folder_parts) > len(path):
            continue
        match_len = 0
        for folder_part, path_part in zip(folder_parts, path):
            if folder_part == path_part:
                match_len += 1
        if match_len > 0:
            if match_len > max_len:
                max_len = match_len
                chosen_folder = folder
    return chosen_folder
