# Copyright 2018 Google LLC.
# Copyright 2017-2020 Palantir Technologies, Inc.
# Copyright 2021- Python Language Server Contributors.

import contextlib
import os
import tempfile

from pylsp import lsp, uris
from pylsp.workspace import Document
from pylsp.plugins import pylint_lint

DOC_URI = uris.from_fs_path(__file__)
DOC = """import sys

def hello():
\tpass

import json
"""

DOC_SYNTAX_ERR = """def hello()
    pass
"""


@contextlib.contextmanager
def temp_document(doc_text, workspace):
    try:
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            name = temp_file.name
            temp_file.write(doc_text)
        yield Document(uris.from_fs_path(name), workspace)
    finally:
        os.remove(name)


def write_temp_doc(document, contents):
    with open(document.path, 'w', encoding='utf-8') as temp_file:
        temp_file.write(contents)


def test_pylint(config, workspace):
    with temp_document(DOC, workspace) as doc:
        diags = pylint_lint.pylsp_lint(config, doc, True)

        msg = '[unused-import] Unused import sys'
        unused_import = [d for d in diags if d['message'] == msg][0]

        assert unused_import['range']['start'] == {'line': 0, 'character': 0}
        assert unused_import['severity'] == lsp.DiagnosticSeverity.Warning
        assert unused_import['tags'] == [lsp.DiagnosticTag.Unnecessary]

        # test running pylint in stdin
        config.plugin_settings('pylint')['executable'] = 'pylint'
        diags = pylint_lint.pylsp_lint(config, doc, True)

        msg = 'Unused import sys (unused-import)'
        unused_import = [d for d in diags if d['message'] == msg][0]

        assert unused_import['range']['start'] == {
            'line': 0,
            'character': 0,
        }
        assert unused_import['severity'] == lsp.DiagnosticSeverity.Warning


def test_syntax_error_pylint(config, workspace):
    with temp_document(DOC_SYNTAX_ERR, workspace) as doc:
        diag = pylint_lint.pylsp_lint(config, doc, True)[0]

        assert diag['message'].startswith("[syntax-error]")
        assert diag['message'].count("expected ':'") or diag['message'].count('invalid syntax')
        # Pylint doesn't give column numbers for invalid syntax.
        assert diag['range']['start'] == {'line': 0, 'character': 12}
        assert diag['severity'] == lsp.DiagnosticSeverity.Error
        assert 'tags' not in diag

        # test running pylint in stdin
        config.plugin_settings('pylint')['executable'] = 'pylint'
        diag = pylint_lint.pylsp_lint(config, doc, True)[0]

        assert diag['message'].count("expected ':'") or diag['message'].count('invalid syntax')
        # Pylint doesn't give column numbers for invalid syntax.
        assert diag['range']['start'] == {'line': 0, 'character': 12}
        assert diag['severity'] == lsp.DiagnosticSeverity.Error


def test_lint_free_pylint(config, workspace):
    # Can't use temp_document because it might give us a file that doesn't
    # match pylint's naming requirements. We should be keeping this file clean
    # though, so it works for a test of an empty lint.
    assert not pylint_lint.pylsp_lint(
        config, Document(uris.from_fs_path(__file__), workspace), True)


def test_lint_caching(workspace):
    # Pylint can only operate on files, not in-memory contents. We cache the
    # diagnostics after a run so we can continue displaying them until the file
    # is saved again.
    #
    # We use PylintLinter.lint directly here rather than pylsp_lint so we can
    # pass --disable=invalid-name to pylint, since we want a temporary file but
    # need to ensure that pylint doesn't give us invalid-name when our temp
    # file has capital letters in its name.

    flags = '--disable=invalid-name'
    with temp_document(DOC, workspace) as doc:
        # Start with a file with errors.
        diags = pylint_lint.PylintLinter.lint(doc, True, flags)
        assert diags

        # Fix lint errors and write the changes to disk. Run the linter in the
        # in-memory mode to check the cached diagnostic behavior.
        write_temp_doc(doc, '')
        assert pylint_lint.PylintLinter.lint(doc, False, flags) == diags

        # Now check the on-disk behavior.
        assert not pylint_lint.PylintLinter.lint(doc, True, flags)

        # Make sure the cache was properly cleared.
        assert not pylint_lint.PylintLinter.lint(doc, False, flags)


def test_per_file_caching(config, workspace):
    # Ensure that diagnostics are cached per-file.
    with temp_document(DOC, workspace) as doc:
        assert pylint_lint.pylsp_lint(config, doc, True)

    assert not pylint_lint.pylsp_lint(
        config, Document(uris.from_fs_path(__file__), workspace), False)
