# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License

"""Tests for programs.py."""

from os.path import dirname, abspath, splitext, join
from spyder.utils.introspection.utils import get_words

HERE = dirname(abspath(__file__))
TEST_DATA_PATH = join(HERE, 'data')


# --- Fixtures
# -----------------------------------------------------------------------------
def get_words_by_content(filename):
    """Test get_words from content in filename."""
    f_in = join(TEST_DATA_PATH, filename)
    ext = splitext(f_in)[1]
    with open(f_in, 'r') as infile:
        content = infile.read()
    return  get_words(content=content, extension=ext)

def get_words_by_filename(filename):
    """Test get_words from  filepath."""
    filepath = join(TEST_DATA_PATH, filename)
    return get_words(filepath)


# --- Tests
# -----------------------------------------------------------------------------

def test_get_words_html():
    """Test for get word from html file syntax."""
    expected_words = ['DOCTYPE', 'Hello', 'Jamie', 'World', 'body', 'charset', 'en', 'h',
                      'head', 'here', 'html', 'lang', 'meta', 'p', 'title', 'utf', 'was']
    assert sorted(expected_words) == sorted(get_words_by_filename("example.html"))
    assert sorted(expected_words) == sorted(get_words_by_content("example.html"))

def test_get_words_r():
    """Test for get word from R file syntax."""
    expected_words = ['Hello', 'function', 'hello', 'name', 's', 'sprintf']
    assert sorted(expected_words) == sorted(get_words_by_filename("example.R"))
    assert sorted(expected_words) == sorted(get_words_by_content("example.R"))

def test_get_words_css():
    """Test for get word from css file syntax."""
    expected_words = ['DeepSkyBlue', 'nombre-valido', 'text', 'css',
    		'h', 'color', 'Hello', 'world', 'type', 'style']
    assert sorted(expected_words) == sorted(get_words_by_filename("example.css"))
    assert sorted(expected_words) == sorted(get_words_by_content("example.css"))

def test_get_words_python():
    """Test for get word from html file syntax."""
    expected_words = ['Apply', 'Browser', 'Count', 'Garcia', 'Juan', 'Make',
                      'Manuel', 'N', 'N_', 'Qt', 'QtWebKit', 'R', 'Set', 'Simple',
                      'This', 'Very', 'VerySimpleWebBrowser', 'Web', 'Z', 'Z_', '__file__',
                      'a', 'and', 'argwhere', 'array', 'as', 'author', 'birth', 'borders',
                      'com', 'def', 'for', 'gmail', 'home', 'i', 'implemented', 'import',
                      'in', 'int', 'is', 'iterate_', 'jmg', 'neighbours', 'new', 'np', 'null',
                      'numpy', 'over', 'print', 'range', 'ravel', 'return', 'rules', 'shape',
                      'stay', 'sure', 'survive', 'utn', 'values', 'zeros']
    assert sorted(expected_words) == sorted(get_words_by_filename("example.py"))
    assert sorted(expected_words) == sorted(get_words_by_content("example.py"))

def test_get_words_java():
    """Test for get word from java file syntax."""
    expected_words = ['Compilation', 'Execution', 'Hello', 'HelloWorld', 'Prints', 'String',
                      'System', 'World', 'args', 'class', 'java', 'javac', 'main', 'out',
                      'println', 'public', 'static', 'terminal', 'the', 'to', 'void', 'window']
    assert sorted(expected_words) == sorted(get_words_by_filename("example.java"))
    assert sorted(expected_words) == sorted(get_words_by_content("example.java"))

def test_get_words_cplusplus():
    """Test for get word from C++ file syntax."""
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
    assert sorted(expected_words) == sorted(get_words_by_filename("example.cpp"))
    assert sorted(expected_words) == sorted(get_words_by_content("example.cpp"))

def test_get_words_markdown():
    """Test for get word from markdown file syntax."""
    expected_words = ['A', 'Blockquote', 'Bold', 'Heading', 'Horizontal', 'Image', 'Inline',
                      'Italic', 'Link', 'List', 'One', 'Rule', 'Three', 'Two', 'a', 'after',
                      'b', 'backticks', 'blank', 'block', 'code', 'com', 'http', 'indent',
                      'jpg', 'line', 'or', 'org', 'paragraph', 'png', 'print', 'spaces',
                      'url', 'with']
    assert sorted(expected_words) == sorted(get_words_by_filename("example.md"))
    assert sorted(expected_words) == sorted(get_words_by_content("example.md"))

def test_get_words_c():
    """Test for get word from C file syntax."""
    expected_words = ['f', 'float', 'foo', 'h', 'i', 'include', 'int', 'main',
                      'n', 'printf', 'pvar', 'return', 'stdio', 'struct',
                      'var', 'x', 'y']
    assert sorted(expected_words) == sorted(get_words_by_filename("example.c"))
    assert sorted(expected_words) == sorted(get_words_by_content("example.c"))
