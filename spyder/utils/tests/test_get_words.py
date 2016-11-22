# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License

"""Tests for programs.py"""

from os.path import dirname, abspath, basename
from spyder.utils.introspection.utils import get_words_file

def test_get_words_html():
    """Test for get word from html file syntax"""

    path = dirname(dirname(abspath(__file__)))
    f_in = path+"/tests/data/example.html"
    words = get_words_file(f_in)
    print(words)
    real = ['meta', 'p', 'body', 'en', 'was', 'h', 'Hello',
            'here', 'title', 'head', 'charset', 'Jamie',
            'World', 'lang', 'html', 'DOCTYPE', 'utf']
    assert sorted(words) == sorted(real)

def test_get_words_python():
    """Test for get word from html file syntax"""

    path = dirname(dirname(abspath(__file__)))
    f_in = path+"/tests/data/example.py"
    words = get_words_file(f_in)
    print(words)
    real = ['a', 'sure', 'np', 'Z_', 'Simple', 'R', 'utn', 'values',
            'is', 'N_', 'zeros', 'i', 'rules', 'jmg', 'Manuel', 'new',
            'numpy', 'neighbours', 'shape', 'survive', 'int', 'gmail',
            'home', 'birth', 'range', 'Z', '-', 'author', 'implemented',
            'array', 'null', 'return', 'Qt', 'import', 'and', 'stay',
            'VerySimpleWebBrowser', 'N', 'com', 'Juan', 'borders', 'Make',
            'iterate_', 'as', 'ravel', 'in', 'Browser', 'def', 'over', 'Set',
            'print', 'This', 'argwhere', 'for', 'Very', 'Web', 'Garcia',
            'Apply', 'QtWebKit', 'Count']
    assert sorted(words) == sorted(real)