# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License

"""Tests for programs.py"""

import os
import os.path as osp
import sys

from flaky import flaky
import pytest

from spyder.utils.programs import (run_python_script_in_terminal,
                                   is_python_interpreter,
                                   is_python_interpreter_valid_name,
                                   find_program, shell_split, check_version,
                                   is_module_installed, get_temp_dir)


if os.name == 'nt':
    python_dir = os.environ['PYTHON'] if os.environ.get('CI', None) else ''
    VALID_INTERPRETER = os.path.join(python_dir, 'python.exe')
    VALID_W_INTERPRETER = os.path.join(python_dir, 'pythonw.exe')
    INVALID_INTERPRETER = os.path.join(python_dir, 'Scripts', 'ipython.exe')
else:
    if sys.platform.startswith('linux'):
        home_dir = os.environ['HOME']
    else:
        # Parent Miniconda dir in macOS Azure VMs
        home_dir = os.path.join('/usr', 'local')
    VALID_INTERPRETER = os.path.join(home_dir, 'miniconda', 'bin', 'python')
    VALID_W_INTERPRETER = os.path.join(home_dir, 'miniconda', 'bin', 'pythonw')
    INVALID_INTERPRETER = os.path.join(home_dir, 'miniconda', 'bin', 'ipython')


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def scriptpath(tmpdir):
    """Save a basic Python script in a file."""
    script = ("with open('out.txt', 'w') as f:\n"
              "    f.write('done')\n")
    scriptpath = tmpdir.join('write-done.py')
    scriptpath.write(script)
    return scriptpath


# =============================================================================
# ---- Tests
# =============================================================================
@pytest.mark.skipif((sys.platform.startswith('linux') or
                     os.environ.get('CI', None) is None),
                    reason='It only runs in CI services and '
                           'Linux does not have pythonw executables.')
def test_is_valid_w_interpreter():
    assert is_python_interpreter(VALID_W_INTERPRETER)


@flaky(max_runs=3)
@pytest.mark.skipif(
    os.environ.get('CI', None) is None or sys.platform == 'darwin',
    reason='fails in macOS and sometimes locally')
def test_run_python_script_in_terminal(scriptpath, qtbot):
    """
    Test running a Python script in an external terminal when specifying
    explicitely the working directory.
    """
    # Run the script.
    outfilepath = osp.join(scriptpath.dirname, 'out.txt')
    run_python_script_in_terminal(
        scriptpath.strpath, scriptpath.dirname, '', False, False, '')
    qtbot.waitUntil(lambda: osp.exists(outfilepath), timeout=1000)

    # Assert the result.
    with open(outfilepath, 'r') as txtfile:
        res = txtfile.read()
    assert res == 'done'


@flaky(max_runs=3)
@pytest.mark.skipif(
    os.environ.get('CI', None) is None or sys.platform == 'darwin',
    reason='fails in macOS and sometimes locally')
def test_run_python_script_in_terminal_with_wdir_empty(scriptpath, qtbot):
    """
    Test running a Python script in an external terminal without specifying
    the working directory.
    """
    # Run the script.
    outfilepath = osp.join(os.getcwd(), 'out.txt')
    run_python_script_in_terminal(scriptpath.strpath, '', '', False, False, '')
    qtbot.waitUntil(lambda: osp.exists(outfilepath), timeout=1000)

    # Assert the result.
    with open(outfilepath, 'r') as txtfile:
        res = txtfile.read()
    assert res == 'done'


@pytest.mark.skipif(os.environ.get('CI', None) is None,
                    reason='It only runs in CI services.')
def test_is_valid_interpreter():
    assert is_python_interpreter(VALID_INTERPRETER)


@pytest.mark.skipif(os.environ.get('CI', None) is None,
                    reason='It only runs in CI services.')
def test_is_invalid_interpreter():
    assert not is_python_interpreter(INVALID_INTERPRETER)


def test_is_valid_interpreter_name():
    names = ['python', 'pythonw', 'python2.7', 'python3.5', 'python.exe', 'pythonw.exe']
    assert all([is_python_interpreter_valid_name(n) for n in names])

def test_find_program():
    """Test if can find the program."""
    assert find_program('git')

def test_shell_split():
    """Test if the text can be split using shell-like sintax."""
    assert shell_split('-q -o -a') == ['-q', '-o', '-a']
    assert shell_split('-q "d:\\Python de xxxx\\t.txt" -o -a') == \
           ['-q', 'd:\\Python de xxxx\\t.txt', '-o', '-a']

def test_check_version():
    """Test the compare function for versions."""
    assert check_version('0.9.4-1', '0.9.4', '>=')
    assert check_version('3.0.0rc1', '3.0.0', '<')
    assert check_version('1.0', '1.0b2', '>')

def test_is_module_installed():
    """Test if a module with the proper version is installed"""
    assert is_module_installed('qtconsole', '>=4.0')
    assert not is_module_installed('IPython', '>=1.0;<3.0')
    assert is_module_installed('jedi', '>=0.7.0')


@pytest.mark.skipif(os.name == 'nt' and os.environ.get('AZURE') is not None,
                    reason="Fails on Windows/Azure")
def test_is_module_installed_with_custom_interpreter():
    """Test if a module with the proper version is installed"""
    current = sys.executable
    assert is_module_installed('qtconsole', '>=4.0', interpreter=current)
    assert not is_module_installed('IPython', '>=1.0;<3.0', interpreter=current)
    assert is_module_installed('jedi', '>=0.7.0', interpreter=current)


def test_get_temp_dir_ensure_dir_exists():
    """Test that the call to get_temp_dir creates the dir when it doesn't exists
    """
    temp_dir = get_temp_dir(suffix='test')
    assert os.path.exists(temp_dir)

    os.rmdir(temp_dir)

    another_call = get_temp_dir(suffix='test')

    assert os.path.exists(another_call)
    assert another_call == temp_dir


if __name__ == '__main__':
    pytest.main()
