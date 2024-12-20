# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2013-2016 Colin Duquesnoy and others (see pyqode/AUTHORS.rst)
# Copyright (c) 2016- Spyder Project Contributors (see AUTHORS.txt)
#
# Distributed under the terms of the MIT License
# (see NOTICE.txt in the Spyder root directory for details)
# -----------------------------------------------------------------------------

"""
This module contains the marker panel.

Adapted from pyqode/core/panels/folding.py of the PyQode project
https://github.com/pyQode/pyQode

Original file:
https://github.com/pyQode/pyqode.core/blob/master/pyqode/core/panels/folding.py
"""

# Standard library imports
from math import ceil

# Third party imports
from intervaltree import IntervalTree
from qtpy.QtCore import Signal, QSize, QPointF, QRectF, QRect, Qt
from qtpy.QtGui import (QTextBlock, QFontMetricsF, QPainter, QLinearGradient,
                        QPen, QResizeEvent, QCursor, QTextCursor)
from qtpy.QtWidgets import QApplication

# Local imports
from spyder.plugins.editor.api.panel import Panel
from spyder.config.gui import is_dark_interface
from spyder.plugins.editor.api.decoration import TextDecoration, DRAW_ORDERS
from spyder.plugins.editor.panels.utils import FoldingRegion
from spyder.plugins.editor.utils.editor import (TextHelper, DelayJobRunner,
                                                drift_color)
from spyder.utils.icon_manager import ima
from spyder.widgets.mixins import EOL_SYMBOLS


class FoldingPanel(Panel):

    """
    Displays the document outline and lets the user collapse/expand blocks.

    The data represented by the panel come from the Language Server Protocol
    invoked via the CodeEditor. This panel stores information about both
    folding regions and their folding state.
    """
    #: signal emitted when a fold trigger state has changed, parameters are
    #: the concerned text block and the new state (collapsed or not).
    trigger_state_changed = Signal(QTextBlock, bool)
    collapse_all_triggered = Signal()
    expand_all_triggered = Signal()

    def __init__(self):
        Panel.__init__(self)

        self.collapsed_icon = ima.icon('folding.arrow_right')
        self.uncollapsed_icon = ima.icon('folding.arrow_down')

        self._block_nbr = -1
        self._highlight_caret = False
        self.highlight_caret_scope = False

        #: the list of deco used to highlight the current fold region (
        #: surrounding regions are darker)
        self._scope_decos = []

        #: the list of folded block decorations
        self._block_decos = {}

        self.setMouseTracking(True)
        self.scrollable = True
        self._mouse_over_line = None
        self._current_scope = None
        self._display_folding = False
        self._key_pressed = False
        self._highlight_runner = DelayJobRunner(delay=250)
        self.current_tree = IntervalTree()
        self.root = FoldingRegion(None, None)
        self.folding_regions = {}
        self.folding_status = {}
        self.folding_levels = {}
        self.folding_nesting = {}

    @property
    def highlight_caret_scope(self):
        """
        True to highlight the caret scope automatically.

        (Similar to the ``Highlight blocks in Qt Creator``.

        Default is False.
        """
        return self._highlight_caret

    @highlight_caret_scope.setter
    def highlight_caret_scope(self, value):
        if value != self._highlight_caret:
            self._highlight_caret = value
            if self.editor:
                if value:
                    self._block_nbr = -1
                    self.editor.cursorPositionChanged.connect(
                        self._highlight_caret_scope)
                else:
                    self._block_nbr = -1
                    self.editor.cursorPositionChanged.disconnect(
                        self._highlight_caret_scope)
                for clone in self.editor.clones:
                    try:
                        clone.modes.get(
                            self.__class__).highlight_caret_scope = value
                    except KeyError:
                        # this should never happen since we're working with
                        # clones
                        pass

    def update_folding(self, folding_info):
        """Update folding panel folding ranges."""
        if folding_info is None:
            return

        (self.current_tree, self.root,
         self.folding_regions, self.folding_nesting,
         self.folding_levels, self.folding_status) = folding_info

        self._clear_block_decos()
        self.update()

    def sizeHint(self):
        """Returns the widget size hint (based on the editor font size) """
        fm = QFontMetricsF(self.editor.font())
        size_hint = QSize(ceil(fm.height()), ceil(fm.height()))
        if size_hint.width() > 16:
            size_hint.setWidth(16)
        return size_hint

    def _draw_collapsed_indicator(self, line_number, top_position, block,
                                  painter, mouse_hover=False):
        if line_number in self.folding_regions:
            collapsed = self.folding_status[line_number]

            if not mouse_hover:
                self._draw_fold_indicator(top_position, collapsed, painter)

            if collapsed:
                if mouse_hover:
                    self._draw_fold_indicator(top_position, collapsed, painter)
            elif not mouse_hover:
                for deco_line in list(self._block_decos.keys()):
                    deco = self._block_decos[deco_line]

                    # Check if the block decoration has been removed, it
                    # might have been unfolded by the parent
                    # editor/document in the case of cloned editor
                    if deco.block == block:
                        # remove it and
                        self._block_decos.pop(deco_line)
                        self.editor.decorations.remove(deco, key='folded')
                        del deco
                        break

    def highlight_folded_regions(self):
        """Highlight folded regions on the editor's visible buffer."""
        first_block_nb, last_block_nb = self.editor.get_buffer_block_numbers()

        # This can happen at startup, and when it does, we don't need to move
        # pass this point.
        if first_block_nb == last_block_nb:
            return

        for block_number in range(first_block_nb, last_block_nb):
            block = self.editor.document().findBlockByNumber(block_number)
            line_number = block_number + 1

            if line_number in self.folding_regions:
                collapsed = self.folding_status[line_number]

                # Check if a block is folded by UI inspection.
                # This is necesary because the algorithm that detects the
                # currently folded regions may fail, for instance, after
                # pasting a big chunk of code.
                ui_collapsed = (
                    block.isVisible() and not block.next().isVisible()
                )

                if collapsed != ui_collapsed:
                    collapsed = ui_collapsed
                    self.folding_status[line_number] = ui_collapsed

                if collapsed:
                    # Check if the block already has a decoration,
                    # it might have been folded by the parent
                    # editor/document in the case of cloned editor
                    for deco_line in self._block_decos:
                        deco = self._block_decos[deco_line]
                        if deco.block == block:
                            # no need to add a deco, just go to the
                            # next block
                            break
                    else:
                        line_end = self.folding_regions[line_number]
                        self._add_fold_decoration(block, line_end)

    def paintEvent(self, event):
        """
        Paint fold indicators on the folding panel and possible folding region
        background on the editor.
        """
        super().paintEvent(event)
        painter = QPainter(self)
        self.paint_cell(painter)

        # Draw collapsed indicators
        if not self._display_folding and not self._key_pressed:
            for top_position, line_number, block in self.editor.visible_blocks:
                if self.folding_status.get(line_number):
                    self._draw_collapsed_indicator(
                        line_number, top_position, block,
                        painter, mouse_hover=True)
            return

        # Draw background over the selected non collapsed fold region
        if self._mouse_over_line is not None:
            block = self.editor.document().findBlockByNumber(
                self._mouse_over_line)
            try:
                self._draw_fold_region_background(block, painter)
            except (ValueError, KeyError):
                # Catching the KeyError above is necessary to avoid
                # issue spyder-ide/spyder#10918.
                # It happens when users have the mouse on top of the
                # folding panel and make some text modifications
                # that trigger a folding recomputation.
                pass

        # Draw all fold indicators
        for top_position, line_number, block in self.editor.visible_blocks:
            self._draw_collapsed_indicator(
                line_number, top_position, block, painter, mouse_hover=False)

    def _draw_fold_region_background(self, block, painter):
        """
        Draw the fold region when the mouse is over and non collapsed
        indicator.

        :param top: Top position
        :param block: Current block.
        :param painter: QPainter
        """
        th = TextHelper(self.editor)
        start = block.blockNumber()
        end = self.folding_regions[start]
        if start > 0:
            top = th.line_pos_from_number(start)
        else:
            top = 0
        bottom = th.line_pos_from_number(end)
        h = bottom - top
        if h == 0:
            h = self.sizeHint().height()
        w = self.sizeHint().width()
        self._draw_rect(QRectF(0, top, w, h), painter)

    def _draw_rect(self, rect, painter):
        """
        Draw the background rectangle using the current style primitive color.

        :param rect: The fold zone rect to draw

        :param painter: The widget's painter.
        """
        c = self.editor.sideareas_color
        grad = QLinearGradient(rect.topLeft(), rect.topRight())

        if is_dark_interface():
            grad.setColorAt(0, c.lighter(110))
            grad.setColorAt(1, c.lighter(130))
            outline = c.darker(100)
        else:
            grad.setColorAt(0, c.darker(105))
            grad.setColorAt(1, c.darker(115))
            outline = c.lighter(110)

        painter.fillRect(rect, grad)
        painter.setPen(QPen(outline))
        painter.drawLine(rect.topLeft() +
                         QPointF(1, 0),
                         rect.topRight() -
                         QPointF(1, 0))
        painter.drawLine(rect.bottomLeft() +
                         QPointF(1, 0),
                         rect.bottomRight() -
                         QPointF(1, 0))
        painter.drawLine(rect.topRight() +
                         QPointF(0, 1),
                         rect.bottomRight() -
                         QPointF(0, 1))
        painter.drawLine(rect.topLeft() +
                         QPointF(0, 1),
                         rect.bottomLeft() -
                         QPointF(0, 1))

    def _draw_fold_indicator(self, top, collapsed, painter):
        """
        Draw the fold indicator/trigger (arrow).

        :param top: Top position
        :param collapsed: Whether the trigger is collapsed or not.
        :param painter: QPainter
        """
        rect = QRect(
            0, top, self.sizeHint().width() + 2, self.sizeHint().height() + 2
        )

        if collapsed:
            icon = self.collapsed_icon
        else:
            icon = self.uncollapsed_icon

        icon.paint(painter, rect)

    def find_parent_scope(self, block):
        """Find parent scope, if the block is not a fold trigger."""
        block_line = block.blockNumber()
        if block_line not in self.folding_regions:
            for start_line in self.folding_regions:
                end_line = self.folding_regions[start_line]
                if end_line > block_line:
                    if start_line < block_line:
                        block = self.editor.document().findBlockByNumber(
                            start_line)
                        break
        return block

    def _clear_scope_decos(self):
        """Clear scope decorations (on the editor)"""
        for deco in self._scope_decos:
            self.editor.decorations.remove(deco)
        self._scope_decos[:] = []

    def _get_scope_highlight_color(self):
        """
        Gets the base scope highlight color (derivated from the editor
        background)

        For lighter themes will be a darker color,
        and for darker ones will be a lighter color
        """
        color = self.editor.sideareas_color

        if is_dark_interface():
            color = drift_color(color, 130)
        else:
            color = drift_color(color, 105)

        return color

    def _decorate_block(self, start, end):
        """
        Create a decoration and add it to the editor.

        Args:
            start (int) start line of the decoration
            end (int) end line of the decoration
        """
        color = self._get_scope_highlight_color()
        draw_order = DRAW_ORDERS.get('folding_areas')
        d = TextDecoration(self.editor.document(),
                           start_line=max(0, start - 1),
                           end_line=end,
                           draw_order=draw_order)
        d.set_background(color)
        d.set_full_width(True, clear=False)
        self.editor.decorations.add(d)
        self._scope_decos.append(d)

    def _highlight_block(self, block):
        """
        Highlights the current fold scope.

        :param block: Block that starts the current fold scope.
        """
        block_line = block.blockNumber()
        end_line = self.folding_regions[block_line]

        scope = (block_line, end_line)
        if (self._current_scope is None or self._current_scope != scope):
            self._current_scope = scope
            self._clear_scope_decos()
            # highlight current scope with darker or lighter color
            start, end = scope
            if not self.folding_status[start]:
                self._decorate_block(start, end)

    def mouseMoveEvent(self, event):
        """
        Detect mouser over indicator and highlight the current scope in the
        editor (up and down decoration arround the foldable text when the mouse
        is over an indicator).

        :param event: event
        """
        super(FoldingPanel, self).mouseMoveEvent(event)
        th = TextHelper(self.editor)
        line = th.line_nbr_from_position(event.pos().y())

        if line >= 0:
            block = self.editor.document().findBlockByNumber(line)
            block = self.find_parent_scope(block)
            line_number = block.blockNumber()

            if line_number in self.folding_regions:
                if self._mouse_over_line is None:
                    # mouse enter fold scope
                    QApplication.setOverrideCursor(
                        QCursor(Qt.PointingHandCursor))
                if (self._mouse_over_line != block.blockNumber() and
                        self._mouse_over_line is not None):
                    # fold scope changed, a previous block was highlighter so
                    # we quickly update our highlighting
                    self._mouse_over_line = block.blockNumber()
                    try:
                        self._highlight_block(block)
                    except KeyError:
                        # Catching the KeyError above is necessary to avoid
                        # issue spyder-ide/spyder#13230.
                        pass
                else:
                    # same fold scope, request highlight
                    self._mouse_over_line = block.blockNumber()
                    try:
                        self._highlight_runner.request_job(
                            self._highlight_block, block)
                    except KeyError:
                        # Catching the KeyError above is necessary to avoid
                        # issue spyder-ide/spyder#11291.
                        pass
                self._highight_block = block
            else:
                # no fold scope to highlight, cancel any pending requests
                self._highlight_runner.cancel_requests()
                self._mouse_over_line = None
                QApplication.restoreOverrideCursor()

            self.repaint()

    def enterEvent(self, event):
        self._display_folding = True
        self.repaint()

    def leaveEvent(self, event):
        """
        Removes scope decorations and background from the editor and the panel
        if highlight_caret_scope, else simply update the scope decorations to
        match the caret scope.
        """
        super(FoldingPanel, self).leaveEvent(event)
        QApplication.restoreOverrideCursor()
        self._highlight_runner.cancel_requests()
        if not self.highlight_caret_scope:
            self._clear_scope_decos()
            self._mouse_over_line = None
            self._current_scope = None
        else:
            self._block_nbr = -1
            self._highlight_caret_scope()
        self.editor.repaint()
        self._display_folding = False

    def _add_fold_decoration(self, block, end_line):
        """
        Add fold decorations (boxes arround a folded block in the editor
        widget).
        """
        start_line = block.blockNumber()
        text = self.editor.get_text_region(start_line + 1, end_line)
        draw_order = DRAW_ORDERS.get('folded_regions')

        deco = TextDecoration(block, draw_order=draw_order)
        deco.signals.clicked.connect(self._on_fold_deco_clicked)
        deco.tooltip = text
        deco.block = block
        deco.select_line()
        deco.set_background(self._get_scope_highlight_color())
        deco.set_full_width(flag=True, clear=True)
        self._block_decos[start_line] = deco
        self.editor.decorations.add(deco, key='folded')

    def _get_block_until_line(self, block, end_line):
        while block.blockNumber() <= end_line and block.isValid():
            block.setVisible(False)
            block = block.next()
        return block

    def fold_region(self, block, start_line, end_line):
        """Fold region spanned by `start_line` and `end_line`."""
        # Note: The block passed to this method is the first one that needs to
        # be hidden.
        initial_block = self.editor.document().findBlockByNumber(
            start_line - 1)
        self._add_fold_decoration(initial_block, end_line)

        while block.blockNumber() < end_line and block.isValid():
            block.setVisible(False)
            block = block.next()

    def unfold_region(self, block, start_line, end_line):
        """Unfold region spanned by `start_line` and `end_line`."""
        if start_line - 1 in self._block_decos:
            deco = self._block_decos[start_line - 1]
            self._block_decos.pop(start_line - 1)
            self.editor.decorations.remove(deco, key='folded')

        while block.blockNumber() < end_line and block.isValid():
            current_line = block.blockNumber()
            block.setVisible(True)
            get_next = True

            if (
                current_line in self.folding_regions
                and current_line != start_line
            ):
                block_end = self.folding_regions[current_line]
                if self.folding_status[current_line]:
                    # Skip setting visible blocks until the block is done
                    get_next = False
                    block = self._get_block_until_line(block, block_end - 1)

            if get_next:
                block = block.next()

    def toggle_fold_trigger(self, block):
        """
        Toggle a fold trigger block (expand or collapse it).

        :param block: The QTextBlock to expand/collapse
        """
        start_line = block.blockNumber()

        if start_line not in self.folding_regions:
            return

        end_line = self.folding_regions[start_line]
        if self.folding_status[start_line]:
            self.unfold_region(block, start_line, end_line)
            self.folding_status[start_line] = False
            if self._mouse_over_line is not None:
                self._decorate_block(start_line, end_line)
        else:
            self.fold_region(block, start_line, end_line)
            self.folding_status[start_line] = True
            self._clear_scope_decos()

        self._refresh_editor_and_scrollbars()

    def mousePressEvent(self, event):
        """Folds/unfolds the pressed indicator if any."""
        if self._mouse_over_line is not None:
            block = self.editor.document().findBlockByNumber(
                self._mouse_over_line)
            self.toggle_fold_trigger(block)

    def _on_fold_deco_clicked(self, deco):
        """Unfold a folded block that has just been clicked by the user"""
        self.toggle_fold_trigger(deco.block)

    def on_state_changed(self, state):
        """
        On state changed we (dis)connect to the cursorPositionChanged signal
        """
        if state:
            self.editor.sig_key_pressed.connect(self._on_key_pressed)
            self.editor.sig_delete_requested.connect(self._expand_selection)

            if self._highlight_caret:
                self.editor.cursorPositionChanged.connect(
                    self._highlight_caret_scope)
                self._block_nbr = -1

            self.editor.new_text_set.connect(self._clear_block_decos)
        else:

            self.editor.sig_key_pressed.disconnect(self._on_key_pressed)
            self.editor.sig_delete_requested.disconnect(self._expand_selection)

            if self._highlight_caret:
                self.editor.cursorPositionChanged.disconnect(
                    self._highlight_caret_scope)
                self._block_nbr = -1

            self.editor.new_text_set.disconnect(self._clear_block_decos)

    def _in_folded_block(self):
        """Check if the current block is folded."""
        cursor = self.editor.textCursor()

        if cursor.hasSelection():
            block_start = self.editor.document().findBlock(
                cursor.selectionStart()
            )
            block_end = self.editor.document().findBlock(cursor.selectionEnd())

            if (
                # The start block needs to be among the folded ones.
                block_start.blockNumber() in self._block_decos
                # This covers the case when there's some text selected in the
                # folded line or when it's selected in its entirety. For the
                # latter, Qt returns the next block as the final one, which
                # is not visible.
                and (block_start == block_end or not block_end.isVisible())
            ):
                return True
            else:
                return False
        else:
            current_block = self.editor.document().findBlock(cursor.position())
            return current_block.blockNumber() in self._block_decos

    def _on_key_pressed(self, event):
        """
        Handle key press events in order to select a whole folded scope if the
        user wants to remove it.

        Notes
        -----
        We don't handle Key_Delete here because it's behind a shortcut in
        CodeEditor. So, the event associated to that key doesn't go through its
        keyPressEvent.

        Instead, CodeEditor emits sig_delete_requested in the method that gets
        called when Key_Delete is pressed, and in several other places, which
        is handled by _expand_selection below.
        """
        # This doesn't apply if there are not folded regions
        if not self._block_decos:
            return

        if self._in_folded_block():
            # We prevent the following events to change folded blocks to make
            # them appear as read-only to users.
            # See the last comments in spyder-ide/spyder#21669 for the details
            # of this decision.
            if (
                # When Tab or Shift+Tab are pressed
                event.key() in [Qt.Key_Tab, Qt.Key_Backtab]
                # When text is trying to be written
                or event.text() and event.key() != Qt.Key_Backspace
            ):
                event.accept()
                return

        delete_pressed = event.key() == Qt.Key_Backspace

        enter_pressed = False
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            if event.key() == Qt.Key_Return:
                enter_pressed = True

        # Delete a folded scope when pressing delete or enter
        if delete_pressed or enter_pressed:
            self._expand_selection()

    def _expand_selection(self):
        """
        Expand selection to encompass a whole folded scope in case the
        current selection starts and/or ends in one, or the cursor is over a
        block deco.
        """
        if not self._block_decos:
            return

        cursor = self.editor.textCursor()
        self._key_pressed = True

        # If there's no selected text, select the current line but only if
        # it corresponds to a block deco. That allows us to remove the folded
        # region associated to it when typing Delete or Backspace on the line.
        # Otherwise, the editor ends up in an inconsistent state.
        if not cursor.hasSelection():
            current_block = self.editor.document().findBlock(cursor.position())

            if current_block.blockNumber() in self._block_decos:
                cursor.select(QTextCursor.LineUnderCursor)
            else:
                self._key_pressed = False
                return

        # Get positions to check if we need to expand the current selection to
        # cover a folded region too.
        start_pos = cursor.selectionStart()
        end_pos = cursor.selectionEnd()

        # A selection can end in an eol when calling CodeEditor.delete_line,
        # for instance. In that case, we need to remove it for the code below
        # to work as expected.
        if cursor.selectedText()[-1] in EOL_SYMBOLS:
            end_pos -= 1

        positions_to_check = (start_pos, end_pos)
        for pos in positions_to_check:
            block = self.editor.document().findBlock(pos)
            start_line = block.blockNumber() + 1

            if (
                start_line in self.folding_regions
                and self.folding_status[start_line]
            ):
                end_line = self.folding_regions[start_line]

                if cursor.hasSelection():
                    tc = TextHelper(self.editor).select_lines(
                        start_line, end_line)
                    tc.movePosition(tc.MoveOperation.NextBlock,
                                    tc.MoveMode.KeepAnchor)

                    if tc.selectionStart() > cursor.selectionStart():
                        start = cursor.selectionStart()
                    else:
                        start = tc.selectionStart()

                    if tc.selectionEnd() < cursor.selectionEnd():
                        end = cursor.selectionEnd()
                    else:
                        end = tc.selectionEnd()

                    tc.setPosition(start)
                    tc.setPosition(end, tc.KeepAnchor)

                    self.editor.setTextCursor(tc)

        self._update_block_decos(start_pos, end_pos)
        self._key_pressed = False

    def _refresh_editor_and_scrollbars(self):
        """
        Refrehes editor content and scollbars.

        We generate a fake resize event to refresh scroll bar.

        We have the same problem as described here:
        http://www.qtcentre.org/threads/44803 and we apply the same solution
        (don't worry, there is no visual effect, the editor does not grow up
        at all, even with a value = 500)
        """
        TextHelper(self.editor).mark_whole_doc_dirty()
        self.editor.repaint()
        s = self.editor.size()
        s.setWidth(s.width() + 1)
        self.editor.resizeEvent(QResizeEvent(self.editor.size(), s))

    def collapse_all(self):
        """
        Collapses all triggers and makes all blocks with fold level > 0
        invisible.
        """
        self._clear_block_decos()
        block = self.editor.document().firstBlock()
        while block.isValid():
            line_number = block.blockNumber()
            if line_number in self.folding_regions:
                end_line = self.folding_regions[line_number]
                self.fold_region(block, line_number, end_line)
            block = block.next()
        self._refresh_editor_and_scrollbars()
        tc = self.editor.textCursor()
        tc.movePosition(tc.Start)
        self.editor.setTextCursor(tc)
        self.collapse_all_triggered.emit()

    def _clear_block_decos(self):
        """Clear the folded block decorations."""
        self.editor.decorations.remove_key('folded')
        self._block_decos = {}

    def _update_block_decos(self, start_pos, end_pos):
        """
        Update block decorations in case some are going to be removed by the
        user.

        Parameters
        ----------
        start_pos: int
            Start cursor position of the selection that's going to remove or
            replace text in the editor
        end_pos: int
            End cursor position of the same selection.
        """
        start_line = self.editor.document().findBlock(start_pos).blockNumber()
        end_line = self.editor.document().findBlock(end_pos).blockNumber()

        for deco_line in self._block_decos.copy():
            if start_line <= deco_line <= end_line:
                deco = self._block_decos[deco_line]
                self._block_decos.pop(deco_line)
                self.editor.decorations.remove(deco, key='folded')
                self.folding_status[deco_line + 1] = False

    def expand_all(self):
        """Expands all fold triggers."""
        block = self.editor.document().firstBlock()
        while block.isValid():
            line_number = block.blockNumber()
            if line_number in self.folding_regions:
                end_line = self.folding_regions[line_number]
                self.unfold_region(block, line_number, end_line)
            block = block.next()
        self._clear_block_decos()
        self._refresh_editor_and_scrollbars()
        self.expand_all_triggered.emit()

    def _highlight_caret_scope(self):
        """
        Highlight the scope of the current caret position.

        This get called only if :attr:`
        spyder.widgets.panels.FoldingPanel.highlight_care_scope` is True.
        """
        cursor = self.editor.textCursor()
        block_nbr = cursor.blockNumber()
        if self._block_nbr != block_nbr:
            block = self.find_parent_scope(cursor.block())
            line_number = block.blockNumber()
            if line_number in self.folding_regions:
                self._mouse_over_line = block.blockNumber()
                try:
                    self._highlight_block(block)
                except KeyError:
                    # Catching the KeyError above is necessary to avoid
                    # issue spyder-ide/spyder#13230.
                    pass
            else:
                self._clear_scope_decos()
        self._block_nbr = block_nbr
