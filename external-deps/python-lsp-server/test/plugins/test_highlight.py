# Copyright 2017-2020 Palantir Technologies, Inc.
# Copyright 2021- Python Language Server Contributors.

from pylsp import lsp, uris
from pylsp.workspace import Document
from pylsp.plugins.highlight import pylsp_document_highlight


DOC_URI = uris.from_fs_path(__file__)
DOC = """a = "hello"
a.startswith("b")
"""


def test_highlight(workspace):
    # Over 'a' in a.startswith
    cursor_pos = {'line': 1, 'character': 0}

    doc = Document(DOC_URI, workspace, DOC)
    assert pylsp_document_highlight(doc, cursor_pos) == [{
        'range': {
            'start': {'line': 0, 'character': 0},
            'end': {'line': 0, 'character': 1},
        },
        # The first usage is Write
        'kind': lsp.DocumentHighlightKind.Write
    }, {
        'range': {
            'start': {'line': 1, 'character': 0},
            'end': {'line': 1, 'character': 1},
        },
        # The second usage is Read
        'kind': lsp.DocumentHighlightKind.Read
    }]


SYS_DOC = '''import sys
print sys.path
'''


def test_sys_highlight(workspace):
    cursor_pos = {'line': 0, 'character': 8}

    doc = Document(DOC_URI, workspace, SYS_DOC)
    assert pylsp_document_highlight(doc, cursor_pos) == [{
        'range': {
            'start': {'line': 0, 'character': 7},
            'end': {'line': 0, 'character': 10}
        },
        'kind': lsp.DocumentHighlightKind.Write
    }, {
        'range': {
            'start': {'line': 1, 'character': 6},
            'end': {'line': 1, 'character': 9}
        },
        'kind': lsp.DocumentHighlightKind.Read
    }]
