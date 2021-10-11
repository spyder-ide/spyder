# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Frames browser widget

This is the main widget used in the Frames Explorer plugin
"""
import os.path as osp
import html

# Third library imports (qtpy)
from qtpy.QtCore import Signal
from qtpy.QtWidgets import (QVBoxLayout, QWidget, QTreeWidget)
from qtpy.QtGui import QAbstractTextDocumentLayout, QTextDocument
from qtpy.QtCore import (QSize, Qt, Slot)
from qtpy.QtWidgets import (QApplication, QStyle,
                            QStyledItemDelegate, QStyleOptionViewItem,
                            QTreeWidgetItem)

# Local imports
from spyder.api.widgets.mixins import SpyderWidgetMixin
from spyder.api.translations import get_translation
from spyder.py3compat import to_text_string
from spyder.config.gui import get_font
from spyder.widgets.helperwidgets import FinderLineEdit

VALID_VARIABLE_CHARS = r"[^\w+*=¡!¿?'\"#$%&()/<>\-\[\]{}^`´;,|¬]*\w"

# Localization
_ = get_translation('spyder')


class FramesBrowser(QWidget, SpyderWidgetMixin):
    """Frames browser (global frames explorer widget)"""
    # This is necessary to test the widget separately from its plugin
    CONF_SECTION = 'frames_explorer'

    # Signals
    edit_goto = Signal((str, int, str), (str, int, str, bool))
    sig_show_namespace = Signal(dict)
    sig_hide_finder_requested = Signal()
    sig_update_postmortem_requested = Signal(object)

    def __init__(self, parent, color_scheme):
        QWidget.__init__(self, parent)

        self.shellwidget = None
        self.results_browser = None
        self.color_scheme = color_scheme
        self.execution_frames = False
        self.should_clear = False
        self.post_mortem = False

        # Finder
        self.text_finder = None
        self.last_find = ''
        self.finder_is_visible = False

    def set_post_mortem_enabled(self, enabled):
        """Enable post-mortem button."""
        self.post_mortem = enabled
        self.sig_update_postmortem_requested.emit(self)

    def setup(self):
        """
        Setup the frames browser with provided settings.
        """
        assert self.shellwidget is not None

        if self.results_browser is not None:
            return

        self.results_browser = ResultsBrowser(self, self.color_scheme)
        self.results_browser.sig_edit_goto.connect(self.edit_goto)
        self.results_browser.sig_show_namespace.connect(
            self.sig_show_namespace)

        # Setup layout.
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.results_browser)
        self.setLayout(layout)

    def set_shellwidget(self, shellwidget):
        """Bind shellwidget instance to frames browser"""
        self.shellwidget = shellwidget
        shellwidget.sig_pdb_stack.connect(self.set_from_pdb)
        shellwidget.sig_show_traceback.connect(self.set_from_exception)
        shellwidget.executed.connect(self.clear_if_needed)

    def refresh(self):
        """Refresh frames table"""
        if self.isVisible():
            sw = self.shellwidget
            if sw.kernel_client is None:
                return
            sw.call_kernel(
                interrupt=True, callback=self.set_from_refresh
                ).get_current_frames(
                    ignore_internal_threads=self.get_conf("exclude_internal"),
                    capture_locals=self.get_conf("capture_locals"))

    def _set_frames(self, frames, title):
        """Set current frames"""
        if self.results_browser is not None:
            self.results_browser.set_frames(frames)
            self.results_browser.set_title(title)

            try:
                self.results_browser.sig_activated.disconnect(
                    self.shellwidget.set_pdb_index)
            except TypeError:
                pass

    def set_from_pdb(self, pdb_stack, curindex):
        """Set from pdb stack"""
        self._set_frames({'pdb': pdb_stack}, _("Pdb stack"))
        self.set_current_item(0, curindex)
        self.results_browser.sig_activated.connect(
            self.shellwidget.set_pdb_index)
        self.execution_frames = True
        self.should_clear = False
        self.set_post_mortem_enabled(False)

    def set_from_exception(self, etype, error, tb):
        """Set from exception"""
        self._set_frames({etype.__name__: tb}, _("Exception occured"))
        self.execution_frames = True
        self.should_clear = False
        self.set_post_mortem_enabled(True)

    def set_from_refresh(self, frames):
        """Set from pdb call"""
        self._set_frames(frames, _("Snapshot of frames"))
        self.execution_frames = False
        self.should_clear = False
        self.set_post_mortem_enabled(False)

    def clear_if_needed(self):
        """Execution finished. Clear if it is relevant."""
        if self.should_clear:
            self._set_frames(None, "")
            self.should_clear = False
            self.set_post_mortem_enabled(False)
        elif self.execution_frames:
            self.should_clear = True
        self.execution_frames = False

    def set_current_item(self, top_idx, sub_index):
        """Set current item"""
        if self.results_browser is not None:
            self.results_browser.set_current_item(top_idx, sub_index)

    def set_text_finder(self, text_finder):
        """Bind NamespaceBrowsersFinder to namespace browser."""
        self.text_finder = text_finder
        if self.finder_is_visible:
            self.text_finder.setText(self.last_find)
        self.results_browser.finder = text_finder

        return self.finder_is_visible

    def save_finder_state(self, last_find, finder_visibility):
        """Save last finder/search text input and finder visibility."""
        if last_find and finder_visibility:
            self.last_find = last_find
        self.finder_is_visible = finder_visibility


class LineFrameItem(QTreeWidgetItem):

    def __init__(self, parent, index, filename, line, lineno, name,
                 f_locals, font, color_scheme=None):
        self.index = index
        self.filename = filename
        self.text = line
        self.lineno = lineno
        self.context = name
        self.color_scheme = color_scheme
        self.font = font
        self.locals = f_locals
        QTreeWidgetItem.__init__(self, parent, [self.__repr__()],
                                 QTreeWidgetItem.Type)

    def __repr__(self):
        """Prints item as html."""
        if self.filename is None:
            return ("<!-- LineFrameItem -->"
                    '<p><span style="color:{0}">idle</span></p>').format(
                        self.color_scheme['normal'][0])
        _str = ("<!-- LineFrameItem -->" +
                "<p style=\"color:'{0}';\"><b> ".format(
                    self.color_scheme['normal'][0]) +
                "<span style=\"color:'{0}';\">{1}</span>:".format(
                    self.color_scheme['string'][0],
                    html.escape(osp.basename(self.filename))) +
                "<span style=\"color:'{0}';\">{1}</span></b>".format(
                    self.color_scheme['number'][0], self.lineno))
        if self.context:
            _str += " (<span style=\"color:'{0}';\">{1}</span>)".format(
                self.color_scheme['builtin'][0], html.escape(self.context))

        _str += (
            "    <span style=\"font-family:{0};".format(self.font.family())
            + "color:'{0}';font-size:50%;\"><em>{1}</em></span></p>".format(
                self.color_scheme['comment'][0], self.text))
        return _str

    def to_plain_text(self):
        """Represent item as plain text."""
        if self.filename is None:
            return ("idle")
        _str = (html.escape(osp.basename(self.filename)) + ":" +
                str(self.lineno))
        if self.context:
            _str += " ({})".format(html.escape(self.context))

        _str += " {}".format(self.text)
        return _str

    def __unicode__(self):
        """String representation."""
        return self.__repr__()

    def __str__(self):
        """String representation."""
        return self.__repr__()

    def __lt__(self, x):
        """Smaller for sorting."""
        return self.index < x.index

    def __ge__(self, x):
        """Larger or equals for sorting."""
        return self.index >= x.index


class ThreadItem(QTreeWidgetItem):

    def __init__(self, parent, name, text_color):
        self.name = str(name)

        title_format = to_text_string('<!-- ThreadItem -->'
                                      '<b style="color:{1}">{0}</b>'
                                      )
        title = (title_format.format(name, text_color))
        QTreeWidgetItem.__init__(self, parent, [title], QTreeWidgetItem.Type)

        self.setToolTip(0, self.name)

    def __lt__(self, x):
        """Smaller for sorting."""
        return self.name < x.name

    def __ge__(self, x):
        """Larger or equals for sorting."""
        return self.name >= x.name


class ItemDelegate(QStyledItemDelegate):

    def __init__(self, parent):
        QStyledItemDelegate.__init__(self, parent)
        self._margin = None

    def paint(self, painter, option, index):
        """Paint the item."""
        options = QStyleOptionViewItem(option)
        self.initStyleOption(options, index)

        style = (QApplication.style() if options.widget is None
                 else options.widget.style())

        doc = QTextDocument()
        text = options.text
        doc.setHtml(text)
        doc.setDocumentMargin(0)

        # This needs to be an empty string to avoid the overlapping the
        # normal text of the QTreeWidgetItem
        options.text = ""
        style.drawControl(QStyle.CE_ItemViewItem, options, painter)

        ctx = QAbstractTextDocumentLayout.PaintContext()

        textRect = style.subElementRect(QStyle.SE_ItemViewItemText,
                                        options, None)
        painter.save()

        painter.translate(textRect.topLeft())
        painter.setClipRect(textRect.translated(-textRect.topLeft()))
        doc.documentLayout().draw(painter, ctx)
        painter.restore()

    def sizeHint(self, option, index):
        """Get a size hint."""
        options = QStyleOptionViewItem(option)
        self.initStyleOption(options, index)
        doc = QTextDocument()
        doc.setHtml(options.text)
        doc.setTextWidth(options.rect.width())
        size = QSize(int(doc.idealWidth()), int(doc.size().height()))
        return size


class ResultsBrowser(QTreeWidget):
    sig_edit_goto = Signal(str, int, str)
    sig_activated = Signal(int)
    sig_show_namespace = Signal(dict)

    def __init__(self, parent, color_scheme):
        super().__init__(parent)
        self.font = get_font()
        self.data = None
        self.threads = None
        self.color_scheme = color_scheme
        self.text_color = color_scheme['normal'][0]
        self.frames = None
        self.menu = None
        self.empty_ws_menu = None

        # Setup
        self.setItemsExpandable(True)
        self.setColumnCount(1)
        self.set_title('')
        self.setSortingEnabled(False)
        self.setItemDelegate(ItemDelegate(self))
        self.setUniformRowHeights(True)  # Needed for performance
        self.sortByColumn(0, Qt.AscendingOrder)

        # Signals
        self.header().sectionClicked.connect(self.sort_section)
        self.itemActivated.connect(self.activated)
        self.itemClicked.connect(self.activated)

        self.finder = None

    def set_title(self, title):
        self.setHeaderLabels([title])

    def activated(self, item):
        """Double-click event."""
        itemdata = self.data.get(id(self.currentItem()))
        if itemdata is not None:
            filename, lineno = itemdata
            self.sig_edit_goto.emit(filename, lineno, '')
            # Index exists if the item is in self.data
            self.sig_activated.emit(self.currentItem().index)
        if self.parent().get_conf("show_locals_on_click"):
            self.view_item_locals()

    def view_item_locals(self):
        """View item locals."""
        item = self.currentItem()
        item_has_locals = (
            isinstance(item, LineFrameItem) and
            item.locals is not None)
        if item_has_locals:
            self.sig_show_namespace.emit(item.locals)

    def contextMenuEvent(self, event):
        """Reimplement Qt method"""
        if self.menu is None:
            return

        if self.frames:
            self.menu.popup(event.globalPos())
            event.accept()
        else:
            self.empty_ws_menu.popup(event.globalPos())
            event.accept()

    def refresh_menu(self):
        """Refresh context menu"""
        item = self.currentItem()
        item_has_locals = (
            isinstance(item, LineFrameItem) and
            item.locals is not None)
        self.view_locals_action.setEnabled(item_has_locals)

    @Slot(int)
    def sort_section(self, idx):
        """Sort section"""
        self.setSortingEnabled(True)

    def set_current_item(self, top_idx, sub_index):
        """Set current item."""
        item = self.topLevelItem(top_idx).child(sub_index)
        self.setCurrentItem(item)

    def set_frames(self, frames):
        """Set frames."""
        self.clear()
        self.threads = {}
        self.data = {}
        self.frames = frames

        if frames is None:
            return
        for threadId, stack in frames.items():
            parent = ThreadItem(
                self, threadId, self.text_color)
            parent.setExpanded(True)
            self.threads[threadId] = parent
            if stack:
                for idx, frame in enumerate(stack):
                    item = LineFrameItem(parent, idx,
                                         frame.filename,
                                         frame.line,
                                         frame.lineno,
                                         frame.name,
                                         frame.locals,
                                         self.font, self.color_scheme)
                    self.data[id(item)] = (frame.filename, frame.lineno)
            else:
                item = LineFrameItem(
                    parent, 0, None, '', 0, '', None,
                    self.font, self.color_scheme)

    def set_regex(self, regex=None):
        """Update the regex text for the variable finder."""
        if self.finder is None or not self.finder.text():
            text = ''
        else:
            text = self.finder.text().replace(' ', '').lower()

        for idx in range(self.topLevelItemCount()):
            item = self.topLevelItem(idx)
            all_hidden = True
            for child_idx in range(item.childCount()):
                line_frame = item.child(child_idx)
                if text:
                    match_text = line_frame.to_plain_text().replace(
                        ' ', '').lower()
                    if match_text.find(text) == -1:
                        line_frame.setHidden(True)
                    else:
                        line_frame.setHidden(False)
                        all_hidden = False
                else:
                    line_frame.setHidden(False)
                    all_hidden = False
            item.setHidden(all_hidden)


class FramesBrowserFinder(FinderLineEdit):
    """Textbox for filtering listed variables in the table."""
    # To load all variables when filtering.
    load_all = False

    def update_parent(self, parent, callback=None, main=None):
        self._parent = parent
        self.main = main
        try:
            self.textChanged.disconnect()
        except TypeError:
            pass
        if callback:
            self.textChanged.connect(callback)

    def keyPressEvent(self, event):
        """Qt and FilterLineEdit Override."""
        key = event.key()
        if key in [Qt.Key_Up, Qt.Key_Down]:
            self._parent.keyPressEvent(event)
        elif key in [Qt.Key_Escape]:
            self.main.sig_hide_finder_requested.emit()
        elif key in [Qt.Key_Enter, Qt.Key_Return]:
            pass
        else:
            super(FramesBrowserFinder, self).keyPressEvent(event)
