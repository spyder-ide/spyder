# Copyright 2017-2020 Palantir Technologies, Inc.
# Copyright 2021- Python Language Server Contributors.

import math
import os
import sys

from pathlib import Path
from typing import NamedTuple, Dict

import pytest

from pylsp import uris, lsp
from pylsp.workspace import Document
from pylsp.plugins.jedi_completion import pylsp_completions as pylsp_jedi_completions
from pylsp.plugins.jedi_completion import pylsp_completion_item_resolve as pylsp_jedi_completion_item_resolve
from pylsp.plugins.rope_completion import pylsp_completions as pylsp_rope_completions
from pylsp._utils import JEDI_VERSION


PY2 = sys.version[0] == '2'
LINUX = sys.platform.startswith('linux')
CI = os.environ.get('CI')
LOCATION = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__))
)
DOC_URI = uris.from_fs_path(__file__)
DOC = """import os
print os.path.isabs("/tmp")

def hello():
    pass

def _a_hello():
    pass

class Hello():

    @property
    def world(self):
        return None

    def everyone(self, a, b, c=None, d=2):
        pass

print Hello().world

print Hello().every

def documented_hello():
    \"\"\"Sends a polite greeting\"\"\"
    pass
"""


def test_rope_import_completion(config, workspace):
    com_position = {'line': 0, 'character': 7}
    doc = Document(DOC_URI, workspace, DOC)
    items = pylsp_rope_completions(config, workspace, doc, com_position)
    assert items is None


class TypeCase(NamedTuple):
    document: str
    position: dict
    label: str
    expected: lsp.CompletionItemKind


TYPE_CASES: Dict[str, TypeCase] = {
    'variable': TypeCase(
        document='test = 1\ntes',
        position={'line': 1, 'character': 3},
        label='test',
        expected=lsp.CompletionItemKind.Variable
    ),
    'function': TypeCase(
        document='def test():\n    pass\ntes',
        position={'line': 2, 'character': 3},
        label='test()',
        expected=lsp.CompletionItemKind.Function
    ),
    'keyword': TypeCase(
        document='fro',
        position={'line': 0, 'character': 3},
        label='from',
        expected=lsp.CompletionItemKind.Keyword
    ),
    'file': TypeCase(
        document='"' + __file__[:-2].replace('"', '\\"') + '"',
        position={'line': 0, 'character': len(__file__) - 2},
        label=Path(__file__).name + '"',
        expected=lsp.CompletionItemKind.File
    ),
    'module': TypeCase(
        document='import statis',
        position={'line': 0, 'character': 13},
        label='statistics',
        expected=lsp.CompletionItemKind.Module
    ),
    'class': TypeCase(
        document='KeyErr',
        position={'line': 0, 'character': 6},
        label='KeyError',
        expected=lsp.CompletionItemKind.Class
    ),
    'property': TypeCase(
        document=(
            'class A:\n'
            '    @property\n'
            '    def test(self):\n'
            '        pass\n'
            'A().tes'
        ),
        position={'line': 4, 'character': 5},
        label='test',
        expected=lsp.CompletionItemKind.Property
    )
}


@pytest.mark.parametrize('case', list(TYPE_CASES.values()), ids=list(TYPE_CASES.keys()))
def test_jedi_completion_type(case, config, workspace):
    # property support was introduced in 0.18
    if case.expected == lsp.CompletionItemKind.Property and JEDI_VERSION.startswith('0.17'):
        return

    doc = Document(DOC_URI, workspace, case.document)
    items = pylsp_jedi_completions(config, doc, case.position)
    items = {i['label']: i for i in items}
    assert items[case.label]['kind'] == case.expected


def test_jedi_completion(config, workspace):
    # Over 'i' in os.path.isabs(...)
    com_position = {'line': 1, 'character': 15}
    doc = Document(DOC_URI, workspace, DOC)
    items = pylsp_jedi_completions(config, doc, com_position)

    assert items
    labels = [i['label'] for i in items]
    assert 'isfile(path)' in labels

    # Test we don't throw with big character
    pylsp_jedi_completions(config, doc, {'line': 1, 'character': 1000})


def test_jedi_completion_item_resolve(config, workspace):
    # Over the blank line
    com_position = {'line': 8, 'character': 0}
    doc = Document(DOC_URI, workspace, DOC)
    config.update({'plugins': {'jedi_completion': {'resolve_at_most': math.inf}}})
    completions = pylsp_jedi_completions(config, doc, com_position)

    items = {c['label']: c for c in completions}

    documented_hello_item = items['documented_hello()']

    assert 'documentation' not in documented_hello_item
    assert 'detail' not in documented_hello_item

    resolved_documented_hello = pylsp_jedi_completion_item_resolve(
        completion_item=documented_hello_item,
        document=doc
    )
    assert 'Sends a polite greeting' in resolved_documented_hello['documentation']


def test_jedi_completion_with_fuzzy_enabled(config, workspace):
    # Over 'i' in os.path.isabs(...)
    config.update({'plugins': {'jedi_completion': {'fuzzy': True}}})
    com_position = {'line': 1, 'character': 15}
    doc = Document(DOC_URI, workspace, DOC)

    items = pylsp_jedi_completions(config, doc, com_position)

    assert items

    expected = 'commonprefix(m)'
    if JEDI_VERSION == '0.18.0':
        expected = 'commonprefix(list)'
    assert items[0]['label'] == expected

    # Test we don't throw with big character
    pylsp_jedi_completions(config, doc, {'line': 1, 'character': 1000})


def test_jedi_completion_resolve_at_most(config, workspace):
    # Over 'i' in os.path.isabs(...)
    com_position = {'line': 1, 'character': 15}
    doc = Document(DOC_URI, workspace, DOC)

    # Do not resolve any labels
    config.update({'plugins': {'jedi_completion': {'resolve_at_most': 0}}})
    items = pylsp_jedi_completions(config, doc, com_position)
    labels = {i['label'] for i in items}
    assert 'isabs' in labels

    # Resolve all items
    config.update({'plugins': {'jedi_completion': {'resolve_at_most': math.inf}}})
    items = pylsp_jedi_completions(config, doc, com_position)
    labels = {i['label'] for i in items}
    assert 'isfile(path)' in labels


def test_rope_completion(config, workspace):
    # Over 'i' in os.path.isabs(...)
    com_position = {'line': 1, 'character': 15}
    workspace.put_document(DOC_URI, source=DOC)
    doc = workspace.get_document(DOC_URI)
    items = pylsp_rope_completions(config, workspace, doc, com_position)

    assert items
    assert items[0]['label'] == 'isabs'


def test_jedi_completion_ordering(config, workspace):
    # Over the blank line
    com_position = {'line': 8, 'character': 0}
    doc = Document(DOC_URI, workspace, DOC)
    config.update({'plugins': {'jedi_completion': {'resolve_at_most': math.inf}}})
    completions = pylsp_jedi_completions(config, doc, com_position)

    items = {c['label']: c['sortText'] for c in completions}

    # And that 'hidden' functions come after unhidden ones
    assert items['hello()'] < items['_a_hello()']


def test_jedi_property_completion(config, workspace):
    # Over the 'w' in 'print Hello().world'
    com_position = {'line': 18, 'character': 15}
    doc = Document(DOC_URI, workspace, DOC)
    completions = pylsp_jedi_completions(config, doc, com_position)

    items = {c['label']: c['sortText'] for c in completions}

    # Ensure we can complete the 'world' property
    assert 'world' in list(items.keys())[0]


def test_jedi_method_completion(config, workspace):
    # Over the 'y' in 'print Hello().every'
    com_position = {'line': 20, 'character': 19}
    doc = Document(DOC_URI, workspace, DOC)

    config.capabilities['textDocument'] = {'completion': {'completionItem': {'snippetSupport': True}}}
    config.update({'plugins': {'jedi_completion': {'include_params': True}}})

    completions = pylsp_jedi_completions(config, doc, com_position)
    everyone_method = [completion for completion in completions if completion['label'] == 'everyone(a, b, c, d)'][0]

    # Ensure we only generate snippets for positional args
    assert everyone_method['insertTextFormat'] == lsp.InsertTextFormat.Snippet
    assert everyone_method['insertText'] == 'everyone(${1:a}, ${2:b})$0'

    # Disable param snippets
    config.update({'plugins': {'jedi_completion': {'include_params': False}}})

    completions = pylsp_jedi_completions(config, doc, com_position)
    everyone_method = [completion for completion in completions if completion['label'] == 'everyone(a, b, c, d)'][0]

    assert 'insertTextFormat' not in everyone_method
    assert everyone_method['insertText'] == 'everyone'


@pytest.mark.skipif(PY2 or (sys.platform.startswith('linux') and os.environ.get('CI') is not None),
                    reason="Test in Python 3 and not on CIs on Linux because wheels don't work on them.")
def test_pyqt_completion(config, workspace):
    # Over 'QA' in 'from PyQt5.QtWidgets import QApplication'
    doc_pyqt = "from PyQt5.QtWidgets import QA"
    com_position = {'line': 0, 'character': len(doc_pyqt)}
    doc = Document(DOC_URI, workspace, doc_pyqt)
    completions = pylsp_jedi_completions(config, doc, com_position)

    assert completions is not None


def test_numpy_completions(config, workspace):
    doc_numpy = "import numpy as np; np."
    com_position = {'line': 0, 'character': len(doc_numpy)}
    doc = Document(DOC_URI, workspace, doc_numpy)
    items = pylsp_jedi_completions(config, doc, com_position)

    assert items
    assert any('array' in i['label'] for i in items)


def test_pandas_completions(config, workspace):
    doc_pandas = "import pandas as pd; pd."
    com_position = {'line': 0, 'character': len(doc_pandas)}
    doc = Document(DOC_URI, workspace, doc_pandas)
    items = pylsp_jedi_completions(config, doc, com_position)

    assert items
    assert any('DataFrame' in i['label'] for i in items)


def test_matplotlib_completions(config, workspace):
    doc_mpl = "import matplotlib.pyplot as plt; plt."
    com_position = {'line': 0, 'character': len(doc_mpl)}
    doc = Document(DOC_URI, workspace, doc_mpl)
    items = pylsp_jedi_completions(config, doc, com_position)

    assert items
    assert any('plot' in i['label'] for i in items)


def test_snippets_completion(config, workspace):
    doc_snippets = 'from collections import defaultdict \na=defaultdict'
    com_position = {'line': 0, 'character': 35}
    doc = Document(DOC_URI, workspace, doc_snippets)
    config.capabilities['textDocument'] = {
        'completion': {'completionItem': {'snippetSupport': True}}}
    config.update({'plugins': {'jedi_completion': {'include_params': True}}})
    completions = pylsp_jedi_completions(config, doc, com_position)
    assert completions[0]['insertText'] == 'defaultdict'

    com_position = {'line': 1, 'character': len(doc_snippets)}
    completions = pylsp_jedi_completions(config, doc, com_position)
    assert completions[0]['insertText'] == 'defaultdict($0)'
    assert completions[0]['insertTextFormat'] == lsp.InsertTextFormat.Snippet


def test_snippets_completion_at_most(config, workspace):
    doc_snippets = 'from collections import defaultdict \na=defaultdict'
    doc = Document(DOC_URI, workspace, doc_snippets)
    config.capabilities['textDocument'] = {
        'completion': {'completionItem': {'snippetSupport': True}}}
    config.update({'plugins': {'jedi_completion': {'include_params': True}}})
    config.update({'plugins': {'jedi_completion': {'resolve_at_most': 0}}})

    com_position = {'line': 1, 'character': len(doc_snippets)}
    completions = pylsp_jedi_completions(config, doc, com_position)
    assert completions[0]['insertText'] == 'defaultdict'
    assert not completions[0].get('insertTextFormat', None)


def test_completion_with_class_objects(config, workspace):
    doc_text = 'class FOOBAR(Object): pass\nFOOB'
    com_position = {'line': 1, 'character': 4}
    doc = Document(DOC_URI, workspace, doc_text)
    config.capabilities['textDocument'] = {
        'completion': {'completionItem': {'snippetSupport': True}}}
    config.update({'plugins': {'jedi_completion': {
        'include_params': True,
        'include_class_objects': True,
    }}})
    completions = pylsp_jedi_completions(config, doc, com_position)
    assert len(completions) == 2

    assert completions[0]['label'] == 'FOOBAR'
    assert completions[0]['kind'] == lsp.CompletionItemKind.Class

    assert completions[1]['label'] == 'FOOBAR object'
    assert completions[1]['kind'] == lsp.CompletionItemKind.TypeParameter


def test_completion_with_function_objects(config, workspace):
    doc_text = 'def foobar(): pass\nfoob'
    com_position = {'line': 1, 'character': 4}
    doc = Document(DOC_URI, workspace, doc_text)
    config.capabilities['textDocument'] = {
        'completion': {'completionItem': {'snippetSupport': True}}}
    config.update({'plugins': {'jedi_completion': {
        'include_params': True,
        'include_function_objects': True,
    }}})
    completions = pylsp_jedi_completions(config, doc, com_position)
    assert len(completions) == 2

    assert completions[0]['label'] == 'foobar()'
    assert completions[0]['kind'] == lsp.CompletionItemKind.Function

    assert completions[1]['label'] == 'foobar() object'
    assert completions[1]['kind'] == lsp.CompletionItemKind.TypeParameter


def test_snippet_parsing(config, workspace):
    doc = 'divmod'
    completion_position = {'line': 0, 'character': 6}
    doc = Document(DOC_URI, workspace, doc)
    config.capabilities['textDocument'] = {
        'completion': {'completionItem': {'snippetSupport': True}}}
    config.update({'plugins': {'jedi_completion': {'include_params': True}}})
    completions = pylsp_jedi_completions(config, doc, completion_position)

    out = 'divmod(${1:x}, ${2:y})$0'
    if JEDI_VERSION == '0.18.0':
        out = 'divmod(${1:a}, ${2:b})$0'
    assert completions[0]['insertText'] == out


def test_multiline_import_snippets(config, workspace):
    document = 'from datetime import(\n date,\n datetime)\na=date'
    doc = Document(DOC_URI, workspace, document)
    config.capabilities['textDocument'] = {
        'completion': {'completionItem': {'snippetSupport': True}}}
    config.update({'plugins': {'jedi_completion': {'include_params': True}}})

    position = {'line': 1, 'character': 5}
    completions = pylsp_jedi_completions(config, doc, position)
    assert completions[0]['insertText'] == 'date'

    position = {'line': 2, 'character': 9}
    completions = pylsp_jedi_completions(config, doc, position)
    assert completions[0]['insertText'] == 'datetime'


def test_multiline_snippets(config, workspace):
    document = 'from datetime import\\\n date,\\\n datetime \na=date'
    doc = Document(DOC_URI, workspace, document)
    config.capabilities['textDocument'] = {
        'completion': {'completionItem': {'snippetSupport': True}}}
    config.update({'plugins': {'jedi_completion': {'include_params': True}}})

    position = {'line': 1, 'character': 5}
    completions = pylsp_jedi_completions(config, doc, position)
    assert completions[0]['insertText'] == 'date'

    position = {'line': 2, 'character': 9}
    completions = pylsp_jedi_completions(config, doc, position)
    assert completions[0]['insertText'] == 'datetime'


def test_multistatement_snippet(config, workspace):
    config.capabilities['textDocument'] = {
        'completion': {'completionItem': {'snippetSupport': True}}}
    config.update({'plugins': {'jedi_completion': {'include_params': True}}})

    document = 'a = 1; from datetime import date'
    doc = Document(DOC_URI, workspace, document)
    position = {'line': 0, 'character': len(document)}
    completions = pylsp_jedi_completions(config, doc, position)
    assert completions[0]['insertText'] == 'date'

    document = 'from math import fmod; a = fmod'
    doc = Document(DOC_URI, workspace, document)
    position = {'line': 0, 'character': len(document)}
    completions = pylsp_jedi_completions(config, doc, position)
    assert completions[0]['insertText'] == 'fmod(${1:x}, ${2:y})$0'


def test_jedi_completion_extra_paths(tmpdir, workspace):
    # Create a tempfile with some content and pass to extra_paths
    temp_doc_content = '''
def spam():
    pass
'''
    p = tmpdir.mkdir("extra_path")
    extra_paths = [str(p)]
    p = p.join("foo.py")
    p.write(temp_doc_content)

    # Content of doc to test completion
    doc_content = """import foo
foo.s"""
    doc = Document(DOC_URI, workspace, doc_content)

    # After 'foo.s' without extra paths
    com_position = {'line': 1, 'character': 5}
    completions = pylsp_jedi_completions(doc._config, doc, com_position)
    assert completions is None

    # Update config extra paths
    settings = {'pylsp': {'plugins': {'jedi': {'extra_paths': extra_paths}}}}
    doc.update_config(settings)

    # After 'foo.s' with extra paths
    com_position = {'line': 1, 'character': 5}
    completions = pylsp_jedi_completions(doc._config, doc, com_position)
    assert completions[0]['label'] == 'spam()'


@pytest.mark.skipif(PY2 or not LINUX or not CI, reason="tested on linux and python 3 only")
def test_jedi_completion_environment(workspace):
    # Content of doc to test completion
    doc_content = '''import logh
'''
    doc = Document(DOC_URI, workspace, doc_content)

    # After 'import logh' with default environment
    com_position = {'line': 0, 'character': 11}

    assert os.path.isdir('/tmp/pyenv/')

    settings = {'pylsp': {'plugins': {'jedi': {'environment': None}}}}
    doc.update_config(settings)
    completions = pylsp_jedi_completions(doc._config, doc, com_position)
    assert completions is None

    # Update config extra environment
    env_path = '/tmp/pyenv/bin/python'
    settings = {'pylsp': {'plugins': {'jedi': {'environment': env_path}}}}
    doc.update_config(settings)

    # After 'import logh' with new environment
    completions = pylsp_jedi_completions(doc._config, doc, com_position)
    assert completions[0]['label'] == 'loghub'

    resolved = pylsp_jedi_completion_item_resolve(completions[0], doc)
    assert 'changelog generator' in resolved['documentation'].lower()


def test_document_path_completions(tmpdir, workspace_other_root_path):
    # Create a dummy module out of the workspace's root_path and try to get
    # completions for it in another file placed next to it.
    module_content = '''
def foo():
    pass
'''

    p = tmpdir.join("mymodule.py")
    p.write(module_content)

    # Content of doc to test completion
    doc_content = """import mymodule
mymodule.f"""
    doc_path = str(tmpdir) + os.path.sep + 'myfile.py'
    doc_uri = uris.from_fs_path(doc_path)
    doc = Document(doc_uri, workspace_other_root_path, doc_content)

    com_position = {'line': 1, 'character': 10}
    completions = pylsp_jedi_completions(doc._config, doc, com_position)
    assert completions[0]['label'] == 'foo()'
