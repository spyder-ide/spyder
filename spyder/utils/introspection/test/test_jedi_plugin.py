# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License

"""Tests for sourcecode.py"""

import os
import sys

import pytest

from spyder.utils.introspection.manager import CodeInfo
from spyder.utils.introspection import jedi_plugin


p = jedi_plugin.JediPlugin()
p.load_plugin()


    source_code = "import numpy; numpy.ones("
    docs = p.get_info(CodeInfo('info', source_code, len(source_code)))

    assert docs['calltip'].startswith('ones(') and docs['name'] == 'ones'

    source_code = "import n"
    completions = p.get_completions(CodeInfo('completions', source_code,
        len(source_code)))
    assert ('numpy', 'module') in completions

    source_code = "import pandas as pd; pd.DataFrame"
    path, line_nr = p.get_definition(CodeInfo('definition', source_code,
        len(source_code)))
    assert 'frame.py' in path

    source_code = 'from .utils import CodeInfo'
    path, line_nr = p.get_definition(CodeInfo('definition', source_code,
        len(source_code), __file__))
    assert 'utils.py' in path and 'introspection' in path

    code = '''
def test(a, b):
    """Test docstring"""
    pass
test(1,'''
    path, line = p.get_definition(CodeInfo('definition', code, len(code),
        'dummy.txt', is_python_like=True))
    assert line == 2

    docs = p.get_info(CodeInfo('info', code, len(code), __file__))
    assert 'Test docstring' in docs['docstring']
    
    
    
    
    
def test_get_primary_at():
    code = 'import functools\nfunctools.partial'
    assert sourcecode.get_primary_at(code, len(code)) == 'functools.partial'


def test_get_identifiers():
    code = 'import functools\nfunctools.partial'
    assert set(sourcecode.get_identifiers(code)) == set(['import', 'functools',
                                                         'functools.partial'])


def test_split_source():
    code = 'import functools\nfunctools.partial'
    assert sourcecode.split_source(code) == ['import functools', 'functools.partial']
    code = code.replace('\n', '\r\n')
    assert sourcecode.split_source(code) == ['import functools', 'functools.partial']


def test_path_components():
    if sys.platform.startswith('linux'):
        path_components0 = ['','','documents','test','test.py']        
    else:
        path_components0 = ['c:','','documents','test','test.py']        
    path0 = os.path.join(*path_components0)
    assert sourcecode.path_components(path0) == path_components0


def test_differentiate_prefix():
    if sys.platform.startswith('linux'):
        path_components0 = ['','','documents','test','test.py']
        path_components1 = ['','','documents','projects','test','test.py']
    else:
        path_components0 = ['c:','','documents','test','test.py']
        path_components1 = ['c:','','documents','projects','test','test.py']
    diff_path0 = os.path.join(*['test'])
    diff_path1 = os.path.join(*['projects','test'])
    assert sourcecode.differentiate_prefix(
                        path_components0, path_components1) ==  diff_path0
    assert sourcecode.differentiate_prefix(
                        path_components1, path_components0) ==  diff_path1


if __name__ == '__main__':
    pytest.main()

