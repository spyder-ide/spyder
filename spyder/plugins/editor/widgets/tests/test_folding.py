# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for the autoindent features
"""

# Third party imports
import pytest

# Local imports
from spyder.plugins.editor.widgets.codeeditor import CodeEditor
from spyder.plugins.editor.api.folding import print_tree

# ---Fixtures-----------------------------------------------------------------
text = """
def myfunc2():
    x = [0, 1, 2, 3,
        3 , 4] # Arbitary Code
    x[0] = 2 # Desired break
    print(x[1]) # Arbitary Code

responses = {
    100: ('Continue', 'Request received, please continue'),
    101: ('Switching Protocols','Switching to new protocol'),
    200: ('OK', 'Request fulfilled, document follows'),
    201: ('Created', 'Document created, URL follows'),
    202: ('Accepted','Request accepted, processing continues off-line'),
    203: ('Non-Authoritative Information', 'Request fulfilled from cache'),
    204: ('No Content', 'Request fulfilled, nothing follows'),
    205: ('Reset Content', 'Clear input form for further input.'),
    206: ('Partial Content', 'Partial content follows.'),
    300: ('Multiple Choices','Object has several resources'),
    301: ('Moved Permanently', 'Object moved permanently -- see URI list'),
    302: ('Found', 'Object moved temporarily -- see URI list'),
    303: ('See Other', 'Object moved -- see Method and URL list'),
    304: ('Not Modified',
        'Document has not changed since given time'),
    305: ('Use Proxy',
        'You must use proxy specified in Location to access this ',
        'resource.'),
    307: ('Temporary Redirect',
        'Object moved temporarily -- see URI list'),

    400: ('Bad Request',
        'Bad request syntax or unsupported method'),
    401: ('Unauthorized',
        'No permission -- see authorization schemes'),
    402: ('Payment Required',
        'No payment -- see charging schemes')
}"""

# --- Fixtures-----------------------------------------------------------------
@pytest.fixture()
def code_editor():
    """setup editor and return fold levels."""
    editor = CodeEditor(parent=None)
    editor.setup_editor(language='Python')
    editor.set_text(text)
    return editor


# --- Tests--------------------------------------------------------------------
def test_simple_folding(code_editor):
    """Test folding by the levels."""
    expected_folding_levels = [0, 0, 1, 2, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1,
                               1, 1, 1, 1, 1, 1, 2, 1, 2, 2, 1, 2, 2, 1, 2, 1,
                               2, 1, 2, 0]

    output_fold = print_tree(code_editor, return_list=True)
    for expected_lvl, (line, lvl, visible) in zip(expected_folding_levels,
                                                  output_fold):
        assert expected_lvl == lvl
