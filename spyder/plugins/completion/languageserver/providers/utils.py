# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Spyder Language Server Protocol Client common util functions."""

import os
import os.path as osp
from spyder.py3compat import PY2
from spyder.utils.encoding import to_unicode


if PY2:
    import pathlib2 as pathlib
    from urlparse import urlparse
    from urllib import url2pathname
    from urllib import quote as urlquote_from_bytes
else:
    import pathlib
    from urllib.parse import urlparse
    from urllib.parse import quote_from_bytes as urlquote_from_bytes
    from urllib.request import url2pathname


def as_posix(path_obj):
    """Get path as_posix as unicode using correct separator."""
    path = path_obj
    return to_unicode(str(path)).replace(os.sep, '/')


def make_as_uri(path):
    """
    As URI path for Windows.
    Reimplementation of Path.make_as_uri to use an unicode as_posix version.
    """
    drive = path.drive
    path_string = as_posix(path)
    if len(drive) == 2 and drive[1] == ':':
        # It's a path on a local drive => 'file:///c:/a/b'
        rest = path_string[2:].lstrip('/')
        return u'file:///%s/%s' % (
            drive, urlquote_from_bytes(rest.encode('utf-8')))
    else:
        # It's a path on a network drive => 'file://host/share/a/b'
        return u'file:' + urlquote_from_bytes(path_string.encode('utf-8'))


def path_as_uri(path):
    path_obj = pathlib.Path(osp.abspath(path))
    if os.name == 'nt' and PY2:
        return make_as_uri(path_obj)
    else:
        return path_obj.as_uri()


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
