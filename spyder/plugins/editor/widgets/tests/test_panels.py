# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#
'''
Tests for editor panels.
'''

# Third party imports
from qtpy.QtCore import QSize, Qt
from qtpy.QtGui import QTextCursor, QPainter, QColor, QFontMetrics
import pytest

# Local imports
from spyder.api.panel import Panel
from spyder.utils.qthelpers import qapplication
from spyder.plugins.editor.panels.linenumber import LineNumberArea
from spyder.plugins.editor.panels.edgeline import EdgeLine
from spyder.plugins.editor.panels.scrollflag import ScrollFlagArea
from spyder.plugins.editor.panels.indentationguides import IndentationGuide
from spyder.plugins.editor.widgets.codeeditor import CodeEditor


# --- External Example Panel
# -----------------------------------------------------------------------------
class EmojiPanel(Panel):
    """Example external panel."""

    def __init__(self):
        """Initialize panel."""
        Panel.__init__(self)
        self.setMouseTracking(True)
        self.scrollable = True

    def sizeHint(self):
        """Override Qt method.
        Returns the widget size hint (based on the editor font size).
        """
        fm = QFontMetrics(self.editor.font())
        size_hint = QSize(fm.height(), fm.height())
        if size_hint.width() > 16:
            size_hint.setWidth(16)
        return size_hint

    def _draw_red(self, top, painter):
        """Draw emojis.

        Arguments
        ---------
        top: int
            top of the line to draw the emoji
        painter: QPainter
            QPainter instance
        """
        painter.setPen(QColor('white'))
        font_height = self.editor.fontMetrics().height()
        painter.drawText(0, top, self.sizeHint().width(),
                         font_height, int(Qt.AlignRight | Qt.AlignBottom),
                         '👀')

    def paintEvent(self, event):
        """Override Qt method.
        Paint emojis.
        """
        super(EmojiPanel, self).paintEvent(event)
        painter = QPainter(self)
        painter.fillRect(event.rect(), self.editor.sideareas_color)
        for top, __, __ in self.editor.visible_blocks:
            self._draw_red(top, painter)


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


@pytest.mark.parametrize('position', [
    Panel.Position.LEFT, Panel.Position.RIGHT, Panel.Position.TOP,
    Panel.Position.BOTTOM, Panel.Position.FLOATING])
def test_register_panel(setup_editor, position):
    """Test registering an example external panel in the editor."""
    editor_stack, editor = setup_editor

    # Register the panel
    editor_stack.register_panel(EmojiPanel, position=position)

    # Verify the panel is added in the panel manager
    new_panel = editor.panels.get(EmojiPanel)
    assert new_panel is not None

    # Verify the panel is in the editorstack
    assert (EmojiPanel, (), {}, position) in editor_stack.external_panels

    # Verify that the panel is shown in new files
    finfo = editor_stack.new('foo.py', 'utf-8', 'hola = 3\n')
    editor2 = finfo.editor

    new_panel = editor2.panels.get(EmojiPanel)
    assert new_panel is not None

    # Remove external panel
    editor_stack.external_panels = []
    editor.panels.remove(EmojiPanel)
    editor2.panels.remove(EmojiPanel)


if __name__ == '__main__':
    pytest.main()
