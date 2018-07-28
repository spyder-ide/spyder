# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for fallback_plugin.py
"""

# Standard library imports
import os
import os.path as osp

# Test library imports
import pytest

# Local imports
from spyder.utils.introspection.fallback_plugin import (FallbackPlugin,
                                                        python_like_exts,
                                                        all_editable_exts,
                                                        get_parent_until,
                                                        python_like_mod_finder
                                                        )
from spyder.utils.introspection.manager import CodeInfo

FALLBACK_PLUGIN_FILE = osp.join(os.path.dirname(__file__), '..',
                                'fallback_plugin.py')

def test_fallback_plugin():
    """Test the fallback plugin."""
    p = FallbackPlugin()
    with open(FALLBACK_PLUGIN_FILE, 'rb') as fid:
        code = fid.read().decode('utf-8')
    code += '\nlog_dt'

    path, line = p.get_definition(CodeInfo('definition', code, len(code),
        __file__, is_python_like=True))
    assert path.endswith('fallback_plugin.py')

    code += '\np.get_completions'
    path, line = p.get_definition(CodeInfo('definition', code, len(code),
        'dummy.py', is_python_like=True))
    assert path == 'dummy.py'
    assert 'def get_completions(' in code.splitlines()[line - 1]

    code += '\npython_like_mod_finder'
    path, line = p.get_definition(CodeInfo('definition', code, len(code),
        'dummy.py', is_python_like=True))
    assert path == 'dummy.py'
    # FIXME: we need to prioritize def over =
    assert 'def python_like_mod_finder' in code.splitlines()[line - 1]

    code += 'python_like_mod_finder'
    resp = p.get_definition(CodeInfo('definition', code, len(code),
        'dummy.py'))
    assert resp is None


def test_extensions():
    """Test the extentions related methods from the fallback plugin."""
    ext = python_like_exts()
    assert '.py' in ext and '.pyx' in ext

    ext = all_editable_exts()
    assert '.cpp' in ext and '.html' in ext

    path = get_parent_until(os.path.abspath(FALLBACK_PLUGIN_FILE))
    assert path == 'spyder.utils.introspection.fallback_plugin'

    line = 'from spyder.widgets.sourcecode.codeeditor import CodeEditor'
    path = python_like_mod_finder(line)
    assert path.endswith('codeeditor.py')
    path = python_like_mod_finder(line, stop_token='sourcecode')
    assert path.endswith('__init__.py') and 'sourcecode' in path

    path = osp.expanduser(r'~/.spyder2/temp.py')
    if os.path.exists(path):
        path = get_parent_until(path)
        assert path == '.spyder2.temp', path


def test_get_completions():
    """Test the get_completions method from the Fallback plugin."""
    p = FallbackPlugin()
    code = 'self.proxy.widget; self.p'
    comp = p.get_completions(CodeInfo('completions', code, len(code), 'dummy.py'))
    assert ('proxy', '') in comp, comp

    code = 'self.sigMessageReady.emit; self.s'
    comp = p.get_completions(CodeInfo('completions', code, len(code), 'dummy.py'))
    assert ('sigMessageReady', '') in comp

    code = 'var = 1; f\'{v'
    comp = p.get_completions(CodeInfo('completions', code, len(code),
                                      'dummy.py'))
    assert ('var', '') in comp

    code = 'var = 1; F\'{v'
    comp = p.get_completions(CodeInfo('completions', code, len(code),
                                      'dummy.py'))
    assert ('var', '') in comp

    code = 'var = 1; f"{v'
    comp = p.get_completions(CodeInfo('completions', code, len(code),
                                      'dummy.py'))
    assert ('var', '') in comp

    code = 'var = 1; F"{v'
    comp = p.get_completions(CodeInfo('completions', code, len(code),
                                      'dummy.py'))
    assert ('var', '') in comp

    code = 'bob = 1; bo'
    comp = p.get_completions(CodeInfo('completions', code, len(code), 'dummy.m'))
    assert ('bob', '') in comp

    code = 'functi'    
    comp = p.get_completions(CodeInfo('completions', code, len(code), 'dummy.sh'))
    assert ('function', '') in comp, comp


def test_get_definition_method():
    """Test the get_definition method for methods."""
    p = FallbackPlugin()
    code = '''
def test(a, b):
    pass
test(1,'''
    path, line = p.get_definition(CodeInfo('definition', code, len(code),
        'dummy.py', is_python_like=True))
    assert line == 2

    code = 'import re\n\nre'
    path, line = p.get_definition(CodeInfo('definition', code, len(code),
        'dummy.py', is_python_like=True))
    assert path == 'dummy.py' and line == 1


def test_get_definition_class():
    """Test the get_definition method for classes."""
    p = FallbackPlugin()
    code = """
    class Test(object):
        def __init__(self):
            self.foo = bar

    t = Test()
    t.foo"""
    path, line = p.get_definition(CodeInfo('definition', code, len(code),
        'dummy.py', is_python_like=True))
    assert line == 4


def test_default_info():
    """Test default info response."""
    p = FallbackPlugin()
    source_code = 'foo'
    docs = p.get_info(CodeInfo('info', source_code, len(source_code),
                               __file__))
    assert sorted(list(docs.keys())) == sorted(['name', 'argspec', 'note',
                                                'docstring', 'calltip'])
    assert not docs['name']
    assert not docs['argspec']
    assert not docs['note']
    assert not docs['docstring']
    assert not docs['calltip']


if __name__ == "__main__":
    pytest.main()
