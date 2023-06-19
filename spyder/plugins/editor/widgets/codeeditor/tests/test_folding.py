# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""Tests for the folding features."""

# Standard library imports
import os

# Third party imports
from flaky import flaky
import pytest
from qtpy.QtCore import Qt


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


@pytest.mark.order(2)
@flaky(max_runs=5)
def test_folding(completions_codeeditor, qtbot):
    code_editor, _ = completions_codeeditor
    code_editor.toggle_code_folding(True)
    code_editor.insert_text(text)
    folding_panel = code_editor.panels.get('FoldingPanel')

    # Wait for the update thread to finish
    qtbot.wait(3000)

    folding_regions = folding_panel.folding_regions
    folding_levels = folding_panel.folding_levels

    expected_regions = {2: 6, 3: 4, 8: 36, 22: 23, 24: 26, 27: 28,
                        30: 31, 32: 33, 34: 35}
    expected_levels = {2: 0, 3: 1, 8: 0, 22: 1, 24: 1, 27: 1, 30: 1,
                       32: 1, 34: 1}
    assert folding_regions == expected_regions
    assert expected_levels == folding_levels
    code_editor.toggle_code_folding(False)


@pytest.mark.order(2)
@flaky(max_runs=5)
@pytest.mark.skipif(os.name == 'nt', reason="Hangs on Windows")
def test_unfold_when_searching(search_codeeditor, qtbot):
    editor, finder = search_codeeditor
    editor.toggle_code_folding(True)

    folding_panel = editor.panels.get('FoldingPanel')
    editor.insert_text(text)

    # Wait for the update thread to finish
    qtbot.wait(3000)

    line_search = editor.document().findBlockByLineNumber(3)

    # fold region
    block = editor.document().findBlockByLineNumber(2)
    folding_panel.toggle_fold_trigger(block)
    assert not line_search.isVisible()

    # unfolded when searching
    finder.show()
    qtbot.keyClicks(finder.search_text, 'print')
    qtbot.keyPress(finder.search_text, Qt.Key_Return)
    assert line_search.isVisible()
    editor.toggle_code_folding(False)


@pytest.mark.order(2)
@flaky(max_runs=5)
@pytest.mark.skipif(os.name == 'nt', reason="Hangs on Windows")
def test_unfold_goto(search_codeeditor, qtbot):
    editor, finder = search_codeeditor
    editor.toggle_code_folding(True)
    editor.insert_text(text)
    folding_panel = editor.panels.get('FoldingPanel')

    # Wait for the update thread to finish
    qtbot.wait(3000)

    line_goto = editor.document().findBlockByLineNumber(5)

    # fold region
    block = editor.document().findBlockByLineNumber(2)
    folding_panel.toggle_fold_trigger(block)
    assert not line_goto.isVisible()

    # unfolded when goto
    editor.go_to_line(6)
    assert line_goto.isVisible()
    editor.toggle_code_folding(False)
