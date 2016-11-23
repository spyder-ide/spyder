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


def test_get_words_css():
    """Test for get word from css file syntax"""

    path = dirname(dirname(abspath(__file__)))
    f_in = path+"/tests/data/example.css"
    words = get_words_file(f_in)
    real = ['DeepSkyBlue', 'nombre-valido', 'text', 'css',
    		'h', 'color', 'Hello', 'world', 'type', 'style']
    assert sorted(words) == sorted(real)


def test_get_words_c():
    """Test for get word from C file syntax"""

    path = dirname(dirname(abspath(__file__)))
    f_in = path+"/tests/data/example.c"
    words = get_words_file(f_in)
    real = ['struct', 'float', 'return', 'foo', 'x', 'pvar',
    		'include', 'stdio', 'h', 'int', 'f', 'var',
    		'main', 'n', 'i', 'printf', 'y']
    assert sorted(words) == sorted(real)

def test_get_words_cplusplus():
    """Test for get word from C++ file syntax"""

    path = dirname(dirname(abspath(__file__)))
    f_in = path+"/tests/data/example.cpp"
    words = get_words_file(f_in)
    real = ['class', 'a', 'friend', 'public', 'include', 'end',
    		'implement', 'while', 'Obj', 'pointer', 'endl',
    		'Implement', 'oc', 'main', 'i', 'of', 'indicates',
    		'overload', 'std', 'do', 'container', 'cout', 'Return',
    		'int', 'value', 'push', 'above', 'g', 'bool', 'iterator',
    		'obj', 'operator', 'SmartPointer', 'false', 'iostream',
    		'Consider', 'vector', 'an', 'the', 'back', 'access', 'return',
    		'Postfix', 'sp', 'add', 'Create', 'sz', 'static', 'to', 'f',
    		'namespace', 'method', 'size', 'j', 'o', 'Static', 'const',
    		'call', 'void', 'ObjContainer', 'definitions', 'using', 'for',
    		'standard', 'actual', 'smart', 'index', 'list', 'member',
    		'Prefix', 'version', 'objc', 'if', 'Zero', 's', 'true']
    assert sorted(words) == sorted(real)


def test_get_words_R():
    """Test for get word from R file syntax"""

    path = dirname(dirname(abspath(__file__)))
    f_in = path+"/tests/data/example.R"
    words = get_words_file(f_in)
    real = ['function', 'Hello', 'name', 'hello', 's', 'sprintf']
    assert sorted(words) == sorted(real)


def test_get_words_java():
    """Test for get word from java file syntax"""

    path = dirname(dirname(abspath(__file__)))
    f_in = path+"/tests/data/example.java"
    words = get_words_file(f_in)
    real = ['class', 'public', 'String', 'println', 'window',
    		'main', 'Execution', 'HelloWorld', 'terminal',
    		'System', 'out', 'java', 'World', 'Prints', 'the',
    		'static', 'to', 'Compilation', 'javac', 'void',
    		'Hello', 'args']
    assert sorted(words) == sorted(real)

def test_get_words_markdown():
    """Test for get word from markdown file syntax """
    path = dirname(dirname(abspath(__file__)))
    f_in = path+"/tests/data/example.java"
    words = get_words_file(f_in)
    real = ['a', 'b', 'Italic', 'blank', 'Rule', 'Image',
    		'Blockquote', 'or', 'Horizontal', 'List', 'after',
    		'Bold', 'Inline', 'Heading', 'http', 'with', 'org',
    		'png', 'Link', 'A', 'url', 'block', 'com', 'backticks',
    		'code', 'paragraph', 'print', 'jpg', 'indent', 'One',
    		'Two', 'line', 'spaces', 'Three']
    assert sorted(words) == sorted(real)