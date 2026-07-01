# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Kernels Contributors
#
# Licensed under the terms of the MIT License
# (see spyder_kernels/__init__.py for details)
# -----------------------------------------------------------------------------

"""Utilities to get information about Python environments."""

# Standard library imports
from __future__ import annotations
import os
from pathlib import Path
from typing import TypedDict


class PythonEnvType:
    """Enum with the different types of Python environments we can detect."""

    Conda = "conda"
    Pixi = "pixi"
    PyEnv = "pyenv"
    Custom = "custom"  # Nor Conda or Pyenv


class PythonEnvInfo(TypedDict):
    """Schema for Python environment information."""

    path: str
    env_type: PythonEnvType
    name: str
    python_version: str

    # These keys are necessary to build the console banner in Spyder
    ipython_version: str
    sys_version: str


def add_quotes(path):
    """Return quotes if needed for spaces on path."""
    quotes = '"' if ' ' in path and '"' not in path else ''
    return '{quotes}{path}{quotes}'.format(quotes=quotes, path=path)


def get_conda_env_path(pyexec, quote=False):
    """
    Return the full path to the conda environment from a given python
    executable.

    If `quote` is True, then quotes are added if spaces are found in the path.
    """
    pyexec = pyexec.replace('\\', '/')
    if os.name == 'nt':
        conda_env = os.path.dirname(pyexec)
    else:
        conda_env = os.path.dirname(os.path.dirname(pyexec))

    if quote:
        conda_env = add_quotes(conda_env)

    return conda_env


def get_pixi_manifest_path_and_env_name(pyexec, quote=False):
    pyexec_path = Path(pyexec.replace("\\", "/"))
    pixi_env_path = pyexec_path.parents[0 if os.name == "nt" else 1]
    pixi_env_name = pixi_env_path.name
    pixi_dir_path = pixi_env_path.parents[1]

    pixi_manifest_path = None
    pixi_manifest_paths = [
        pixi_dir_path.parent / "pixi.toml",
        pixi_dir_path.parent / "pyproject.toml",
        pixi_dir_path.parent / "manifests" / "pixi-global.toml",
    ]

    for manifest_path in pixi_manifest_paths:
        if manifest_path.exists():
            pixi_manifest_path = manifest_path
            break

    if not pixi_manifest_path:
        raise FileNotFoundError(
            "No manifest file for your pixi environment was found!"
        )

    if quote:
        pixi_env_name = add_quotes(pixi_env_name)

    return str(pixi_manifest_path), pixi_env_name


def is_conda_env(prefix=None, pyexec=None):
    """Check if prefix or python executable are in a conda environment."""
    if pyexec is not None:
        pyexec = pyexec.replace('\\', '/')

    if (prefix is None and pyexec is None) or (prefix and pyexec):
        raise ValueError('Only `prefix` or `pyexec` should be provided!')

    if pyexec and prefix is None:
        prefix = get_conda_env_path(pyexec).replace('\\', '/')

    return os.path.exists(os.path.join(prefix, 'conda-meta'))


def is_pyenv_env(pyexec):
    """Check if a python executable is a Pyenv environment."""
    path = Path(pyexec)
    return "pyenv" in path.parts[:-1]


def is_pixi_env(pyexec):
    """Check if a python executable is a Pixi environment."""
    path = Path(pyexec)
    return ".pixi" in path.parts[:-1]


def get_env_dir(interpreter, only_dir=False):
    """Get the environment directory from the interpreter executable."""
    path = Path(interpreter)

    if os.name == 'nt':
        # This is enough for Conda and Pyenv envs
        env_dir = path.parent

        # This is necessary for envs created with `python -m venv`
        if env_dir.parts[-1].lower() == "scripts":
            env_dir = path.parents[1]
    else:
        env_dir = path.parents[1]

    return env_dir.parts[-1] if only_dir else str(env_dir)
