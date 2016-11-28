# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License

"""Tests for programs.py"""

from os.path import dirname, abspath, splitext
from spyder.utils.introspection.utils import get_words_file

def test_get_words_html():
    """Test for get word from html file syntax"""

    path = dirname(dirname(abspath(__file__)))
    f_in = path+"/tests/data/example.html"
    words = get_words_file(f_in)
    expected_words = ['DOCTYPE', 'Hello', 'Jamie', 'World', 'body', 'charset', 'en', 'h',
                      'head', 'here', 'html', 'lang', 'meta', 'p', 'title', 'utf', 'was']
    assert sorted(words) == sorted(expected_words)

def test_get_words_R():
    """Test for get word from R file syntax"""

    path = dirname(dirname(abspath(__file__)))
    f_in = path+"/tests/data/example.R"
    words = get_words_file(f_in)
    expected_words = ['Hello', 'function', 'hello', 'name', 's', 'sprintf']
    assert sorted(words) == sorted(expected_words)

def test_get_words_content_R():
    """Test for get word from R file syntax"""

    path = dirname(dirname(abspath(__file__)))
    f_in = path+"/tests/data/example.R"

    print(f_in)
    ext = splitext(f_in)[1]
    with open(f_in, 'r') as infile:
        content = infile.read()
    print(content)
    words = get_words_file(content=content, extension=ext)
    expected_words = ['function', 'Hello', 'name', 'hello', 's', 'sprintf']
    assert sorted(words) == sorted(expected_words)


def test_get_words_css():
    """Test for get word from css file syntax"""

    path = dirname(dirname(abspath(__file__)))
    f_in = path+"/tests/data/example.css"
    words = get_words_file(f_in)
    expected_words = ['DeepSkyBlue', 'nombre-valido', 'text', 'css',
    		'h', 'color', 'Hello', 'world', 'type', 'style']
    assert sorted(words) == sorted(expected_words)


def test_get_words_python():
    """Test for get word from html file syntax"""

    path = dirname(dirname(abspath(__file__)))
    f_in = path + "/tests/data/example.py"
    words = get_words_file(f_in)
    expected_words = ['Apply', 'Browser', 'Count', 'Garcia', 'Juan', 'Make',
                      'Manuel', 'N', 'N_', 'Qt', 'QtWebKit', 'R', 'Set', 'Simple',
                      'This', 'Very', 'VerySimpleWebBrowser', 'Web', 'Z', 'Z_', '__file__',
                      'a', 'and', 'argwhere', 'array', 'as', 'author', 'birth', 'borders',
                      'com', 'def', 'for', 'gmail', 'home', 'i', 'implemented', 'import',
                      'in', 'int', 'is', 'iterate_', 'jmg', 'neighbours', 'new', 'np', 'null',
                      'numpy', 'over', 'print', 'range', 'ravel', 'return', 'rules', 'shape',
                      'stay', 'sure', 'survive', 'utn', 'values', 'zeros']
    assert sorted(words) == sorted(expected_words)


def test_get_words_java():
    """Test for get word from java file syntax"""

    path = dirname(dirname(abspath(__file__)))
    f_in = path+"/tests/data/example.java"
    words = get_words_file(f_in)
    expected_words = ['Compilation', 'Execution', 'Hello', 'HelloWorld', 'Prints', 'String',
                      'System', 'World', 'args', 'class', 'java', 'javac', 'main', 'out',
                      'println', 'public', 'static', 'terminal', 'the', 'to', 'void', 'window']
    assert sorted(words) == sorted(expected_words)


def test_get_words_cplusplus():
    """Test for get word from C++ file syntax"""

    path = dirname(dirname(abspath(__file__)))
    f_in = path+"/tests/data/example.cpp"
    words = get_words_file(f_in)
    expected_words = ['Consider', 'Create', 'Implement', 'Obj', 'ObjContainer',
                      'Postfix', 'Prefix', 'Return', 'SmartPointer', 'Static',
                      'Zero', 'a', 'above', 'access', 'actual', 'add', 'an', 'back',
                      'bool', 'call', 'class', 'const', 'container', 'cout', 'definitions',
                      'do', 'end', 'endl', 'f', 'false', 'for', 'friend', 'g', 'i', 'if',
                      'implement', 'include', 'index', 'indicates', 'int', 'iostream', 'iterator',
                      'j', 'list', 'main', 'member', 'method', 'namespace', 'o', 'obj', 'objc',
                      'oc', 'of', 'operator', 'overload', 'pointer', 'public', 'push', 'return',
                      's', 'size', 'smart', 'sp', 'standard', 'static', 'std', 'sz', 'the',
                      'to', 'true', 'using', 'value', 'vector', 'version', 'void', 'while']
    assert sorted(words) == sorted(expected_words)


def test_get_words_markdown():
    """Test for get word from markdown file syntax """
    path = dirname(dirname(abspath(__file__)))
    f_in = path+"/tests/data/example.md"
    words = get_words_file(f_in)
    expected_words = ['A', 'Blockquote', 'Bold', 'Heading', 'Horizontal', 'Image', 'Inline',
                      'Italic', 'Link', 'List', 'One', 'Rule', 'Three', 'Two', 'a', 'after',
                      'b', 'backticks', 'blank', 'block', 'code', 'com', 'http', 'indent',
                      'jpg', 'line', 'or', 'org', 'paragraph', 'png', 'print', 'spaces',
                      'url', 'with']
    assert sorted(words) == sorted(expected_words)


def test_get_words_c():
    """Test for get word from C file syntax"""

    path = dirname(dirname(abspath(__file__)))
    f_in = path+"/tests/data/example.c"
    words = get_words_file(f_in)
    expected_words = ['f', 'float', 'foo', 'h', 'i', 'include', 'int', 'main',
                      'n', 'printf', 'pvar', 'return', 'stdio', 'struct',
                      'var', 'x', 'y']
    assert sorted(words) == sorted(expected_words)
