# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License

"""Tests for sourcecode.py"""

import os
import sys

import pytest

from spyder.utils import sourcecode


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

