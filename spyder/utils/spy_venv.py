#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Create virtual environment from Spyder macOS app
"""

import sys
import venv
from pathlib import Path
from subprocess import Popen, PIPE


def create_venv(name='main'):
    executable_path = Path(sys.executable).resolve().parent
    frameworks = executable_path.parent / 'Frameworks'

    venv_root_path = Path('/Users/rclary/.spyder-py3-dev/venvs')  # replace with config path
    venv_path = venv_root_path / name
    venv_frameworks = venv_path / 'Frameworks'

    venv.create(venv_path, clear=True, symlinks=True, with_pip=False)

    # venv_frameworks.unlink()  # if already exists
    venv_frameworks.symlink_to(frameworks, target_is_directory=True)

    cmd = f"""source {venv_path}/bin/activate
    curl https://bootstrap.pypa.io/get-pip.py | python
    """

    Popen(cmd, shell=True, stderr=PIPE, stdout=PIPE, stdin=PIPE)


def install_plugin(name='spyder-terminal'):
    pass


def unininstall_plugin(name='spyder-terminal'):
    pass
