# Copyright 2017-2020 Palantir Technologies, Inc.
# Copyright 2021- Python Language Server Contributors.

from pylsp import lsp, uris
from pylsp.workspace import Document
from pylsp.plugins import mccabe_lint

DOC_URI = uris.from_fs_path(__file__)
DOC = """def hello():
\tpass
"""

DOC_SYNTAX_ERR = """def hello()
\tpass"""


def test_mccabe(config, workspace):
    old_settings = config.settings
    try:
        config.update({'plugins': {'mccabe': {'threshold': 1}}})
        doc = Document(DOC_URI, workspace, DOC)
        diags = mccabe_lint.pylsp_lint(config, doc)

        assert all(d['source'] == 'mccabe' for d in diags)

        # One we're expecting is:
        msg = 'Cyclomatic complexity too high: 1 (threshold 1)'
        mod_import = [d for d in diags if d['message'] == msg][0]

        assert mod_import['severity'] == lsp.DiagnosticSeverity.Warning
        assert mod_import['range']['start'] == {'line': 0, 'character': 0}
        assert mod_import['range']['end'] == {'line': 0, 'character': 6}
    finally:
        config._settings = old_settings


def test_mccabe_syntax_error(config, workspace):
    doc = Document(DOC_URI, workspace, DOC_SYNTAX_ERR)
    assert mccabe_lint.pylsp_lint(config, doc) is None
