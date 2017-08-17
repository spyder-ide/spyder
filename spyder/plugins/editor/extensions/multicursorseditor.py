# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""This module contains the multicursors editing extension."""

# Standard library imports
import copy

# Third party imports
from qtpy.QtCore import Qt, QTimerEvent, QTimer
from qtpy.QtGui import QColor, QTextCursor, QPainter, QTextLayout
from qtpy.QtWidgets import QApplication

# Local imports
from spyder.py3compat import to_text_string

from spyder.api.editorextension import EditorExtension


class MultiCursorsEditorExtension(EditorExtension):
    """Multicursors Editor Extension."""

    def __init__(self):
        super(MultiCursorsEditorExtension, self).__init__()
        self._cursors = []
        self._master_cursor = None
        self._multi_cursor_state = None

    def on_install(self, editor):
        super(MultiCursorsEditorExtension, self).on_install(editor)
        editor.sig_key_pressed.connect(self._on_key_pressed)
        editor.sig_mouse_pressed.connect(self._on_mouse_pressed)
        editor.sig_about_to_be_painted.connect(self._on_editor_paint_event)

        self.blinktimer = QTimer(self)
        self.blinktimer.timeout.connect(self._on_blinktimer_timeout)

        # QApplication.instance().installEventFilter(self)

    # ---- Cursors handlers
    def editorCursor(self):
        return self._editor.textCursor()

    def cursors(self):
        return self._cursors

    def add_cursor(self, cursor):
        self._cursors.append(cursor)
        cursor.clipboard = ""
        if self._master_cursor is None:
            self._master_cursor = self.editorCursor()
            self._master_cursor.clipboard = ""
        self.start_blinking_timer()
        self._editor.viewport().update()

    def clear_cursors(self):
        self._cursors = []
        if self._master_cursor is not None:
            self._editor.setTextCursor(self._master_cursor)
            self._master_cursor = None
        self.stop_blinking_timer()
        self._editor.viewport().update()

    # ---- Timers
    # def eventFilter(self, widget, event):
    #     if widget == self.blinktimer:
    #         return False
    #     if self.cursors() and type(event) == QTimerEvent:
    #         return True
    #     else:
    #         return False

    def _on_blinktimer_timeout(self):
        self._multi_cursor_state = not self._multi_cursor_state
        if self._editor.isVisible():
            self._editor.viewport().update()

    def cursor_flash_time(self):
        return QApplication.cursorFlashTime()/2

    def stop_blinking_timer(self):
        self.blinktimer.stop()

    def start_blinking_timer(self):
        self._multi_cursor_state = True
        if self.cursor_flash_time() > 0:
            self.blinktimer.start(self.cursor_flash_time())

    # ---- Event handlers
    def _on_mouse_pressed(self, event):
        if event.isAccepted():
            return

        if event.button() not in [1, 2]:
            self.add_cursor(self._editor.cursorForPosition(event.pos()))
            event.accept()
        else:
            self.clear_cursors()
            event.ignore()

    def _on_key_pressed(self, event):
        """Handle when a key press event is registered by the editor."""
        if event.isAccepted():
            return
        else:
            event.accept()

        ctrl = bool(Qt.ControlModifier & event.modifiers())
        shift = bool(Qt.ShiftModifier & event.modifiers())
        text = to_text_string(event.text())

        # Cancel multicursors editing mode
        if event.key() == Qt.Key_Escape:
            self.clear_cursors()
        if not self.cursors():
            event.ignore()
            return

        cursors = self.cursors() + [self._master_cursor]
        # Reset the timer for the cursor blinking state
        self.start_blinking_timer()

        if ctrl or (ctrl and shift):
            self.editorCursor().beginEditBlock()
            if event.key() == Qt.Key_Z:
                event.ignore()
            elif event.key() == Qt.Key_X:
                for cursor in cursors:
                    cursor.clipboard = cursor.selectedText()
                    cursor.removeSelectedText()
            elif event.key() == Qt.Key_C:
                for cursor in cursors:
                    cursor.clipboard = cursor.selectedText()
            elif event.key() == Qt.Key_V:
                for cursor in cursors:
                    cursor.insertText(cursor.clipboard)
            self.editorCursor().endEditBlock()
            return

        if shift:
            mode = QTextCursor.KeepAnchor
        else:
            mode = QTextCursor.MoveAnchor

        self.editorCursor().beginEditBlock()
        # ---- Move ----
        if event.key() == Qt.Key_Left:
            for cursor in cursors:
                cursor.movePosition(QTextCursor.Left, mode)
        elif event.key() == Qt.Key_Right:
            for cursor in cursors:
                cursor.movePosition(QTextCursor.Right, mode)
        elif event.key() == Qt.Key_Down:
            for cursor in cursors:
                cursor.movePosition(QTextCursor.Down, mode)
        elif event.key() == Qt.Key_Up:
            for cursor in cursors:
                cursor.movePosition(QTextCursor.Up, mode)
        elif event.key() == Qt.Key_Home:
            for cursor in cursors:
                cursor.movePosition(QTextCursor.StartOfBlock, mode)
        elif event.key() == Qt.Key_End:
            for cursor in cursors:
                cursor.movePosition(QTextCursor.EndOfBlock, mode)
        # elif event.key() == Qt.Key_Return:
        #     for cursor in cursors:
        #         cursor.insertText(os.linesep)
        elif event.key() == Qt.Key_Backspace:
            for cursor in cursors:
                cursor.deletePreviousChar()
        elif event.key() == Qt.Key_Delete:
            for cursor in cursors:
                cursor.deleteChar()
        else:
            if text:
                for cursor in cursors:
                    cursor.insertText(event.text())
        self.editorCursor().endEditBlock()
        self._editor.viewport().update()

    def _on_editor_paint_event(self, event):
        if not self.cursors():
            event.ignore()
            return
        else:
            event.accept()

        self._editor.update_visible_blocks(event)

        er = event.rect()
        viewportRect = self._editor.viewport().rect()

        qp = QPainter()
        qp.begin(self._editor.viewport())

        offset = self._editor.contentOffset()
        editable = not self._editor.isReadOnly()

        block = self._editor.firstVisibleBlock()
        doc = self._editor.document()
        max_width = doc.documentLayout().documentSize().width()

        # Set a brush origin so that the WaveUnderline knows where the
        # wave started
        qp.setBrushOrigin(offset)

        # keep right margin clean from full-width selection
        maxX = (offset.x() +
                max(viewportRect.width(), max_width) -
                doc.documentMargin()
                )
        er.setRight(min(er.right(), maxX))

        while block.isValid():
            r = self._editor.blockBoundingRect(block).translated(offset)
            layout = block.layout()

            if not block.isVisible():
                offset.setY(offset.y() + r.height())
                block = block.next()
                continue

            if (r.bottom() >= er.top() and r.top() <= er.bottom()):
                blockFormat = block.blockFormat()
                bg = blockFormat.background()
                if (bg != Qt.NoBrush):
                    contentsRect = copy.copy(r)
                    contentsRect.setWidth(max(r.width(), max_width))
                    self.fillBackground(qp, contentsRect, bg)

            # ---- selections

            blpos = block.position()
            bllen = block.length()

            selections = []
            for cursor in self.cursors() + [self._master_cursor]:
                if (not cursor.hasSelection() or
                        not block.contains(cursor.position())):
                    continue
                selStart = cursor.selectionStart() - blpos
                selEnd = cursor.selectionEnd() - blpos
                if (selStart < bllen and selEnd > 0
                        and selEnd > selStart):
                    o = QTextLayout.FormatRange()
                    o.start = selStart
                    o.length = selEnd - selStart
                    o.format.setBackground(QColor(Qt.green))
                    selections.append(o)

            # ---- draw block

            if selections:
                layout.draw(qp, offset, selections=selections)
            else:
                layout.draw(qp, offset)

            # ---- draw cursors

            for cursor in self.cursors() + [self._master_cursor]:
                cursor_pos = cursor.position()
                drawCursor = (self.drawCursor(cursor_pos, block) and
                              self._multi_cursor_state)
                drawCursorAsBlock = False
                if ((drawCursor and not drawCursorAsBlock)
                        or (editable and cursor_pos < -1
                            and not layout.preeditAreaText().isEmpty())):
                    cpos = cursor_pos
                    if (cpos < -1):
                        cpos = layout.preeditAreaPosition() - (cpos + 2)
                    else:
                        cpos -= blpos
                    layout.drawCursor(qp, offset, cpos,
                                      self._editor.cursorWidth())

            offset.setY(offset.y() + r.height())
            if (offset.y() > viewportRect.height()):
                break
            block = block.next()

#        vmax = self.verticalScrollBar().maximum()
#        vmin = self.verticalScrollBar().minimum()
#        if (self.backgroundVisible() and not
#            block.isValid() and
#            offset.y() <= er.bottom() and
#            (self.centerOnScroll() or vmax == vmin)):
#        painter.fillRect(QRect(QPoint((int)er.left(),
#                                      (int)offset.y()),
#                               er.bottomRight()),
#                         palette().background())

        qp.end()
        self._editor.painted.emit(event)

    def fillBackground(self, qp, contentsRect, bg):
        qp.save()
        qp.setBrushOrigin(contentsRect.topLeft())
        qp.fillRect(contentsRect, bg)
        qp.restore()

    def drawCursor(self, cursor_pos, block):
        editable = not self._editor.isReadOnly()
        flags = (self._editor.textInteractionFlags() and
                 Qt.TextSelectableByKeyboard)
        blpos = block.position()
        bllen = block.length()

        return ((editable or flags)
                and cursor_pos >= blpos
                and cursor_pos < blpos + bllen
                )
