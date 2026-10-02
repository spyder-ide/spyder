# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Conversion between file system paths and ``file:`` URIs."""

from __future__ import annotations

# Standard library imports
import os.path as osp
import pathlib
from urllib.parse import urlparse
from urllib.request import url2pathname


def path_as_uri(path: str) -> str:
    """``file:`` URI of the absolute form of ``path``."""
    return pathlib.Path(osp.abspath(path)).as_uri()


def uri_as_path(uri: str) -> str:
    """File system path of a ``file:`` URI (UNC shares kept on Windows)."""
    parsed = urlparse(uri)
    netloc = "\\\\" + parsed.netloc if parsed.netloc else parsed.netloc
    return url2pathname(netloc + parsed.path)
