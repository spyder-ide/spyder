# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Conda/anaconda utilities."""

# Standard library imports
from functools import lru_cache
import os

# Third-party imports
from packaging.version import parse

# Local imports
from spyder.utils.programs import find_program, run_program

WINDOWS = os.name == "nt"


def find_pixi(pyexec=None):
    """
    Find pixi executable.

    `pyexec` is a python executable, the relative location from which to
    attempt to locate a pixi executable.
    """
    # Try the environment variables
    pixi_home = os.environ.get('PIXI_HOME')
    pixi = None
    if pixi_home:
        pixi = os.environ.get('PIXI_HOME') or os.environ.get('MAMBA_EXE')

    # Next try searching for the executable in default paths
    if pixi is None:
        pixi_exec = 'pixi.exe' if WINDOWS else 'pixi'
        pixi = find_program(pixi_exec)

    return pixi


@lru_cache(maxsize=1)
def conda_version(pixi_executable=None):
    """Get the pixi version if available."""
    version = parse('0')
    if not pixi_executable:
        pixi_executable = find_pixi()
    if not pixi_executable:
        return version
    try:
        version, __ = run_program(pixi_executable, ['--version']).communicate()
        version = parse(version.decode().split()[-1].strip())
    except Exception:
        pass
    return version
