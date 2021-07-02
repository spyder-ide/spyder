# Copyright 2017-2020 Palantir Technologies, Inc.
# Copyright 2021- Python Language Server Contributors.

import os
from pylsp import lsp, uris
from pylsp.workspace import Document
from pylsp.plugins import pydocstyle_lint

DOC_URI = uris.from_fs_path(os.path.join(os.path.dirname(__file__), "pydocstyle.py"))
TEST_DOC_URI = uris.from_fs_path(__file__)

DOC = """import sys

def hello():
\tpass

import json
"""


def test_pydocstyle(config, workspace):
    doc = Document(DOC_URI, workspace, DOC)
    diags = pydocstyle_lint.pylsp_lint(config, doc)

    assert all(d['source'] == 'pydocstyle' for d in diags)

    # One we're expecting is:
    assert diags[0] == {
        'code': 'D100',
        'message': 'D100: Missing docstring in public module',
        'severity': lsp.DiagnosticSeverity.Warning,
        'range': {
            'start': {'line': 0, 'character': 0},
            'end': {'line': 0, 'character': 11},
        },
        'source': 'pydocstyle'
    }


def test_pydocstyle_test_document(config, workspace):
    # The default --match argument excludes test_* documents.
    doc = Document(TEST_DOC_URI, workspace, "")
    diags = pydocstyle_lint.pylsp_lint(config, doc)
    assert not diags


def test_pydocstyle_empty_source(config, workspace):
    doc = Document(DOC_URI, workspace, "")
    diags = pydocstyle_lint.pylsp_lint(config, doc)
    assert diags[0]['message'] == 'D100: Missing docstring in public module'
    assert len(diags) == 1


def test_pydocstyle_invalid_source(config, workspace):
    doc = Document(DOC_URI, workspace, "bad syntax")
    diags = pydocstyle_lint.pylsp_lint(config, doc)
    # We're unable to parse the file, so can't get any pydocstyle diagnostics
    assert not diags
