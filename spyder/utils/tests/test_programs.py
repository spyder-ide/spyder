# -*- coding: utf-8 -*-
#
# Copyright © 2009- The Spyder Development Team
# Licensed under the terms of the MIT License

"""Tests for programs.py"""

import time

import pytest

from spyder.utils.programs import run_python_script_in_terminal

def test_run_python_script_in_terminal(tmpdir):
    scriptpath = tmpdir.join('write-done.py')
    outfilepath = tmpdir.join('out.txt')
    script = ("with open('out.txt', 'w') as f:\n"
              "    f.write('done')\n")
    scriptpath.write(script)
    run_python_script_in_terminal(scriptpath.strpath, tmpdir.strpath, '',
                                  False, False, '')
    time.sleep(1) # wait for script to finish
    res = outfilepath.read()
    assert res == 'done'

def test_run_python_script_in_terminal_with_wdir_empty(tmpdir):
    scriptpath = tmpdir.join('write-done.py')
    outfilepath = tmpdir.join('out.txt')
    script = ("with open('{}', 'w') as f:\n"
              "    f.write('done')\n").format(outfilepath.strpath)
    scriptpath.write(script)
    run_python_script_in_terminal(scriptpath.strpath, '', '', False, False, '')
    time.sleep(1) # wait for script to finish
    res = outfilepath.read()
    assert res == 'done'

    
if __name__ == '__main__':
    pytest.main()
    
