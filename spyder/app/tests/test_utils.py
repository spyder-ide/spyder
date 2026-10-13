# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for spyder/app/utils.py
"""

# Standard library imports
import os
import os.path as osp
import sys

# Third-party imports
import pytest

# Local imports
from spyder.app import utils
from spyder.app.utils import get_spyder_command


START_SCRIPT = osp.join(osp.dirname(osp.abspath(utils.__file__)), 'start.py')


def create_file(path):
    os.makedirs(osp.dirname(path), exist_ok=True)
    with open(path, 'w'):
        pass


@pytest.fixture
def environment(tmp_path, monkeypatch):
    """
    Simulate a Python environment, returning a function to set the OS name
    and the path to its interpreter.
    """
    scripts_dir = osp.join(str(tmp_path), 'env', 'Scripts')
    monkeypatch.setattr(
        utils.sysconfig, 'get_path', lambda name: scripts_dir
    )
    monkeypatch.setattr(utils, 'SHORTCUT_EXE', None)

    def set_environment(os_name, python):
        monkeypatch.setattr(os, 'name', os_name)
        monkeypatch.setattr(sys, 'executable', python)

    return scripts_dir, set_environment


@pytest.mark.parametrize(
    "os_name, launcher_name, expected",
    [
        ('posix', 'spyder', '{launcher} --reset-hdpi-settings'),
        ('nt', 'spyder.exe', '{launcher} --reset-hdpi-settings'),
    ]
)
def test_get_spyder_command_launcher(environment, os_name, launcher_name,
                                     expected):
    """Check that the Spyder launcher of the environment is used."""
    scripts_dir, set_environment = environment
    launcher = osp.join(scripts_dir, launcher_name)
    create_file(launcher)
    set_environment(os_name, osp.join(scripts_dir, 'python'))

    command = get_spyder_command(['--reset-hdpi-settings'])
    assert command == expected.format(launcher=launcher)


@pytest.mark.parametrize(
    "os_name, python, expected_python",
    [
        ('posix', 'python', 'python'),
        ('nt', 'python.exe', 'python.exe'),
        # pythonw.exe can't show output, so python.exe needs to be used
        ('nt', 'pythonw.exe', 'python.exe'),
    ]
)
def test_get_spyder_command_no_launcher(environment, tmp_path, os_name,
                                        python, expected_python):
    """Check that start.py is used if there is no Spyder launcher."""
    _, set_environment = environment
    set_environment(os_name, osp.join(str(tmp_path), python))

    command = get_spyder_command(['--reset-hdpi-settings'])
    assert command == (
        f'{osp.join(str(tmp_path), expected_python)} {START_SCRIPT} '
        f'--reset-hdpi-settings'
    )


def test_get_spyder_command_shortcut_exe(environment, monkeypatch):
    """
    Check that the interpreter of the macOS app is used if it's available,
    as done when restarting Spyder.
    """
    _, set_environment = environment
    set_environment('posix', '../../../bin/python')
    shortcut_exe = '/Applications/Spyder.app/Contents/MacOS/python'
    monkeypatch.setattr(utils, 'SHORTCUT_EXE', shortcut_exe)

    command = get_spyder_command([])
    assert command == f'{shortcut_exe} {START_SCRIPT}'


@pytest.mark.parametrize(
    "os_name, expected",
    [
        # Quoting for POSIX shells
        ('posix', "'{launcher}' --reset-hdpi-settings"),
        # Quoting for the Windows Command Prompt
        ('nt', '"{launcher}" --reset-hdpi-settings'),
    ]
)
def test_get_spyder_command_spaces(tmp_path, monkeypatch, os_name, expected):
    """Check that paths with spaces are quoted for the system's shell."""
    scripts_dir = osp.join(str(tmp_path), 'my env', 'Scripts')
    launcher = osp.join(
        scripts_dir, 'spyder.exe' if os_name == 'nt' else 'spyder'
    )
    create_file(launcher)
    monkeypatch.setattr(utils.sysconfig, 'get_path', lambda name: scripts_dir)
    monkeypatch.setattr(os, 'name', os_name)

    command = get_spyder_command(['--reset-hdpi-settings'])
    assert command == expected.format(launcher=launcher)


if __name__ == "__main__":
    pytest.main()
