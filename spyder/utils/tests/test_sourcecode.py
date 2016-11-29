# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License

"""Tests for sourcecode.py"""

import os

import pytest

from spyder.utils import sourcecode


def test_get_primary_at(tmpdir, qtbot):
    code = 'import functools\nfunctools.partial'
    assert sourcecode.get_primary_at(code, len(code)) == 'functools.partial'


def test_get_identifiers(tmpdir, qtbot):
    code = 'import functools\nfunctools.partial'
    assert set(sourcecode.get_identifiers(code)) == set(['import', 'functools',
                                              'functools.partial'])


def test_split_source(tmpdir, qtbot):
    code = 'import functools\nfunctools.partial'
    assert sourcecode.split_source(code) == ['import functools', 'functools.partial']
    code = code.replace('\n', '\r\n')
    assert sourcecode.split_source(code) == ['import functools', 'functools.partial']


def test_path_components(tmpdir, qtbot):
    path_components0 = ['c:','','documents','test','test.py']
    path_components1 = ['c:','','documents','projects','test','test.py']
    path0 = os.path.join(*path_components0)
    path1 = os.path.join(*path_components1)
    assert sourcecode.path_components(path0) == path_components0
    assert sourcecode.path_components(path1) == path_components1
    

def test_differentiate_prefix(tmpdir, qtbot):
    path_components0 = ['documents','test','test.py']
    path_components1 = ['documents','projects','test','test.py']
    differ_path0 = os.path.join(*['documents','test'])
    differ_path1 = os.path.join(*['documents', 'projects', 'test'])
    assert sourcecode.differentiate_prefix(
                        path_components0, path_components1) ==  differ_path0
    assert sourcecode.differentiate_prefix(
                        path_components1, path_components0) ==  differ_path1


if __name__ == '__main__':
    pytest.main()

