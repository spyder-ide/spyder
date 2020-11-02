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


def temp_document(doc_text, workspace):
    temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False)
    name = temp_file.name
    temp_file.write(doc_text)
    temp_file.close()
    doc = Document(uris.from_fs_path(name), workspace)

    return name, doc


def test_flake8_unsaved(workspace):
    doc = Document('', workspace, DOC)
    diags = flake8_lint.pyls_lint(workspace, doc)
    msg = 'local variable \'a\' is assigned to but never used'
    unused_var = [d for d in diags if d['message'] == msg][0]

    assert unused_var['source'] == 'flake8'
    assert unused_var['code'] == 'F841'
    assert unused_var['range']['start'] == {'line': 5, 'character': 1}
    assert unused_var['range']['end'] == {'line': 5, 'character': 11}
    assert unused_var['severity'] == lsp.DiagnosticSeverity.Warning


def test_flake8_lint(workspace):
    try:
        name, doc = temp_document(DOC, workspace)
        diags = flake8_lint.pyls_lint(workspace, doc)
        msg = 'local variable \'a\' is assigned to but never used'
        unused_var = [d for d in diags if d['message'] == msg][0]

        assert unused_var['source'] == 'flake8'
        assert unused_var['code'] == 'F841'
        assert unused_var['range']['start'] == {'line': 5, 'character': 1}
        assert unused_var['range']['end'] == {'line': 5, 'character': 11}
        assert unused_var['severity'] == lsp.DiagnosticSeverity.Warning

    finally:
        os.remove(name)


def test_flake8_config_param(workspace):
    with patch('pyls.plugins.flake8_lint.Popen') as popen_mock:
        mock_instance = popen_mock.return_value
        mock_instance.communicate.return_value = [bytes(), bytes()]
        flake8_conf = '/tmp/some.cfg'
        workspace._config.update({'plugins': {'flake8': {'config': flake8_conf}}})
        _name, doc = temp_document(DOC, workspace)
        flake8_lint.pyls_lint(workspace, doc)
        call_args = popen_mock.call_args.args[0]
        assert 'flake8' in call_args
        assert '--config={}'.format(flake8_conf) in call_args


def test_flake8_executable_param(workspace):
    with patch('pyls.plugins.flake8_lint.Popen') as popen_mock:
        mock_instance = popen_mock.return_value
        mock_instance.communicate.return_value = [bytes(), bytes()]

        flake8_executable = '/tmp/flake8'
        workspace._config.update({'plugins': {'flake8': {'executable': flake8_executable}}})

        _name, doc = temp_document(DOC, workspace)
        flake8_lint.pyls_lint(workspace, doc)

        call_args = popen_mock.call_args.args[0]
        assert flake8_executable in call_args
