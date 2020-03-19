# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""Tests for completion that doesn't fit in instropection.py due to Windows."""

# Third party imports
from flaky import flaky
import pytest


@pytest.mark.slow
@pytest.mark.first
@flaky(max_runs=5)
def test_automatic_completions_hide_complete(lsp_codeeditor, qtbot):
    """Test on-the-fly completion closing when already complete.

    Regression test for issue #11600 and pull request #11824.
    """
    code_editor, _ = lsp_codeeditor
    completion = code_editor.completion_widget
    code_editor.toggle_code_snippets(False)

    code_editor.set_text('some = 0\nsomething = 1\n')
    cursor = code_editor.textCursor()
    code_editor.moveCursor(cursor.End)

    # Complete some -> [some, something]
    with qtbot.waitSignal(completion.sig_show_completions,
                          timeout=10000) as sig:
        qtbot.keyClicks(code_editor, 'some')
    assert "some" in [x['label'] for x in sig.args[0]]
    assert "something" in [x['label'] for x in sig.args[0]]

    # No completion for 'something' as already complete
    qtbot.keyClicks(code_editor, 'thing')
    qtbot.wait(500)
    assert completion.isHidden()

    code_editor.toggle_code_snippets(True)


if __name__ == '__main__':
    pytest.main(['test_completion.py', '--run-slow'])
