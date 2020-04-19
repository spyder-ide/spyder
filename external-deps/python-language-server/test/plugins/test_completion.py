# Copyright 2017 Palantir Technologies, Inc.
from distutils.version import LooseVersion
import os
import sys

from test.test_utils import MockWorkspace
import pytest

from pyls import uris, lsp
from pyls._utils import JEDI_VERSION
from pyls.workspace import Document
from pyls.plugins.jedi_completion import pyls_completions as pyls_jedi_completions
from pyls.plugins.rope_completion import pyls_completions as pyls_rope_completions


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
"""


def test_rope_import_completion(config, workspace):
    com_position = {'line': 0, 'character': 7}
    doc = Document(DOC_URI, DOC)
    items = pyls_rope_completions(config, workspace, doc, com_position)
    assert items is None


def test_jedi_completion(config):
    # Over 'i' in os.path.isabs(...)
    com_position = {'line': 1, 'character': 15}
    doc = Document(DOC_URI, DOC)
    items = pyls_jedi_completions(config, doc, com_position)

    assert items
    assert items[0]['label'] == 'isabs(path)'

    # Test we don't throw with big character
    pyls_jedi_completions(config, doc, {'line': 1, 'character': 1000})


def test_rope_completion(config, workspace):
    # Over 'i' in os.path.isabs(...)
    com_position = {'line': 1, 'character': 15}
    workspace.put_document(DOC_URI, source=DOC)
    doc = workspace.get_document(DOC_URI)
    items = pyls_rope_completions(config, workspace, doc, com_position)

    assert items
    assert items[0]['label'] == 'isabs'


def test_jedi_completion_ordering(config):
    # Over the blank line
    com_position = {'line': 8, 'character': 0}
    doc = Document(DOC_URI, DOC)
    completions = pyls_jedi_completions(config, doc, com_position)

    items = {c['label']: c['sortText'] for c in completions}

    # And that 'hidden' functions come after unhidden ones
    assert items['hello()'] < items['_a_hello()']


def test_jedi_property_completion(config):
    # Over the 'w' in 'print Hello().world'
    com_position = {'line': 18, 'character': 15}
    doc = Document(DOC_URI, DOC)
    completions = pyls_jedi_completions(config, doc, com_position)

    items = {c['label']: c['sortText'] for c in completions}

    # Ensure we can complete the 'world' property
    assert 'world' in list(items.keys())[0]


def test_jedi_method_completion(config):
    # Over the 'y' in 'print Hello().every'
    com_position = {'line': 20, 'character': 19}
    doc = Document(DOC_URI, DOC)

    config.capabilities['textDocument'] = {'completion': {'completionItem': {'snippetSupport': True}}}
    config.update({'plugins': {'jedi_completion': {'include_params': True}}})

    completions = pyls_jedi_completions(config, doc, com_position)
    everyone_method = [completion for completion in completions if completion['label'] == 'everyone(a, b, c, d)'][0]

    # Ensure we only generate snippets for positional args
    assert everyone_method['insertTextFormat'] == lsp.InsertTextFormat.Snippet
    assert everyone_method['insertText'] == 'everyone(${1:a}, ${2:b})$0'

    # Disable param snippets
    config.update({'plugins': {'jedi_completion': {'include_params': False}}})

    completions = pyls_jedi_completions(config, doc, com_position)
    everyone_method = [completion for completion in completions if completion['label'] == 'everyone(a, b, c, d)'][0]

    assert 'insertTextFormat' not in everyone_method
    assert everyone_method['insertText'] == 'everyone'


@pytest.mark.skipif(PY2 or (sys.platform.startswith('linux') and os.environ.get('CI') is not None),
                    reason="Test in Python 3 and not on CIs on Linux because wheels don't work on them.")
def test_pyqt_completion(config):
    # Over 'QA' in 'from PyQt5.QtWidgets import QApplication'
    doc_pyqt = "from PyQt5.QtWidgets import QA"
    com_position = {'line': 0, 'character': len(doc_pyqt)}
    doc = Document(DOC_URI, doc_pyqt)
    completions = pyls_jedi_completions(config, doc, com_position)

    # Test we don't throw an error for Jedi < 0.15.2 and get completions
    # for Jedi 0.15.2+
    if LooseVersion(JEDI_VERSION) < LooseVersion('0.15.2'):
        assert completions is None
    else:
        assert completions is not None


@pytest.mark.skipif(LooseVersion('0.15.0') <= LooseVersion(JEDI_VERSION) < LooseVersion('0.15.2'),
                    reason='This test fails with Jedi 0.15.0 and 0.15.1')
def test_numpy_completions(config):
    doc_numpy = "import numpy as np; np."
    com_position = {'line': 0, 'character': len(doc_numpy)}
    doc = Document(DOC_URI, doc_numpy)
    items = pyls_jedi_completions(config, doc, com_position)

    assert items
    assert any(['array' in i['label'] for i in items])


@pytest.mark.skipif(LooseVersion('0.15.0') <= LooseVersion(JEDI_VERSION) < LooseVersion('0.15.2'),
                    reason='This test fails with Jedi 0.15.0 and 0.15.1')
def test_pandas_completions(config):
    doc_pandas = "import pandas as pd; pd."
    com_position = {'line': 0, 'character': len(doc_pandas)}
    doc = Document(DOC_URI, doc_pandas)
    items = pyls_jedi_completions(config, doc, com_position)

    assert items
    assert any(['DataFrame' in i['label'] for i in items])


def test_matplotlib_completions(config):
    doc_mpl = "import matplotlib.pyplot as plt; plt."
    com_position = {'line': 0, 'character': len(doc_mpl)}
    doc = Document(DOC_URI, doc_mpl)
    items = pyls_jedi_completions(config, doc, com_position)

    assert items
    assert any(['plot' in i['label'] for i in items])


@pytest.mark.skipif(LooseVersion(JEDI_VERSION) < LooseVersion('0.15.2'),
                    reason='This test fails with Jedi 0.15.1 or less')
def test_snippets_completion(config):
    doc_snippets = 'from collections import defaultdict \na=defaultdict'
    com_position = {'line': 0, 'character': 35}
    doc = Document(DOC_URI, doc_snippets)
    config.capabilities['textDocument'] = {
        'completion': {'completionItem': {'snippetSupport': True}}}
    config.update({'plugins': {'jedi_completion': {'include_params': True}}})
    completions = pyls_jedi_completions(config, doc, com_position)
    assert completions[0]['insertText'] == 'defaultdict'

    com_position = {'line': 1, 'character': len(doc_snippets)}
    completions = pyls_jedi_completions(config, doc, com_position)
    assert completions[0]['insertText'] == 'defaultdict($0)'


def test_snippet_parsing(config):
    doc = 'import numpy as np\nnp.logical_and'
    completion_position = {'line': 1, 'character': 14}
    doc = Document(DOC_URI, doc)
    config.capabilities['textDocument'] = {
        'completion': {'completionItem': {'snippetSupport': True}}}
    config.update({'plugins': {'jedi_completion': {'include_params': True}}})
    completions = pyls_jedi_completions(config, doc, completion_position)
    out = 'logical_and(${1:x1}, ${2:x2})$0'
    assert completions[0]['insertText'] == out


def test_multiline_import_snippets(config):
    document = 'from datetime import(\n date,\n datetime)\na=date'
    doc = Document(DOC_URI, document)
    config.capabilities['textDocument'] = {
        'completion': {'completionItem': {'snippetSupport': True}}}
    config.update({'plugins': {'jedi_completion': {'include_params': True}}})

    position = {'line': 1, 'character': 5}
    completions = pyls_jedi_completions(config, doc, position)
    assert completions[0]['insertText'] == 'date'

    position = {'line': 2, 'character': 9}
    completions = pyls_jedi_completions(config, doc, position)
    assert completions[0]['insertText'] == 'datetime'


def test_multiline_snippets(config):
    document = 'from datetime import\\\n date,\\\n datetime \na=date'
    doc = Document(DOC_URI, document)
    config.capabilities['textDocument'] = {
        'completion': {'completionItem': {'snippetSupport': True}}}
    config.update({'plugins': {'jedi_completion': {'include_params': True}}})

    position = {'line': 1, 'character': 5}
    completions = pyls_jedi_completions(config, doc, position)
    assert completions[0]['insertText'] == 'date'

    position = {'line': 2, 'character': 9}
    completions = pyls_jedi_completions(config, doc, position)
    assert completions[0]['insertText'] == 'datetime'


def test_multistatement_snippet(config):
    config.capabilities['textDocument'] = {
        'completion': {'completionItem': {'snippetSupport': True}}}
    config.update({'plugins': {'jedi_completion': {'include_params': True}}})

    document = 'a = 1; from datetime import date'
    doc = Document(DOC_URI, document)
    position = {'line': 0, 'character': len(document)}
    completions = pyls_jedi_completions(config, doc, position)
    assert completions[0]['insertText'] == 'date'

    document = 'from datetime import date; a = date'
    doc = Document(DOC_URI, document)
    position = {'line': 0, 'character': len(document)}
    completions = pyls_jedi_completions(config, doc, position)
    assert completions[0]['insertText'] == 'date(${1:year}, ${2:month}, ${3:day})$0'


def test_jedi_completion_extra_paths(config, tmpdir):
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
    doc = Document(DOC_URI, doc_content)

    # After 'foo.s' without extra paths
    com_position = {'line': 1, 'character': 5}
    completions = pyls_jedi_completions(config, doc, com_position)
    assert completions is None

    # Update config extra paths
    config.update({'plugins': {'jedi': {'extra_paths': extra_paths}}})
    doc.update_config(config)

    # After 'foo.s' with extra paths
    com_position = {'line': 1, 'character': 5}
    completions = pyls_jedi_completions(config, doc, com_position)
    assert completions[0]['label'] == 'spam()'


@pytest.mark.skipif(PY2 or not LINUX or not CI, reason="tested on linux and python 3 only")
def test_jedi_completion_environment(config):
    # Content of doc to test completion
    doc_content = '''import logh
'''
    doc = Document(DOC_URI, doc_content, workspace=MockWorkspace())

    # After 'import logh' with default environment
    com_position = {'line': 0, 'character': 11}

    assert os.path.isdir('/tmp/pyenv/')

    config.update({'plugins': {'jedi': {'environment': None}}})
    doc.update_config(config)
    completions = pyls_jedi_completions(config, doc, com_position)
    assert completions is None

    # Update config extra environment
    env_path = '/tmp/pyenv/bin/python'
    config.update({'plugins': {'jedi': {'environment': env_path}}})
    doc.update_config(config)

    # After 'import logh' with new environment
    completions = pyls_jedi_completions(config, doc, com_position)
    assert completions[0]['label'] == 'loghub'
    assert 'changelog generator' in completions[0]['documentation'].lower()
