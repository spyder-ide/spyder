# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License

"""Tests for programs.py"""

import os

import pytest

from spyder.utils.programs import (run_python_script_in_terminal,
                                   is_python_interpreter)

@pytest.mark.skipif(os.name == 'nt', reason='gets stuck on Windows') # FIXME
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

@pytest.mark.skipif(os.name == 'nt', reason='gets stuck on Windows') # FIXME
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

@pytest.mark.skipif(os.environ.get('TEST_CI_WIDGETS', None) == True,
                    reason='To only run the test in spyders CI services.')
def test_is_python_interpreter_linux_true():
    filename = "$HOME/miniconda/bin/python"
    valid = is_python_interpreter(filename)

    assert valid == True

@pytest.mark.skipif(os.environ.get('TEST_CI_WIDGETS', None) == True,
                    reason='To only run the test in spyders CI services.')
def test_is_python_interpreter_linux_false():
    filename = "$HOME/miniconda/bin/ipython"
    valid = is_python_interpreter(filename)

    assert valid == False

@pytest.mark.skipif(os.environ.get('TEST_CI_WIDGETS', None) == True,
                    reason='To only run the test in spyders CI services.')
def test_is_python_interpreter_windows_true():
    filename = "%PYTHON%\bin\python.exe"
    valid = is_python_interpreter(filename)

    assert valid == True

@pytest.mark.skipif(os.environ.get('TEST_CI_WIDGETS', None) == True,
                    reason='To only run the test in spyders CI services.')
def test_is_python_interpreter_windows_false():
    filename = "%PYTHON%\Scripts\ipython.exe"
    valid = is_python_interpreter(filename)

    assert valid == False


if __name__ == '__main__':
    pytest.main()
    
