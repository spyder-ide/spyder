# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Frames browser widget

This is the main widget used in the Debugger plugin
"""

# Standard library imports
import os.path as osp
import html

# Third library imports
from qtpy.QtCore import Signal
from qtpy.QtGui import QAbstractTextDocumentLayout, QTextDocument
from qtpy.QtCore import (QSize, Qt, Slot)
from qtpy.QtWidgets import (
    QApplication, QStyle, QStyledItemDelegate, QStyleOptionViewItem,
    QTreeWidgetItem, QVBoxLayout, QWidget, QTreeWidget, QStackedLayout)

# Local imports
from spyder.api.config.decorators import on_conf_change
from spyder.api.fonts import SpyderFontsMixin, SpyderFontType
from spyder.api.widgets.mixins import SpyderWidgetMixin
from spyder.api.translations import _
from spyder.utils.palette import SpyderPalette
from spyder.widgets.helperwidgets import FinderWidget, PaneEmptyWidget


class FramesBrowserState:
    Debug = 'debug'
    DebugWait = 'debugwait'
    Inspect = 'inspect'
    Error = 'error'


class FramesBrowser(QWidget, SpyderWidgetMixin):
    """Frames browser (global debugger widget)"""
    CONF_SECTION = 'debugger'

    # Signals
    sig_edit_goto = Signal(str, int, str)
    """
    This signal will request to open a file in a given row and column
    using a code editor.

    Parameters
    ----------
    path: str
        Path to file.
    row: int
        Cursor starting row position.
    word: str
        Word to select on given row.
    """

    sig_update_actions_requested = Signal()
    """Update the widget actions."""

    sig_hide_finder_requested = Signal()
    """Hide the finder widget."""

    sig_load_pdb_file = Signal(str, int)
    """
    This signal is emitted when Pdb reaches a new line.

    Parameters
    ----------
    filename: str
        The filename the debugger stepped in
    line_number: int
        The line number the debugger stepped in
    """

    def __init__(self, parent, shellwidget):
        super().__init__(parent)
        self.shellwidget = shellwidget
        self.results_browser = None
        # -1 means never clear, otherwise number of calls
        self._persistence = -1
        self.state = None
        self.finder = None
        self.pdb_curindex = None
        self._pdb_state = []

    def pdb_has_stopped(self, fname, lineno):
        """Handle pdb has stopped"""
        # this will set the focus to the editor
        self.sig_load_pdb_file.emit(fname, lineno)
        if not self.shellwidget._pdb_take_focus:
            # Not taking focus will be required on each call to the debugger
            self.shellwidget._pdb_take_focus = True
        else:
            # take back focus
            self.shellwidget._control.setFocus()

    def toggle_finder(self, show):
        """Show and hide the finder."""
        self.finder.set_visible(show)
        if not show:
            self.results_browser.setFocus()

    def do_find(self, text):
        """Search for text."""
        if self.results_browser is not None:
            self.results_browser.do_find(text)

    def finder_is_visible(self):
        """Check if the finder is visible."""
        if self.finder is None:
            return False
        return self.finder.isVisible()

    def set_pane_empty(self, empty):
        if empty:
            self.stack_layout.setCurrentWidget(self.pane_empty)
        else:
            self.stack_layout.setCurrentWidget(self.container)

    def setup(self):
        """
        Setup the frames browser with provided settings.
        """
        if self.results_browser is not None:
            return

        self.results_browser = ResultsBrowser(self)
        self.results_browser.sig_edit_goto.connect(self.sig_edit_goto)

        self.finder = FinderWidget(self)
        self.finder.sig_find_text.connect(self.do_find)
        self.finder.sig_hide_finder_requested.connect(
            self.sig_hide_finder_requested)

        # Widget empty pane
        self.pane_empty = PaneEmptyWidget(
            self,
            "debugger",
            _("Debugging is not active"),
            _("Start a debugging session with the ⏯ button, allowing you to "
              "step through your code and see the functions here that "
              "Python has run.")
        )

        # Setup layout.
        self.stack_layout = QStackedLayout()
        self.stack_layout.addWidget(self.pane_empty)
        self.setLayout(self.stack_layout)
        self.stack_layout.setContentsMargins(0, 0, 0, 0)
        self.stack_layout.setSpacing(0)
        self.setContentsMargins(0, 0, 0, 0)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.results_browser)
        layout.addWidget(self.finder)

        self.container = QWidget(self)
        self.container.setLayout(layout)
        self.stack_layout.addWidget(self.container)

    def _show_frames(self, stack_dict, title, state):
        """Set current frames"""
        # Reset defaults
        self._persistence = -1  # survive to the next prompt
        self.state = state
        self.pdb_curindex = None

        if self.results_browser is not None:
            if stack_dict is not None:
                self.set_pane_empty(False)
            else:
                self.set_pane_empty(True)
            self.results_browser.set_frames(stack_dict)
            self.results_browser.set_title(title)
            try:
                self.results_browser.sig_activated.disconnect(
                    self.set_pdb_index)
            except (TypeError, RuntimeError):
                pass

    def set_pdb_index(self, index):
        """Set pdb index"""
        if self.pdb_curindex is None:
            return
        delta_index = self.pdb_curindex - index
        if delta_index > 0:
            command = "up " + str(delta_index)
        elif delta_index < 0:
            command = "down " + str(-delta_index)
        else:
            # Don't move
            return
        self.shellwidget.pdb_execute_command(command)

    def set_from_pdb(self, pdb_stack, curindex):
        """Set frames from pdb stack"""
        depth = self.shellwidget.debugging_depth()
        # Crop old state
        self._pdb_state = self._pdb_state[:depth - 1]
        while len(self._pdb_state) < depth - 1:
            # Missing data
            self._pdb_state.append(None)
        self._pdb_state.append((pdb_stack, curindex))

    def show_pdb(self, pdb_stack, curindex):
        """Show pdb frames."""
        self._show_frames(
            {_("Frames"): pdb_stack},
            _("Debugger stack"),
            FramesBrowserState.Debug,
        )
        self._persistence = 0
        self.pdb_curindex = curindex
        self.set_current_item(0, curindex)
        self.results_browser.sig_activated.connect(
            self.set_pdb_index)
        self.sig_update_actions_requested.emit()

    def show_exception(self, etype, error, tb):
        """Set frames from exception"""
        self._show_frames(
            {etype: tb}, _("Exception occured"),
            FramesBrowserState.Error)
        self.sig_update_actions_requested.emit()

    def show_captured_frames(self, stack_dict):
        """Set from captured frames"""
        self._show_frames(
            stack_dict, _("Snapshot of frames"), FramesBrowserState.Inspect
        )
        self.sig_update_actions_requested.emit()

    def show_pdb_preview(self, stack_dict):
        """Set from captured frames"""
        if "MainThread" in stack_dict:
            stack_dict = {_("Waiting for debugger"): stack_dict["MainThread"]}
        self._show_frames(
            stack_dict,
            _("Waiting for debugger"),
            FramesBrowserState.DebugWait
        )
        # Disappear immediately
        self._persistence = 0
        self.sig_update_actions_requested.emit()

    def clear_if_needed(self):
        """Execution finished. Clear if it is relevant."""

        # If debugging, show the state if we have it
        if self.shellwidget.is_debugging():
            depth = self.shellwidget.debugging_depth()
            if len(self._pdb_state) > depth - 1:
                pdb_state = self._pdb_state[depth - 1]
                if pdb_state:
                    self.show_pdb(*pdb_state)
                    self._persistence = 0
                    return

        # Otherwise check persistance
        if self._persistence == 0:
            self._show_frames(None, "", None)
            self.sig_update_actions_requested.emit()
        elif self._persistence > 0:
            self._persistence -= 1

    def set_current_item(self, top_idx, sub_index):
        """Set current item"""
        if self.results_browser is not None:
            self.results_browser.set_current_item(top_idx, sub_index)

    def on_config_kernel(self):
        """Ask shellwidget to send Pdb configuration to kernel."""
        self.shellwidget.set_kernel_configuration("pdb", {
            'breakpoints': self.get_conf("breakpoints", default={}),
            'pdb_ignore_lib': self.get_conf('pdb_ignore_lib'),
            'pdb_execute_events': self.get_conf('pdb_execute_events'),
            'pdb_use_exclamation_mark': self.get_conf(
                'pdb_use_exclamation_mark'),
            'pdb_stop_first_line': self.get_conf('pdb_stop_first_line'),
            'pdb_publish_stack': True,
        })

    def on_unconfig_kernel(self):
        """Ask shellwidget to stop sending stack."""
        if not self.shellwidget.spyder_kernel_ready:
            return
        self.shellwidget.set_kernel_configuration(
            "pdb", {'pdb_publish_stack': False}
        )

    @on_conf_change(option='pdb_ignore_lib')
    def change_pdb_ignore_lib(self, value):
        self.shellwidget.set_kernel_configuration(
            "pdb", {
            'pdb_ignore_lib': value
        })

    @on_conf_change(option='pdb_execute_events')
    def change_pdb_execute_events(self, value):
        self.shellwidget.set_kernel_configuration(
            "pdb", {
            'pdb_execute_events': value
        })

    @on_conf_change(option='pdb_use_exclamation_mark')
    def change_pdb_use_exclamation_mark(self, value):
        self.shellwidget.set_kernel_configuration(
            "pdb", {
            'pdb_use_exclamation_mark': value
        })

    @on_conf_change(option='pdb_stop_first_line')
    def change_pdb_stop_first_line(self, value):
        self.shellwidget.set_kernel_configuration(
            "pdb", {
            'pdb_stop_first_line': value
        })

    def set_breakpoints(self):
        """Set current breakpoints."""
        self.shellwidget.set_kernel_configuration(
            "pdb", {
            'breakpoints': self.get_conf(
                "breakpoints", default={}, section='debugger')
        })


class LineFrameItem(QTreeWidgetItem, SpyderFontsMixin):

    def __init__(self, parent, index, filename, line, lineno, name):
        self.index = index
        self.filename = filename
        self.text = line
        self.lineno = lineno
        self.context = name
        QTreeWidgetItem.__init__(
            self, parent, [self.__repr__()], QTreeWidgetItem.Type
        )

    def __repr__(self):
        """Print item as html."""
        text_color = SpyderPalette.COLOR_TEXT_1
        idle = _("Idle")

        if self.filename is None:
            return f'<p><span style="color:{text_color}">{idle}</span></p>'

        fname = html.escape(osp.basename(self.filename))
        formatted_text = (
            f"<p style=\"color:'{text_color}';\">"
            f"<b>{fname}</b> ({self.lineno}): "
        )

        monospace_font = self.get_font(SpyderFontType.Monospace).family()
        formatted_text += (
            f"<span style=\"font-family:{monospace_font};\">"
            f"{self.text}"
            f"</span>"
        )

        if self.context:
            scope = _("Scope")
            formatted_text += (
                f"&nbsp;&nbsp;&nbsp;&#8212;&nbsp;&nbsp;&nbsp;"
                f"{scope}: {html.escape(self.context)}</p>"
            )
        else:
            formatted_text += "</p>"

        return formatted_text

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

    def __init__(self, parent, name):
        self.name = str(name)
        text_color = SpyderPalette.COLOR_TEXT_1

        title_format = str(
            '<!-- ThreadItem -->'
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

        # This needs to be an empty string to avoid overlapping the
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

    def __init__(self, parent):
        super().__init__(parent)
        self.data = None
        self.threads = None
        self.text_color = SpyderPalette.COLOR_TEXT_1
        self.stack_dict = None

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

    @Slot(int)
    def sort_section(self, idx):
        """Sort section"""
        self.setSortingEnabled(True)

    def set_current_item(self, top_idx, sub_index):
        """Set current item."""
        item = self.topLevelItem(top_idx).child(sub_index)
        self.setCurrentItem(item)

    def set_frames(self, stack_dict):
        """Set frames."""
        self.clear()
        self.threads = {}
        self.data = {}
        self.stack_dict = stack_dict

        if stack_dict is None:
            return

        for thread_id, stack in stack_dict.items():
            parent = ThreadItem(self, thread_id)
            parent.setExpanded(True)
            self.threads[thread_id] = parent

            if stack:
                for idx, frame in enumerate(stack):
                    item = LineFrameItem(
                        parent,
                        idx,
                        frame["filename"],
                        frame["line"],
                        frame["lineno"],
                        frame["name"],
                    )
                    self.data[id(item)] = (frame["filename"], frame["lineno"])
            else:
                item = LineFrameItem(
                    parent, 0, None, '', 0, '', None,
                )

    def do_find(self, text):
        """Update the regex text for the variable finder."""
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
