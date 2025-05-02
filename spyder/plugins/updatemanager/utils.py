# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

# Standard library imports
import os
from pathlib import Path
import subprocess as sp
import sys

# Local imports
from spyder.config.base import is_conda_based_app


def get_updater_info() -> (str, str):
    """
    Get spyder-updater info

    Returns
    -------
    updater_exe : str
        Full path to the spyder-updater executable. This may not exist.
    version : str
        Version of spyder-updater. If not installed, defaults to "0.0.0"
    """
    real_pyexec = Path(sys.executable).resolve()
    env_dir = real_pyexec.parent.parent
    if os.name == 'nt':
        updater_exe = (
            env_dir / "spyder-updater" / "Scripts" / "spyder-updater.exe"
        )
    else:
        env_dir = env_dir.parent
        updater_exe = env_dir / "spyder-updater" / "bin" / "spyder-updater"

    version = "0.0.0"  # Not installed
    if is_conda_based_app() and updater_exe.exists():
        cmd = " ".join([str(updater_exe), "--version"])
        proc = sp.run(cmd, shell=True, text=True, capture_output=True)
        if proc.returncode == 0:
            version = proc.stdout

    return str(updater_exe), version
