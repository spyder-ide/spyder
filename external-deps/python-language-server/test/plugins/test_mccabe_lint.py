# Copyright 2017 Palantir Technologies, Inc.
from pyls import lsp, uris
from pyls.workspace import Document
from pyls.plugins import mccabe_lint

DOC_URI = uris.from_fs_path(__file__)
DOC = """def hello():
\tpass
"""

DOC_SYNTAX_ERR = """def hello()
\tpass"""


def test_mccabe(config):
    old_settings = config.settings
    try:
        config.update({'plugins': {'mccabe': {'threshold': 1}}})
        doc = Document(DOC_URI, DOC)
        diags = mccabe_lint.pyls_lint(config, doc)

        assert all([d['source'] == 'mccabe' for d in diags])

        # One we're expecting is:
        msg = 'Cyclomatic complexity too high: 1 (threshold 1)'
        mod_import = [d for d in diags if d['message'] == msg][0]

        assert mod_import['severity'] == lsp.DiagnosticSeverity.Warning
        assert mod_import['range']['start'] == {'line': 0, 'character': 0}
        assert mod_import['range']['end'] == {'line': 0, 'character': 6}
    finally:
        config._settings = old_settings


def test_mccabe_syntax_error(config):
    doc = Document(DOC_URI, DOC_SYNTAX_ERR)
    assert mccabe_lint.pyls_lint(config, doc) is None
