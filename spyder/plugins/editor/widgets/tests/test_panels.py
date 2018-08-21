# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#
'''
Tests for editor panels.
'''

# Third party imports
from qtpy.QtGui import QTextCursor
import pytest

# Local imports
from spyder.utils.qthelpers import qapplication
from spyder.plugins.editor.widgets.codeeditor import CodeEditor
from spyder.plugins.editor.panels.linenumber import LineNumberArea
from spyder.plugins.editor.panels.edgeline import EdgeLine
from spyder.plugins.editor.panels.scrollflag import ScrollFlagArea
from spyder.plugins.editor.panels.indentationguides import IndentationGuide


# --- Fixtures
# -----------------------------------------------------------------------------
def construct_editor(*args, **kwargs):
    app = qapplication()
    editor = CodeEditor(parent=None)
    kwargs['language'] = 'Python'
    editor.setup_editor(*args, **kwargs)
    return editor


# --- Tests
# -----------------------------------------------------------------------------
@pytest.mark.parametrize('state', [True, False])
@pytest.mark.parametrize('setting, panelclass', [
    ('linenumbers', LineNumberArea),
    ('edge_line', EdgeLine),
    ('scrollflagarea', ScrollFlagArea),
    ('indent_guides', IndentationGuide),
])
def test_activate_panels(setting, panelclass, state):
    """Test activate/deactivate of editors Panels.

    Also test that the panel is added to the editor.
    """
    kwargs = {}
    kwargs[setting] = state
    editor = construct_editor(**kwargs)

    found = False
    for panel in editor.panels:
        if isinstance(panel, panelclass):
            assert panel.enabled == state
            found = True
    assert found


if __name__ == '__main__':
    pytest.main()
