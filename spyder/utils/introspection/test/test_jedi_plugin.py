# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License

"""Tests for jedi_plugin.py"""

from textwrap import dedent

import pytest

from spyder.utils.introspection.manager import CodeInfo
from spyder.utils.introspection import jedi_plugin

p = jedi_plugin.JediPlugin()
p.load_plugin()
jedi_plugin.jedi.set_debug_function()


def test_get_info():
    source_code = "import numpy; numpy.ones("
    docs = p.get_info(CodeInfo('info', source_code, len(source_code)))
    assert docs['calltip'].startswith('ones(') and docs['name'] == 'ones'


def test_get_completions():
    source_code = "import n"
    completions = p.get_completions(CodeInfo('completions', source_code,
                                             len(source_code)))
    assert ('numpy', 'module') in completions


def test_get_definition():
    source_code = "import pandas as pd; pd.DataFrame"
    path, line_nr = p.get_definition(CodeInfo('definition', source_code,
                                              len(source_code)))
    assert 'frame.py' in path


def test_get_path():
    source_code = 'from spyder.utils.introspection.manager import CodeInfo'
    path, line_nr = p.get_definition(CodeInfo('definition', source_code,
                                              len(source_code), __file__))
    assert 'utils.py' in path and 'introspection' in path


def test_get_docstring():
    source_code = dedent('''
    def test(a, b):
        """Test docstring"""
        pass
    test(1,''')
    path, line = p.get_definition(CodeInfo('definition', source_code,
                                           len(source_code), 'dummy.txt',
                                           is_python_like=True))
    assert line == 2

    docs = p.get_info(CodeInfo('info', source_code, len(source_code),
                               __file__))
    assert 'Test docstring' in docs['docstring']


def test_numpy_returns():
    source_code = dedent('''
    import numpy as np
    x = np.array([1,2,3])
    x.a''')
    completions = p.get_completions(CodeInfo('completions', source_code,
                                             len(source_code)))
    assert ('argmax', 'function') in completions


def test_matplotlib_returns():
    source_code = dedent('''
    import matplotlib.pyplot as plt
    fig = plt.figure()
    fig.''')
    completions = p.get_completions(CodeInfo('completions', source_code,
                                             len(source_code)))
    assert ('add_axes', 'function') in completions


if __name__ == '__main__':
    pytest.main()
