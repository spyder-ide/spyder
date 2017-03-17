# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License

"""Tests for jedi_plugin.py"""

from textwrap import dedent

import pytest

from spyder.utils.introspection.manager import CodeInfo
from spyder.utils.introspection import jedi_plugin

try:
    import numpydoc
except ImportError:
    numpydoc = None

try:
    import numpy
except ImportError:
    numpy = None

try:
    import matplotlib
except ImportError:
    matplotlib = None

p = jedi_plugin.JediPlugin()
p.load_plugin()


def test_get_info():
    source_code = "import os; os.walk"
    docs = p.get_info(CodeInfo('info', source_code, len(source_code)))
    assert docs['calltip'].startswith('walk(') and docs['name'] == 'walk'


def test_get_completions():
    source_code = "import o"
    completions = p.get_completions(CodeInfo('completions', source_code,
                                             len(source_code)))
    assert ('os', 'module') in completions


def test_get_definition():
    source_code = "import os; os.walk"
    path, line_nr = p.get_definition(CodeInfo('definition', source_code,
                                              len(source_code)))
    assert 'os.py' in path


def test_get_path():
    source_code = 'from spyder.utils.introspection.manager import CodeInfo'
    path, line_nr = p.get_definition(CodeInfo('definition', source_code,
                                              len(source_code), __file__))
    assert 'utils' in path and 'introspection' in path


def test_get_docstring():
    source_code = dedent('''
    def test(a, b):
        """Test docstring"""
        pass
    test''')
    path, line = p.get_definition(CodeInfo('definition', source_code,
                                           len(source_code), 'dummy.txt',
                                           is_python_like=True))
    assert line == 2

    docs = p.get_info(CodeInfo('info', source_code, len(source_code),
                               __file__))
    assert 'Test docstring' in docs['docstring']


@pytest.mark.skipif(not(numpy and numpydoc),
                    reason="numpy and numpydoc required")
def test_numpy_returns():
    source_code = dedent('''
    import numpy as np
    x = np.array([1,2,3])
    x.a''')
    completions = p.get_completions(CodeInfo('completions', source_code,
                                             len(source_code)))
    assert ('argmax', 'function') in completions


@pytest.mark.skipif(not(matplotlib and numpydoc),
                    reason="matplotlib required")
def test_matplotlib_fig_returns():
    source_code = dedent('''
    import matplotlib.pyplot as plt
    fig = plt.figure()
    fig.''')
    completions = p.get_completions(CodeInfo('completions', source_code,
                                             len(source_code)))
    assert ('add_axes', 'function') in completions


if __name__ == '__main__':
    pytest.main()
