# Copyright 2017-2020 Palantir Technologies, Inc.
# Copyright 2021- Python Language Server Contributors.

from pylsp import lsp, uris
from pylsp.workspace import Document
from pylsp.plugins import pyflakes_lint

DOC_URI = uris.from_fs_path(__file__)
DOC = """import sys

def hello():
\tpass

import json
"""

DOC_SYNTAX_ERR = """def hello()
    pass
"""

DOC_UNDEFINED_NAME_ERR = "a = b"


DOC_ENCODING = u"""# encoding=utf-8
import sys
"""


def test_pyflakes(workspace):
    doc = Document(DOC_URI, workspace, DOC)
    diags = pyflakes_lint.pylsp_lint(doc)

    # One we're expecting is:
    msg = '\'sys\' imported but unused'
    unused_import = [d for d in diags if d['message'] == msg][0]

    assert unused_import['range']['start'] == {'line': 0, 'character': 0}
    assert unused_import['severity'] == lsp.DiagnosticSeverity.Warning


def test_syntax_error_pyflakes(workspace):
    doc = Document(DOC_URI, workspace, DOC_SYNTAX_ERR)
    diag = pyflakes_lint.pylsp_lint(doc)[0]

    assert diag['message'] == 'invalid syntax'
    assert diag['range']['start'] == {'line': 0, 'character': 12}
    assert diag['severity'] == lsp.DiagnosticSeverity.Error


def test_undefined_name_pyflakes(workspace):
    doc = Document(DOC_URI, workspace, DOC_UNDEFINED_NAME_ERR)
    diag = pyflakes_lint.pylsp_lint(doc)[0]

    assert diag['message'] == 'undefined name \'b\''
    assert diag['range']['start'] == {'line': 0, 'character': 4}
    assert diag['severity'] == lsp.DiagnosticSeverity.Error


def test_unicode_encoding(workspace):
    doc = Document(DOC_URI, workspace, DOC_ENCODING)
    diags = pyflakes_lint.pylsp_lint(doc)

    assert len(diags) == 1
    assert diags[0]['message'] == '\'sys\' imported but unused'
