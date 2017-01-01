# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License

"""Tests for programs.py"""

import os
import pytest

from spyder.utils.programs import (run_python_script_in_terminal,
                                   is_python_interpreter)

if os.name == 'nt':
    VALID_INTERPRETER = '%PYTHON%\bin\python.exe'
    INVALID_INTERPRETER = '%PYTHON%\Scripts\ipython.exe'
else:
    VALID_INTERPRETER = '$HOME/miniconda/bin/python'
    INVALID_INTERPRETER = '$HOME/miniconda/bin/ipython'

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

@pytest.mark.skipif(os.environ.get('CI', None) == True,
                    reason='It only runs in CI services.')
def test_is_valid_interpreter():
    assert is_python_interpreter(VALID_INTERPRETER)

@pytest.mark.skipif(os.environ.get('CI', None) == True,
                    reason='It only runs in CI services.')
def test_is_invalid_interpreter():
    assert not is_python_interpreter(INVALID_INTERPRETER)


if __name__ == '__main__':
    pytest.main()
    
