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

Adapted from pyqode/core/panels/folding.py of the
`PyQode project <https://github.com/pyQode/pyQode>`_.
Original file:
<https://github.com/pyQode/pyqode.core/blob/master/pyqode/core/panels/folding.py>
"""

# Standard library imports
import sys

# Third party imports
from qtpy.QtCore import Signal, QSize, QPointF, QRectF, QRect, Qt
from qtpy.QtWidgets import QApplication, QStyleOptionViewItem, QStyle
from qtpy.QtGui import (QTextBlock, QColor, QFontMetricsF, QPainter,
                        QLinearGradient, QPen, QPalette, QResizeEvent,
                        QCursor)

# Local imports
from spyder.plugins.editor.api.decoration import TextDecoration, DRAW_ORDERS
from spyder.plugins.editor.utils.folding import FoldScope
from spyder.api.panel import Panel
from spyder.plugins.editor.utils.editor import (TextBlockHelper, TextHelper,
                                                DelayJobRunner, drift_color)
import spyder.utils.icon_manager as ima


class FoldingPanel(Panel):

    """
    Displays the document outline and lets the user collapse/expand blocks.

    The data represented by the panel come from the text block user state and
    is set by the SyntaxHighlighter mode.

    The panel does not expose any function that you can use directly. To
    interact with the fold tree, you need to modify text block fold level or
    trigger state using :class:`spyder.api.utils.TextBlockHelper` or
    :mod:`spyder.api.folding`
    """
    #: signal emitted when a fold trigger state has changed, parameters are
    #: the concerned text block and the new state (collapsed or not).
    trigger_state_changed = Signal(QTextBlock, bool)
    collapse_all_triggered = Signal()
    expand_all_triggered = Signal()

    @property
    def native_icons(self):
        """
        Defines whether the panel will use native indicator icons or
        use custom ones.

        If you want to use custom indicator icons, you must first
        set this flag to False.
        """
        return self.native_icons

    @native_icons.setter
    def native_icons(self, value):
        self._native_icons = value
        # propagate changes to every clone
        if self.editor:
            for clone in self.editor.clones:
                try:
                    clone.modes.get(self.__class__).native_icons = value
                except KeyError:
                    # this should never happen since we're working with clones
                    pass

    @property
    def indicators_icons(self):
        """
        Gets/sets the icons for the fold indicators.

        The list of indicators is interpreted as follow::

            (COLLAPSED_OFF, COLLAPSED_ON, EXPANDED_OFF, EXPANDED_ON)

        To use this property you must first set `native_icons` to False.

        :returns: tuple(str, str, str, str)
        """
        return self._indicators_icons

    @indicators_icons.setter
    def indicators_icons(self, value):
        if len(value) != 4:
            raise ValueError('The list of custom indicators must contains 4 '
                             'strings')
        self._indicators_icons = value
        if self.editor:
            # propagate changes to every clone
            for clone in self.editor.clones:
                try:
                    clone.modes.get(
                        self.__class__).indicators_icons = value
                except KeyError:
                    # this should never happen since we're working with clones
                    pass


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

    def __init__(self, highlight_caret_scope=False):
        Panel.__init__(self)
        self._native_icons = False
        self._indicators_icons = (
            'folding.arrow_right_off',
            'folding.arrow_right_on',
            'folding.arrow_down_off',
            'folding.arrow_down_on'
        )
        self._block_nbr = -1
        self._highlight_caret = False
        self.highlight_caret_scope = highlight_caret_scope
        self._indic_size = 16
        #: the list of deco used to highlight the current fold region (
        #: surrounding regions are darker)
        self._scope_decos = []
        #: the list of folded blocs decorations
        self._block_decos = []
        self.setMouseTracking(True)
        self.scrollable = True
        self._mouse_over_line = None
        self._current_scope = None
        self._prev_cursor = None
        self.context_menu = None
        self.action_collapse = None
        self.action_expand = None
        self.action_collapse_all = None
        self.action_expand_all = None
        self._original_background = None
        self._highlight_runner = DelayJobRunner(delay=250)

    def sizeHint(self):
        """Returns the widget size hint (based on the editor font size) """
        fm = QFontMetricsF(self.editor.font())
        size_hint = QSize(fm.height(), fm.height())
        if size_hint.width() > 16:
            size_hint.setWidth(16)
        return size_hint

    def paintEvent(self, event):
        # Paints the fold indicators and the possible fold region background
        # on the folding panel.
        super(FoldingPanel, self).paintEvent(event)
        painter = QPainter(self)
        # Draw background over the selected non collapsed fold region
        if self._mouse_over_line is not None:
            block = self.editor.document().findBlockByNumber(
                self._mouse_over_line)
            try:
                self._draw_fold_region_background(block, painter)
            except ValueError:
                pass
        # Draw fold triggers
        for top_position, line_number, block in self.editor.visible_blocks:
            if TextBlockHelper.is_fold_trigger(block):
                collapsed = TextBlockHelper.is_collapsed(block)
                mouse_over = self._mouse_over_line == line_number
                self._draw_fold_indicator(
                    top_position, mouse_over, collapsed, painter)
                if collapsed:
                    # check if the block already has a decoration, it might
                    # have been folded by the parent editor/document in the
                    # case of cloned editor
                    for deco in self._block_decos:
                        if deco.block == block:
                            # no need to add a deco, just go to the next block
                            break
                    else:
                        self._add_fold_decoration(block, FoldScope(block))
                else:
                    for deco in self._block_decos:
                        # check if the block decoration has been removed, it
                        # might have been unfolded by the parent
                        # editor/document in the case of cloned editor
                        if deco.block == block:
                            # remove it and
                            self._block_decos.remove(deco)
                            self.editor.decorations.remove(deco)
                            del deco
                            break

    def _draw_fold_region_background(self, block, painter):
        """
        Draw the fold region when the mouse is over and non collapsed
        indicator.

        :param top: Top position
        :param block: Current block.
        :param painter: QPainter
        """
        r = FoldScope(block)
        th = TextHelper(self.editor)
        start, end = r.get_range(ignore_blank_lines=True)
        if start > 0:
            top = th.line_pos_from_number(start)
        else:
            top = 0
        bottom = th.line_pos_from_number(end + 1)
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
        grad = QLinearGradient(rect.topLeft(),
                                     rect.topRight())
        if sys.platform == 'darwin':
            grad.setColorAt(0, c.lighter(100))
            grad.setColorAt(1, c.lighter(110))
            outline = c.darker(110)
        else:
            grad.setColorAt(0, c.lighter(110))
            grad.setColorAt(1, c.lighter(130))
            outline = c.darker(100)
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

    def _draw_fold_indicator(self, top, mouse_over, collapsed, painter):
        """
        Draw the fold indicator/trigger (arrow).

        :param top: Top position
        :param mouse_over: Whether the mouse is over the indicator
        :param collapsed: Whether the trigger is collapsed or not.
        :param painter: QPainter
        """
        rect = QRect(0, top, self.sizeHint().width(),
                            self.sizeHint().height())
        if self._native_icons:
            opt = QStyleOptionViewItem()

            opt.rect = rect
            opt.state = (QStyle.State_Active |
                         QStyle.State_Item |
                         QStyle.State_Children)
            if not collapsed:
                opt.state |= QStyle.State_Open
            if mouse_over:
                opt.state |= (QStyle.State_MouseOver |
                              QStyle.State_Enabled |
                              QStyle.State_Selected)
                opt.palette.setBrush(QPalette.Window,
                                     self.palette().highlight())
            opt.rect.translate(-2, 0)
            self.style().drawPrimitive(QStyle.PE_IndicatorBranch,
                                       opt, painter, self)
        else:
            index = 0
            if not collapsed:
                index = 2
            if mouse_over:
                index += 1
            ima.icon(self._indicators_icons[index]).paint(painter, rect)

    @staticmethod
    def find_parent_scope(block):
        """Find parent scope, if the block is not a fold trigger."""
        original = block
        if not TextBlockHelper.is_fold_trigger(block):
            # search level of next non blank line
            while block.text().strip() == '' and block.isValid():
                block = block.next()
            ref_lvl = TextBlockHelper.get_fold_lvl(block) - 1
            block = original
            while (block.blockNumber() and
                   (not TextBlockHelper.is_fold_trigger(block) or
                    TextBlockHelper.get_fold_lvl(block) > ref_lvl)):
                block = block.previous()
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
        if color.lightness() < 128:
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
        draw_order = DRAW_ORDERS.get('codefolding')
        d = TextDecoration(self.editor.document(), start_line=start,
                           end_line=end+1, draw_order=draw_order)
        d.set_background(color)
        d.set_full_width(True, clear=False)
        self.editor.decorations.add(d)
        self._scope_decos.append(d)

    def _highlight_block(self, block):
        """
        Highlights the current fold scope.

        :param block: Block that starts the current fold scope.
        """
        scope = FoldScope(block)
        if (self._current_scope is None or
                self._current_scope.get_range() != scope.get_range()):
            self._current_scope = scope
            self._clear_scope_decos()
            # highlight current scope with darker or lighter color
            start, end = scope.get_range()
            if not TextBlockHelper.is_collapsed(block):
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
            block = FoldScope.find_parent_scope(
                self.editor.document().findBlockByNumber(line-1))
            if TextBlockHelper.is_fold_trigger(block):
                if self._mouse_over_line is None:
                    # mouse enter fold scope
                    QApplication.setOverrideCursor(
                        QCursor(Qt.PointingHandCursor))
                if self._mouse_over_line != block.blockNumber() and \
                        self._mouse_over_line is not None:
                    # fold scope changed, a previous block was highlighter so
                    # we quickly update our highlighting
                    self._mouse_over_line = block.blockNumber()
                    self._highlight_block(block)
                else:
                    # same fold scope, request highlight
                    self._mouse_over_line = block.blockNumber()
                    self._highlight_runner.request_job(
                        self._highlight_block, block)
                self._highight_block = block
            else:
                # no fold scope to highlight, cancel any pending requests
                self._highlight_runner.cancel_requests()
                self._mouse_over_line = None
                QApplication.restoreOverrideCursor()
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

    def _add_fold_decoration(self, block, region):
        """
        Add fold decorations (boxes arround a folded block in the editor
        widget).
        """
        draw_order = DRAW_ORDERS.get('codefolding')
        deco = TextDecoration(block, draw_order=draw_order)
        deco.signals.clicked.connect(self._on_fold_deco_clicked)
        deco.tooltip = region.text(max_lines=25)
        deco.block = block
        deco.select_line()
        deco.set_outline(drift_color(
            self._get_scope_highlight_color(), 110))
        deco.set_background(self._get_scope_highlight_color())
        deco.set_foreground(QColor('#808080'))
        self._block_decos.append(deco)
        self.editor.decorations.add(deco)

    def toggle_fold_trigger(self, block):
        """
        Toggle a fold trigger block (expand or collapse it).

        :param block: The QTextBlock to expand/collapse
        """
        if not TextBlockHelper.is_fold_trigger(block):
            return
        region = FoldScope(block)
        if region.collapsed:
            region.unfold()
            if self._mouse_over_line is not None:
                self._decorate_block(*region.get_range())
        else:
            region.fold()
            self._clear_scope_decos()
        self._refresh_editor_and_scrollbars()
        self.trigger_state_changed.emit(region._trigger, region.collapsed)

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
            if self._highlight_caret:
                self.editor.cursorPositionChanged.connect(
                    self._highlight_caret_scope)
                self._block_nbr = -1
            self.editor.new_text_set.connect(self._clear_block_deco)
        else:
            self.editor.sig_key_pressed.disconnect(self._on_key_pressed)
            if self._highlight_caret:
                self.editor.cursorPositionChanged.disconnect(
                    self._highlight_caret_scope)
                self._block_nbr = -1
            self.editor.new_text_set.disconnect(self._clear_block_deco)

    def _on_key_pressed(self, event):
        """
        Override key press to select the current scope if the user wants
        to deleted a folded scope (without selecting it).
        """
        delete_request = event.key() in [Qt.Key_Backspace,
                                         Qt.Key_Delete]
        if event.text() or delete_request:
            cursor = self.editor.textCursor()
            if cursor.hasSelection():
                # change selection to encompass the whole scope.
                positions_to_check = cursor.selectionStart(), cursor.selectionEnd()
            else:
                positions_to_check = (cursor.position(), )
            for pos in positions_to_check:
                block = self.editor.document().findBlock(pos)
                th = TextBlockHelper()
                if th.is_fold_trigger(block) and th.is_collapsed(block):
                    self.toggle_fold_trigger(block)
                    if delete_request and cursor.hasSelection():
                        scope = FoldScope(self.find_parent_scope(block))
                        tc = TextHelper(self.editor).select_lines(*scope.get_range())
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

    @staticmethod
    def _show_previous_blank_lines(block):
        """
        Show the block previous blank lines
        """
        # set previous blank lines visibles
        pblock = block.previous()
        while (pblock.text().strip() == '' and
               pblock.blockNumber() >= 0):
            pblock.setVisible(True)
            pblock = pblock.previous()

    def refresh_decorations(self, force=False):
        """
        Refresh decorations colors. This function is called by the syntax
        highlighter when the style changed so that we may update our
        decorations colors according to the new style.
        """
        cursor = self.editor.textCursor()
        if (self._prev_cursor is None or force or
                self._prev_cursor.blockNumber() != cursor.blockNumber()):
            for deco in self._block_decos:
                self.editor.decorations.remove(deco)
            for deco in self._block_decos:
                deco.set_outline(drift_color(
                    self._get_scope_highlight_color(), 110))
                deco.set_background(self._get_scope_highlight_color())
                self.editor.decorations.add(deco)
        self._prev_cursor = cursor

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
        self._clear_block_deco()
        block = self.editor.document().firstBlock()
        last = self.editor.document().lastBlock()
        while block.isValid():
            lvl = TextBlockHelper.get_fold_lvl(block)
            trigger = TextBlockHelper.is_fold_trigger(block)
            if trigger:
                if lvl == 0:
                    self._show_previous_blank_lines(block)
                TextBlockHelper.set_collapsed(block, True)
            block.setVisible(lvl == 0)
            if block == last and block.text().strip() == '':
                block.setVisible(True)
                self._show_previous_blank_lines(block)
            block = block.next()
        self._refresh_editor_and_scrollbars()
        tc = self.editor.textCursor()
        tc.movePosition(tc.Start)
        self.editor.setTextCursor(tc)
        self.collapse_all_triggered.emit()

    def _clear_block_deco(self):
        """Clear the folded block decorations."""
        for deco in self._block_decos:
            self.editor.decorations.remove(deco)
        self._block_decos[:] = []

    def expand_all(self):
        """Expands all fold triggers."""
        block = self.editor.document().firstBlock()
        while block.isValid():
            TextBlockHelper.set_collapsed(block, False)
            block.setVisible(True)
            block = block.next()
        self._clear_block_deco()
        self._refresh_editor_and_scrollbars()
        self.expand_all_triggered.emit()

    def _on_action_toggle(self):
        """Toggle the current fold trigger."""
        block = FoldScope.find_parent_scope(self.editor.textCursor().block())
        self.toggle_fold_trigger(block)

    def _on_action_collapse_all_triggered(self):
        """Closes all top levels fold triggers recursively."""
        self.collapse_all()

    def _on_action_expand_all_triggered(self):
        """
        Expands all fold triggers.
        :return:
        """
        self.expand_all()

    def _highlight_caret_scope(self):
        """
        Highlight the scope of the current caret position.

        This get called only if :attr:`
        spyder.widgets.panels.FoldingPanel.highlight_care_scope` is True.
        """
        cursor = self.editor.textCursor()
        block_nbr = cursor.blockNumber()
        if self._block_nbr != block_nbr:
            block = FoldScope.find_parent_scope(
                self.editor.textCursor().block())
            try:
                s = FoldScope(block)
            except ValueError:
                self._clear_scope_decos()
            else:
                self._mouse_over_line = block.blockNumber()
                if TextBlockHelper.is_fold_trigger(block):
                    self._highlight_block(block)
        self._block_nbr = block_nbr

    def clone_settings(self, original):
        self.native_icons = original.native_icons
        self.indicators_icons = original.indicators_icons
        self.highlight_caret_scope = original.highlight_caret_scope
        self.custom_fold_region_background = \
            original.custom_fold_region_background
