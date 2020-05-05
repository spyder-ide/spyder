# Copyright 2019 Palantir Technologies, Inc.
import tempfile
import os
from mock import patch

from pyls import lsp, uris
from pyls.plugins import flake8_lint
from pyls.workspace import Document

DOC_URI = uris.from_fs_path(__file__)
DOC = """import pyls

t = "TEST"

def using_const():
\ta = 8 + 9
\treturn t
"""


def temp_document(doc_text):
    temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False)
    name = temp_file.name
    temp_file.write(doc_text)
    temp_file.close()
    doc = Document(uris.from_fs_path(name))

    return name, doc


def test_flake8_no_checked_file(config):
    # A bad uri or a non-saved file may cause the flake8 linter to do nothing.
    # In this situtation, the linter will return an empty list.

    doc = Document('', DOC)
    diags = flake8_lint.pyls_lint(config, doc)
    assert diags == []


def test_flake8_lint(config):
    try:
        name, doc = temp_document(DOC)
        diags = flake8_lint.pyls_lint(config, doc)
        msg = 'local variable \'a\' is assigned to but never used'
        unused_var = [d for d in diags if d['message'] == msg][0]

        assert unused_var['source'] == 'flake8'
        assert unused_var['code'] == 'F841'
        assert unused_var['range']['start'] == {'line': 5, 'character': 1}
        assert unused_var['range']['end'] == {'line': 5, 'character': 11}
        assert unused_var['severity'] == lsp.DiagnosticSeverity.Warning

    finally:
        os.remove(name)


def test_flake8_config_param(config):
    with patch('pyls.plugins.flake8_lint.Popen') as popen_mock:
        flake8_conf = '/tmp/some.cfg'
        config.update({'plugins': {'flake8': {'config': flake8_conf}}})
        _name, doc = temp_document(DOC)
        flake8_lint.pyls_lint(config, doc)
        call_args = popen_mock.call_args.args[0]
        assert 'flake8' in call_args
        assert '--config={}'.format(flake8_conf) in call_args
