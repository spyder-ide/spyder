# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License

"""Tests for programs.py"""

import os
import sys

from flaky import flaky
import pytest

from spyder.utils.programs import (run_python_script_in_terminal,
                                   is_python_interpreter,
                                   is_python_interpreter_valid_name,
                                   find_program, shell_split, check_version,
                                   is_module_installed, get_temp_dir,
                                   is_stable_version)


if os.name == 'nt':
    python_dir = os.environ['PYTHON'] if os.environ.get('CI', None) else ''
    VALID_INTERPRETER = os.path.join(python_dir, 'python.exe')
    VALID_W_INTERPRETER = os.path.join(python_dir, 'pythonw.exe')
    INVALID_INTERPRETER = os.path.join(python_dir, 'Scripts', 'ipython.exe')
else:
    home_dir = os.environ['HOME']
    VALID_INTERPRETER = os.path.join(home_dir, 'miniconda', 'bin', 'python')
    VALID_W_INTERPRETER = os.path.join(home_dir, 'miniconda', 'bin', 'pythonw')
    INVALID_INTERPRETER = os.path.join(home_dir, 'miniconda', 'bin', 'ipython')


@pytest.mark.skipif((sys.platform.startswith('linux') or
                     os.environ.get('CI', None) is None),
                    reason='It only runs in CI services and '
                           'Linux does not have pythonw executables.')
def test_is_valid_w_interpreter():
    assert is_python_interpreter(VALID_W_INTERPRETER)


@flaky(max_runs=3)
@pytest.mark.skipif((os.name == 'nt' or os.environ.get('CI', None) is None or
                     sys.platform == 'darwin'),
                    reason='gets stuck on Windows and fails in macOS and sometimes locally') # FIXME
def test_run_python_script_in_terminal(tmpdir, qtbot):
    scriptpath = tmpdir.join('write-done.py')
    outfilepath = tmpdir.join('out.txt')
    script = ("with open('out.txt', 'w') as f:\n"
              "    f.write('done')\n")
    scriptpath.write(script)
    run_python_script_in_terminal(scriptpath.strpath, tmpdir.strpath, '',
                                  False, False, '')
    qtbot.wait(1000) # wait for script to finish
    res = outfilepath.read()
    assert res == 'done'


@flaky(max_runs=3)
@pytest.mark.skipif((os.name == 'nt' or os.environ.get('CI', None) is None or
                     sys.platform == 'darwin'),
                    reason='gets stuck on Windows and fails in macOS and sometimes locally') # FIXME
def test_run_python_script_in_terminal_with_wdir_empty(tmpdir, qtbot):
    scriptpath = tmpdir.join('write-done.py')
    outfilepath = tmpdir.join('out.txt')
    script = ("with open('{}', 'w') as f:\n"
              "    f.write('done')\n").format(outfilepath.strpath)
    scriptpath.write(script)
    run_python_script_in_terminal(scriptpath.strpath, '', '', False, False, '')
    qtbot.wait(1000) # wait for script to finish
    res = outfilepath.read()
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


def test_is_stable_version():
    """Tests for is_stable_version."""
    assert is_stable_version('3.3.0')
    assert not is_stable_version('4.0.0b1')


if __name__ == '__main__':
    pytest.main()
