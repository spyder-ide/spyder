# -*- coding: utf-8 -*-
"""
This module contains the marker panel
"""
import logging
import os
import sys
from pyqode.core.api import TextBlockHelper, folding, TextDecoration, \
    DelayJobRunner
from pyqode.core.api.folding import FoldScope
from pyqode.core.api.panel import Panel
from pyqode.qt import QtCore, QtWidgets, QtGui, PYQT5_API
from pyqode.core.api.utils import TextHelper, drift_color, keep_tc_pos


def _logger():
    """ Gets module's logger """
    return logging.getLogger(__name__)


class FoldingPanel(Panel):

    """ Displays the document outline and lets the user collapse/expand blocks.

    The data represented by the panel come from the text block user state and
    is set by the SyntaxHighlighter mode.

    The panel does not expose any function that you can use directly. To
    interact with the fold tree, you need to modify text block fold level or
    trigger state using :class:`pyqode.core.api.utils.TextBlockHelper` or
    :mod:`pyqode.core.api.folding`
    """
    #: signal emitted when a fold trigger state has changed, parameters are
    #: the concerned text block and the new state (collapsed or not).
    trigger_state_changed = QtCore.Signal(QtGui.QTextBlock, bool)
    collapse_all_triggered = QtCore.Signal()
    expand_all_triggered = QtCore.Signal()

    @property
    def native_look(self):
        """
        Defines whether the panel will use native indicator icons and color or
        use custom one.

        If you want to use custom indicator icons and color, you must first
        set this flag to False.
        """
        return self._native

    @native_look.setter
    def native_look(self, value):
        self._native = value
        # propagate changes to every clone
        if self.editor:
            for clone in self.editor.clones:
                try:
                    clone.modes.get(self.__class__).native_look = value
                except KeyError:
                    # this should never happen since we're working with clones
                    pass

    @property
    def custom_indicators_icons(self):
        """
        Gets/sets the custom icon for the fold indicators.

        The list of indicators is interpreted as follow::

            (COLLAPSED_OFF, COLLAPSED_ON, EXPANDED_OFF, EXPANDED_ON)

        To use this property you must first set `native_look` to False.

        :returns: tuple(str, str, str, str)
        """
        return self._custom_indicators

    @custom_indicators_icons.setter
    def custom_indicators_icons(self, value):
        if len(value) != 4:
            raise ValueError('The list of custom indicators must contains 4 '
                             'strings')
        self._custom_indicators = value
        if self.editor:
            # propagate changes to every clone
            for clone in self.editor.clones:
                try:
                    clone.modes.get(
                        self.__class__).custom_indicators_icons = value
                except KeyError:
                    # this should never happen since we're working with clones
                    pass

    @property
    def custom_fold_region_background(self):
        """
        Custom base color for the fold region background

        :return: QColor
        """
        return self._custom_color

    @custom_fold_region_background.setter
    def custom_fold_region_background(self, value):
        self._custom_color = value
        # propagate changes to every clone
        if self.editor:
            for clone in self.editor.clones:
                try:
                    clone.modes.get(
                        self.__class__).custom_fold_region_background = value
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
        self._native = True
        self._custom_indicators = (
            ':/pyqode-icons/rc/arrow_right_off.png',
            ':/pyqode-icons/rc/arrow_right_on.png',
            ':/pyqode-icons/rc/arrow_down_off.png',
            ':/pyqode-icons/rc/arrow_down_on.png'
        )
        self._custom_color = QtGui.QColor('gray')
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

    def on_install(self, editor):
        """
        Add the folding menu to the editor, on install.

        :param editor: editor instance on which the mode has been installed to.
        """
        super(FoldingPanel, self).on_install(editor)
        self.context_menu = QtWidgets.QMenu(_('Folding'), self.editor)
        action = self.action_collapse = QtWidgets.QAction(
            _('Collapse'), self.context_menu)
        action.setShortcut('Shift+-')
        action.triggered.connect(self._on_action_toggle)
        self.context_menu.addAction(action)
        action = self.action_expand = QtWidgets.QAction(_('Expand'),
                                                        self.context_menu)
        action.setShortcut('Shift++')
        action.triggered.connect(self._on_action_toggle)
        self.context_menu.addAction(action)
        self.context_menu.addSeparator()
        action = self.action_collapse_all = QtWidgets.QAction(
            _('Collapse all'), self.context_menu)
        action.setShortcut('Ctrl+Shift+-')
        action.triggered.connect(self._on_action_collapse_all_triggered)
        self.context_menu.addAction(action)
        action = self.action_expand_all = QtWidgets.QAction(
            _('Expand all'), self.context_menu)
        action.setShortcut('Ctrl+Shift++')
        action.triggered.connect(self._on_action_expand_all_triggered)
        self.context_menu.addAction(action)
        self.editor.add_menu(self.context_menu)

    def sizeHint(self):
        """ Returns the widget size hint (based on the editor font size) """
        fm = QtGui.QFontMetricsF(self.editor.font())
        size_hint = QtCore.QSize(fm.height(), fm.height())
        if size_hint.width() > 16:
            size_hint.setWidth(16)
        return size_hint

    def paintEvent(self, event):
        # Paints the fold indicators and the possible fold region background
        # on the folding panel.
        super(FoldingPanel, self).paintEvent(event)
        painter = QtGui.QPainter(self)
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
        r = folding.FoldScope(block)
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
        self._draw_rect(QtCore.QRectF(0, top, w, h), painter)

    def _draw_rect(self, rect, painter):
        """
        Draw the background rectangle using the current style primitive color
        or foldIndicatorBackground if nativeFoldingIndicator is true.

        :param rect: The fold zone rect to draw

        :param painter: The widget's painter.
        """
        c = self._custom_color
        if self._native:
            c = self.get_system_bck_color()
        grad = QtGui.QLinearGradient(rect.topLeft(),
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
        painter.setPen(QtGui.QPen(outline))
        painter.drawLine(rect.topLeft() +
                         QtCore.QPointF(1, 0),
                         rect.topRight() -
                         QtCore.QPointF(1, 0))
        painter.drawLine(rect.bottomLeft() +
                         QtCore.QPointF(1, 0),
                         rect.bottomRight() -
                         QtCore.QPointF(1, 0))
        painter.drawLine(rect.topRight() +
                         QtCore.QPointF(0, 1),
                         rect.bottomRight() -
                         QtCore.QPointF(0, 1))
        painter.drawLine(rect.topLeft() +
                         QtCore.QPointF(0, 1),
                         rect.bottomLeft() -
                         QtCore.QPointF(0, 1))

    @staticmethod
    def get_system_bck_color():
        """
        Gets a system color for drawing the fold scope background.
        """
        def merged_colors(colorA, colorB, factor):
            maxFactor = 100
            colorA = QtGui.QColor(colorA)
            colorB = QtGui.QColor(colorB)
            tmp = colorA
            tmp.setRed((tmp.red() * factor) / maxFactor +
                       (colorB.red() * (maxFactor - factor)) / maxFactor)
            tmp.setGreen((tmp.green() * factor) / maxFactor +
                         (colorB.green() * (maxFactor - factor)) / maxFactor)
            tmp.setBlue((tmp.blue() * factor) / maxFactor +
                        (colorB.blue() * (maxFactor - factor)) / maxFactor)
            return tmp

        pal = QtWidgets.QApplication.instance().palette()
        b = pal.window().color()
        h = pal.highlight().color()
        return merged_colors(b, h, 50)

    def _draw_fold_indicator(self, top, mouse_over, collapsed, painter):
        """
        Draw the fold indicator/trigger (arrow).

        :param top: Top position
        :param mouse_over: Whether the mouse is over the indicator
        :param collapsed: Whether the trigger is collapsed or not.
        :param painter: QPainter
        """
        rect = QtCore.QRect(0, top, self.sizeHint().width(),
                            self.sizeHint().height())
        if self._native:
            if os.environ['QT_API'].lower() not in PYQT5_API:
                opt = QtGui.QStyleOptionViewItemV2()
            else:
                opt = QtWidgets.QStyleOptionViewItem()
            opt.rect = rect
            opt.state = (QtWidgets.QStyle.State_Active |
                         QtWidgets.QStyle.State_Item |
                         QtWidgets.QStyle.State_Children)
            if not collapsed:
                opt.state |= QtWidgets.QStyle.State_Open
            if mouse_over:
                opt.state |= (QtWidgets.QStyle.State_MouseOver |
                              QtWidgets.QStyle.State_Enabled |
                              QtWidgets.QStyle.State_Selected)
                opt.palette.setBrush(QtGui.QPalette.Window,
                                     self.palette().highlight())
            opt.rect.translate(-2, 0)
            self.style().drawPrimitive(QtWidgets.QStyle.PE_IndicatorBranch,
                                       opt, painter, self)
        else:
            index = 0
            if not collapsed:
                index = 2
            if mouse_over:
                index += 1
            QtGui.QIcon(self._custom_indicators[index]).paint(painter, rect)

    @staticmethod
    def find_parent_scope(block):
        """
        Find parent scope, if the block is not a fold trigger.

        """
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
        """
        Clear scope decorations (on the editor)

        """
        for deco in self._scope_decos:
            self.editor.decorations.remove(deco)
        self._scope_decos[:] = []

    def _get_scope_highlight_color(self):
        """
        Gets the base scope highlight color (derivated from the editor
        background)

        """
        color = self.editor.background
        if color.lightness() < 128:
            color = drift_color(color, 130)
        else:
            color = drift_color(color, 105)
        return color

    def _add_scope_deco(self, start, end, parent_start, parent_end, base_color,
                        factor):
        """
        Adds a scope decoration that enclose the current scope
        :param start: Start of the current scope
        :param end: End of the current scope
        :param parent_start: Start of the parent scope
        :param parent_end: End of the parent scope
        :param base_color: base color for scope decoration
        :param factor: color factor to apply on the base color (to make it
            darker).
        """
        color = drift_color(base_color, factor=factor)
        # upper part
        if start > 0:
            d = TextDecoration(self.editor.document(),
                               start_line=parent_start, end_line=start)
            d.set_full_width(True, clear=False)
            d.draw_order = 2
            d.set_background(color)
            self.editor.decorations.append(d)
            self._scope_decos.append(d)
        # lower part
        if end <= self.editor.document().blockCount():
            d = TextDecoration(self.editor.document(),
                               start_line=end, end_line=parent_end + 1)
            d.set_full_width(True, clear=False)
            d.draw_order = 2
            d.set_background(color)
            self.editor.decorations.append(d)
            self._scope_decos.append(d)

    def _add_scope_decorations(self, block, start, end):
        """
        Show a scope decoration on the editor widget

        :param start: Start line
        :param end: End line
        """
        try:
            parent = FoldScope(block).parent()
        except ValueError:
            parent = None
        if TextBlockHelper.is_fold_trigger(block):
            base_color = self._get_scope_highlight_color()
            factor_step = 5
            if base_color.lightness() < 128:
                factor_step = 10
                factor = 70
            else:
                factor = 100
            while parent:
                # highlight parent scope
                parent_start, parent_end = parent.get_range()
                self._add_scope_deco(
                    start, end + 1, parent_start, parent_end,
                    base_color, factor)
                # next parent scope
                start = parent_start
                end = parent_end
                parent = parent.parent()
                factor += factor_step
            # global scope
            parent_start = 0
            parent_end = self.editor.document().blockCount()
            self._add_scope_deco(
                start, end + 1, parent_start, parent_end, base_color,
                factor + factor_step)
        else:
            self._clear_scope_decos()

    def _highlight_surrounding_scopes(self, block):
        """
        Highlights the scopes surrounding the current fold scope.

        :param block: Block that starts the current fold scope.
        """
        scope = FoldScope(block)
        if (self._current_scope is None or
                self._current_scope.get_range() != scope.get_range()):
            self._current_scope = scope
            self._clear_scope_decos()
            # highlight surrounding parent scopes with a darker color
            start, end = scope.get_range()
            if not TextBlockHelper.is_collapsed(block):
                self._add_scope_decorations(block, start, end)

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
                self.editor.document().findBlockByNumber(line))
            if TextBlockHelper.is_fold_trigger(block):
                if self._mouse_over_line is None:
                    # mouse enter fold scope
                    QtWidgets.QApplication.setOverrideCursor(
                        QtGui.QCursor(QtCore.Qt.PointingHandCursor))
                if self._mouse_over_line != block.blockNumber() and \
                        self._mouse_over_line is not None:
                    # fold scope changed, a previous block was highlighter so
                    # we quickly update our highlighting
                    self._mouse_over_line = block.blockNumber()
                    self._highlight_surrounding_scopes(block)
                else:
                    # same fold scope, request highlight
                    self._mouse_over_line = block.blockNumber()
                    self._highlight_runner.request_job(
                        self._highlight_surrounding_scopes, block)
                self._highight_block = block
            else:
                # no fold scope to highlight, cancel any pending requests
                self._highlight_runner.cancel_requests()
                self._mouse_over_line = None
                QtWidgets.QApplication.restoreOverrideCursor()
            self.repaint()

    def leaveEvent(self, event):
        """
        Removes scope decorations and background from the editor and the panel
        if highlight_caret_scope, else simply update the scope decorations to
        match the caret scope.

        """
        super(FoldingPanel, self).leaveEvent(event)
        QtWidgets.QApplication.restoreOverrideCursor()
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
        deco = TextDecoration(block)
        deco.signals.clicked.connect(self._on_fold_deco_clicked)
        deco.tooltip = region.text(max_lines=25)
        deco.draw_order = 1
        deco.block = block
        deco.select_line()
        deco.set_outline(drift_color(
            self._get_scope_highlight_color(), 110))
        deco.set_background(self._get_scope_highlight_color())
        deco.set_foreground(QtGui.QColor('#808080'))
        self._block_decos.append(deco)
        self.editor.decorations.append(deco)

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
                self._add_scope_decorations(
                    region._trigger, *region.get_range())
        else:
            region.fold()
            self._clear_scope_decos()
        self._refresh_editor_and_scrollbars()
        self.trigger_state_changed.emit(region._trigger, region.collapsed)

    def mousePressEvent(self, event):
        """ Folds/unfolds the pressed indicator if any. """
        if self._mouse_over_line is not None:
            block = self.editor.document().findBlockByNumber(
                self._mouse_over_line)
            self.toggle_fold_trigger(block)

    def _on_fold_deco_clicked(self, deco):
        """
        Unfold a folded block that has just been clicked by the user
        """
        self.toggle_fold_trigger(deco.block)

    def on_state_changed(self, state):
        """
        On state changed we (dis)connect to the cursorPositionChanged signal
        """
        if state:
            self.editor.key_pressed.connect(self._on_key_pressed)
            if self._highlight_caret:
                self.editor.cursorPositionChanged.connect(
                    self._highlight_caret_scope)
                self._block_nbr = -1
            self.editor.new_text_set.connect(self._clear_block_deco)
        else:
            self.editor.key_pressed.disconnect(self._on_key_pressed)
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
        delete_request = event.key() in [QtCore.Qt.Key_Backspace,
                                         QtCore.Qt.Key_Delete]
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
                self.editor.decorations.append(deco)
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
        self.editor.resizeEvent(QtGui.QResizeEvent(self.editor.size(), s))

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
        """
        Clear the folded block decorations.
        """
        for deco in self._block_decos:
            self.editor.decorations.remove(deco)
        self._block_decos[:] = []

    def expand_all(self):
        """
        Expands all fold triggers.
        """
        block = self.editor.document().firstBlock()
        while block.isValid():
            TextBlockHelper.set_collapsed(block, False)
            block.setVisible(True)
            block = block.next()
        self._clear_block_deco()
        self._refresh_editor_and_scrollbars()
        self.expand_all_triggered.emit()

    def _on_action_toggle(self):
        """
        Toggle the current fold trigger.
        """
        block = FoldScope.find_parent_scope(self.editor.textCursor().block())
        self.toggle_fold_trigger(block)

    def _on_action_collapse_all_triggered(self):
        """
        Closes all top levels fold triggers recursively
        """
        self.collapse_all()

    def _on_action_expand_all_triggered(self):
        """
        Expands all fold triggers
        :return:
        """
        self.expand_all()

    def _highlight_caret_scope(self):
        """
        Highlight the scope surrounding the current caret position.

        This get called only if :attr:`
        pyqode.core.panels.FoldingPanel.highlight_care_scope` is True.
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
                    self._highlight_surrounding_scopes(block)
        self._block_nbr = block_nbr

    def clone_settings(self, original):
        self.native_look = original.native_look
        self.custom_indicators_icons = original.custom_indicators_icons
        self.highlight_caret_scope = original.highlight_caret_scope
        self.custom_fold_region_background = \
            original.custom_fold_region_background
