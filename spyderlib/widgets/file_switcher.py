# -*- coding: utf-8 -*-
#
# Copyright © 2013-2015 The Spyder Development Team
# Copyright © 2015 Daniel Manson (@d1manson)
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

from __future__ import print_function
import os
import os.path as osp

from spyderlib.qt.QtCore import Signal, Qt, QObject, QSize, QEvent, QRegExp
from spyderlib.qt.QtGui import (QVBoxLayout, QHBoxLayout,
                                QListWidget, QListWidgetItem,
                                QDialog, QLineEdit, QRegExpValidator)

# Local imports
from spyderlib.config.base import _
from spyderlib.config.gui import new_shortcut
from spyderlib.py3compat import to_text_string
from spyderlib.utils import icon_manager as ima
from spyderlib.utils.stringmatching import get_search_scores
from spyderlib.widgets.helperwidgets import HelperToolButton, HTMLDelegate


def shorten_paths(path_list, is_unsaved):
    """
    Takes a list of paths and tries to "intelligently" shorten them all. The
    aim is to make it clear to the user where the paths differ, as that is
    likely what they care about. Note that this operates on a list of paths
    not on individual paths.

    If the path ends in an actual file name, it will be trimmed off.
    """
    # TODO: at the end, if the path is too long, should do a more dumb kind of
    # shortening, but not completely dumb.

    # Convert the path strings to a list of tokens and start building the
    # new_path using the drive
    path_list = path_list[:]  # Make a local copy
    new_path_list = []

    for ii, (path, is_unsav) in enumerate(zip(path_list, is_unsaved)):
        if is_unsav:
            new_path_list.append(_('unsaved file'))
            path_list[ii] = None
        else:
            drive, path = osp.splitdrive(osp.dirname(path))
            new_path_list.append(drive + osp.sep)
            path_list[ii] = [part for part in path.split(osp.sep) if part]

    def recurse_level(level_idx):
        # If toks are all empty we need not have recursed here
        if not any(level_idx.values()):
            return

        # Firstly, find the longest common prefix for all in the level
        # s = len of longest common prefix
        sample_toks = level_idx.values()[0]
        if not sample_toks:
            s = 0
        else:
            for s, sample_val in enumerate(sample_toks):
                if not all(len(toks) > s and toks[s] == sample_val
                           for toks in level_idx.values()):
                    break

        # Shorten longest common prefix
        if s == 0:
            short_form = ''
        else:
            if s == 1:
                short_form = sample_toks[0]
            elif s == 2:
                short_form = sample_toks[0] + os.sep + sample_toks[1]
            else:
                short_form = "..." + os.sep + sample_toks[s-1]
            for idx in level_idx:
                new_path_list[idx] += short_form + os.sep
                level_idx[idx] = level_idx[idx][s:]

        # Group the remaining bit after the common prefix, shorten, and recurse
        while level_idx:
            k, group = 0, level_idx  # k is length of the group's common prefix
            while True:
                # Abort if we've gone beyond end of one or more in the group
                prospective_group = {idx: toks for idx, toks
                                     in group.items() if len(toks) == k}
                if prospective_group:
                    if k == 0:  # we spit out the group with no suffix
                        group = prospective_group
                    break
                # Only keep going if all n still match on the kth token
                _, sample_toks = next(group.iteritems())
                prospective_group = {idx: toks for idx, toks
                                     in group.items()
                                     if toks[k] == sample_toks[k]}
                if len(prospective_group) == len(group) or k == 0:
                    group = prospective_group
                    k += 1
                else:
                    break
            _, sample_toks = next(group.iteritems())
            if k == 0:
                short_form = ''
            elif k == 1:
                short_form = sample_toks[0]
            elif k == 2:
                short_form = sample_toks[0] + os.sep + sample_toks[1]
            else:  # k > 2
                short_form = sample_toks[0] + "..." + os.sep + sample_toks[k-1]
            for idx in group.keys():
                new_path_list[idx] += short_form + (os.sep if k > 0 else '')
                del level_idx[idx]
            recurse_level({idx: toks[k:] for idx, toks in group.items()})

    recurse_level({i: pl for i, pl in enumerate(path_list) if pl})

    return [path.rstrip(os.sep) for path in new_path_list]


class KeyPressFilter(QObject):
    """
    Use with `installEventFilter` to get up/down arrow key press signal.
    """
    UP, DOWN = [-1, 1]  # Step constants

    sig_up_key_pressed = Signal()
    sig_down_key_pressed = Signal()

    def eventFilter(self, src, e):
        if e.type() == QEvent.KeyPress:
            if e.key() == Qt.Key_Up:
                self.sig_up_key_pressed.emit()
            elif e.key() == Qt.Key_Down:
                self.sig_down_key_pressed.emit()

        return super(KeyPressFilter, self).eventFilter(src, e)


class FileSwitcher(QDialog):
    """A Sublime-like file switcher."""
    sig_close_file = Signal(int)
    sig_goto_file = Signal(int)
    sig_goto_line = Signal(int)

    # Constants that define the mode in which the list widget is working
    # FILE_MODE is for a list of files, SYMBOL_MODE if for a list of symbols
    # in a given file
    FILE_MODE, SYMBOL_MODE = [1, 2]

    def __init__(self, parent, tabs, tab_data):
        QDialog.__init__(self, parent)

        # Variables
        self.tabs = tabs                     # Editor stack tabs
        self.tab_data = tab_data
        self.mode = self.FILE_MODE           # By default start in this mode

        self.filtered_index_to_line = None   # []
        self.original_path = None
        self.original_line_num = None
        self.full_index_to_path = None       # []
        self.filtered_index_to_path = None   # []
        self.path_to_line_count = None       # []
        self.line_number = -1
        self.line_number_modified_for_path = None
        help_text = _("Press <b>Enter</b> to switch files or <b>Esc</b> to "
                      "cancel.<br><br>Type to filter filenames.<br><br>"
                      "Use <b>:number</b> to go to a line, e.g. 'main:42'."
                      "<br><br> Press <b>Ctrl+W</b> to close current tab.<br>")
        # Either allow searching for a line number or a symbol but not both
        regex = QRegExp("([A-Za-z0-9_]{0,100}@[A-Za-z0-9_]{0,100})|" +
                        "([A-Za-z]{0,100}:{0,1}[0-9]{0,100})")

        # Widgets
        self.edit = QLineEdit(self)
        self.help = HelperToolButton()
        self.list = QListWidget(self)
        self.filter = KeyPressFilter()
        regex_validator = QRegExpValidator(regex, self.edit)

        # Widgets setup
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setWindowOpacity(0.95)

        self.edit.installEventFilter(self.filter)
        self.edit.setValidator(regex_validator)
        self.help.setToolTip(help_text)
        self.list.setItemDelegate(HTMLDelegate(self))

        def close_tab():
            self.sig_close_file.emit(
                 self.filtered_index_to_full(self.current_row()))

        new_shortcut("Ctrl+W", self, close_tab)

        # Layout
        edit_layout = QHBoxLayout()
        edit_layout.addWidget(self.edit)
        edit_layout.addWidget(self.help)

        layout = QVBoxLayout()
        layout.addLayout(edit_layout)
        layout.addWidget(self.list)

        self.setLayout(layout)

        # Signals
        self.sig_goto_line.connect(self.goto_line)
        self.rejected.connect(self.handle_reject)

        self.filter.sig_up_key_pressed.connect(self.previous_row)
        self.filter.sig_down_key_pressed.connect(self.next_row)

        self.edit.returnPressed.connect(self.goto_file)
        self.edit.textChanged.connect(lambda text: self.setup(None))
        self.list.itemSelectionChanged.connect(self.item_selection_changed)
        self.list.itemActivated.connect(self.goto_file)

    def handle_reject(self):
        """Qt override."""
        # This means there is no longer a current_path
        self.list.clear()

        # Reset line number for current tab, if it was changed
        self.sig_goto_line.emit(-1)

        # Reset tab choice, if it was changed
        if self.original_path is not None:
            index = self.full_index_to_path.index(self.original_path)
            target_tab_index = self.sig_goto_file.emit(index)
            self.sig_goto_file.emit(target_tab_index)

    def show(self, stack_index):
        """Qt override."""
        QDialog.show(self)

        edit = self.edit

        edit.setText("")
        self.setup(stack_index)

        edit.selectAll()
        edit.setFocus()
        self.set_position()

    def set_position(self):
        """ """
        parent = self.parent()
        geo = parent.geometry()
        width = self.list.width()  # This has been set in setup

        left = parent.geometry().width()/2 - width/2
        top = 0
        while parent:
            geo = parent.geometry()
            top += geo.top()
            left += geo.left()
            parent = parent.parent()

        # Note: the +1 pixel on the top makes it look better
        self.move(left, top + self.tabs.tabBar().geometry().height() + 1)

    # --- Helper methods: List widget
    def count(self):
        """Gets the item count in the list widget."""
        return self.list.count()

    def current_row(self):
        """Returns the current selected row in the list widget."""
        return self.list.currentRow()

    def set_current_row(self, row):
        """Sets the current selected row in the list widget."""
        return self.list.setCurrentRow(row)

    def select_row(self, steps):
        """Select row in list widget based on a number of steps with direction.

        Steps can be positive (next rows) or negative (previous rows).
        """
        row = self.current_row() + steps
        if 0 <= row < self.count():
            self.set_current_row(row)

    def previous_row(self):
        """Select previous row in list widget."""
        self.select_row(-1)

    def next_row(self):
        """Select next row in list widget."""
        self.select_row(+1)

    def current_path(self):
        """ """
        if self.mode == self.FILE_MODE:
            if self.current_row() >= 0:
                return self.filtered_index_to_path[self.current_row()]
            else:
                return None

    @property
    def filter_text(self):
        """Get the content of the line text edit holding the filter text."""
        return to_text_string(self.edit.text()).lower()

    # --- Helper methods: Editor
    def get_editor(self):
        """ """
        return self.parent().get_current_editor()

    def get_editor_filename(self, index):
        """ """
        return to_text_string(self.tabs.tabText(index))

    def get_editor_line_number(self, index=None):
        """ """
        if index:
            line_number = self.tabs.widget(index).get_cursor_line_number()
        else:
            editor = self.get_editor()
            line_number = editor.get_cursor_line_number()
        return line_number

    def get_editor_line_count(self, index=None):
        """ """
        if index:
            line_count = self.tabs.widget(index).get_line_count()
        else:
            editor = self.get_editor()
            line_count = editor.get_line_count()
        return line_count

    def goto_editor_line_number(self, line_number):
        """ """
        editor = self.get_editor()
        editor.go_to_line(min(line_number, self.get_editor_line_count()))

    # --- Helper methods: Outline explorer
    def get_symbol_list(self):
        """Get the object explorer data."""
        editor = self.get_editor()
        return editor.highlighter.get_outlineexplorer_data()

    # --- Handlers
    def filtered_index_to_full(self, idx):
        """
        Note we assume idx is valid and the two mappings are valid.
        """
        return self.full_index_to_path.index(self.filtered_index_to_path[idx])

    def goto_file(self):
        """ """
        row = self.current_row()
        if self.count() and row >= 0:
            if self.mode == self.FILE_MODE:
                self.sig_goto_file.emit(self.filtered_index_to_full(row))
            self.hide()

    def goto_line(self, line_number):
        """ """
        current_path = self.current_path()
        line_number_modified = self.line_number_modified_for_path

        # If we've changed path since last doing a goto line, we need to reset
        # that previous file
        if line_number_modified is not None and \
                current_path != line_number_modified:

            if line_number_modified in self.full_index_to_path:
                tab = self.tabs.widget(self.full_index_to_path.index(
                    line_number_modified))
                tab.go_to_line(self.original_line_num)

            self.line_number_modified_for_path = None
            self.original_line_num = None

        # Record it for use when switching items
        self.line_number = line_number

        # Apply the line num to the current file, recording the original
        # location if need be
        if line_number >= 0 and self.filtered_index_to_path:
            if self.original_line_num is None:
                self.original_line_num = self.get_editor_line_number()
                self.line_number_modified_for_path = current_path

            self.goto_editor_line_number(line_number)

    def item_selection_changed(self):
        """ """
        row = self.current_row()
        if self.count() and row >= 0:
            if self.mode == self.FILE_MODE:
                try:
                    self.sig_goto_file.emit(self.filtered_index_to_full(row))
                except ValueError:
                    pass
                # If this is -1 it does nothing
                self.sig_goto_line.emit(self.line_number)
            else:
                # TODO
                self.goto_editor_line_number(self.filtered_index_to_line[row])

    def setup_file_list(self, filter_text, current_path):
        """ """
        trying_for_line_number = ':' in filter_text

        # Get optional line number
        if trying_for_line_number:
            filter_text, line_number = filter_text.split(':', 1)
        else:
            filter_text, line_number = filter_text, ""

        try:
            line_number = int(line_number)
        except ValueError:
            line_number = -1

        # Cache line counts if we need now them
        if trying_for_line_number and self.path_to_line_count is None:
            self.path_to_line_count = {
                path: self.get_editor_line_count(index)
                for index, path in enumerate(self.full_index_to_path)}

        # Get all available filenames and get the scores for "fuzzy" matching
        choices = []
        paths = []
        for index, path in enumerate(self.full_index_to_path):
            choices.append(self.get_editor_filename(index))
            paths.append(path)
        scores = get_search_scores(filter_text, choices, template="<b>{0}</b>")

        # Build the text that will appear on the list widget
        results = []
        for index, score in enumerate(scores):
            text, rich_text, score_value = score
            if score_value != -1:
                text_item = '<big>' + rich_text + '</big>'
                if trying_for_line_number:
                    text_item += " [{0:} {1:}]".format(
                        self.path_to_line_count[paths[index]], _("lines"))
                text_item += "<br><i>{0:}</i>".format(
                    self.full_index_to_short_path[index])

                results.append((score_value, index, text_item))

        # Sort the obtained scores and populate the list widget
        for result in sorted(results):
            index = result[1]
            text = result[-1]
            path = self.full_index_to_path[index]
            item = QListWidgetItem(self.tabs.tabIcon(index), text)
            item.setToolTip(path)
            item.setSizeHint(QSize(0, 25))
            self.list.addItem(item)
            self.filtered_index_to_path.append(path)

        if (current_path is not None and
                current_path in self.filtered_index_to_path):
            self.set_current_row(
                self.filtered_index_to_path.index(current_path))
        elif self.filtered_index_to_path:
            self.set_current_row(0)
        self.sig_goto_line.emit(line_number)  # Note that line_num may =-1
        self.fix_size(self.full_index_to_short_path)

    def setup_symbol_list(self, filter_text, current_path):
        """ """
        # Get optional symbol name
        filter_text, symbol_text = filter_text.split('@', 1)
        oe_data = self.get_symbol_list()
        symbol_list = []
        for key in oe_data:
            val = oe_data[key]
            if val and val != 'found_cell_separators':
                if val.is_class_or_function():
                    symbol_list.append((key, val.get_full_name(),
                                        val.fold_level))

        # Get all available filenames and get the scores for "fuzzy" matching
        symbol_list = sorted(symbol_list)
        icons = get_symbol_icons(symbol_list)
        line_fold = [(item[0], item[2]) for item in symbol_list]
        choices = [item[1] for item in symbol_list]
        scores = get_search_scores(symbol_text, choices, template="<b>{0}</b>")

        # Build the text that will appear on the list widget
        results = []
        lines = []
        self.filtered_index_to_line = []
        for index, score in enumerate(scores):
            text, rich_text, score_value = score
            line, fold_level = line_fold[index]
            lines.append(text + ' '*(fold_level + 2))

            if score_value != -1:
                self.filtered_index_to_line.append(line + 1)
                results.append((score_value, line, text, rich_text,
                                fold_level, icons[index]))

        template_1 = '<code>{0}<big>{1}</big></code>'

        for score, line, text, rich_text, fold_level, icon in sorted(results):
            # The plus 2 is just to improve the appearance
            textline = template_1.format('&nbsp;'*(fold_level), rich_text)
            item = QListWidgetItem(icon, textline)
#            item.setToolTip(path)
            item.setSizeHint(QSize(0, 16))
            self.list.addItem(item)

        self.fix_size(lines, extra=120)

    def setup(self, stack_index):
        """
        stack_index is either an index into the tab list or None.
        """
        # Now that there is always at least one editor... this is perhaps not
        # needed
        count = self.tabs.count()
        if not count:
            self.hide()
            return

        if stack_index is not None:
            # Cache full paths, and short paths and invalidate line counts
            self.full_index_to_path = [getattr(td, 'filename', None)
                                       for td in self.tab_data]
            current_path = self.original_path = \
                self.full_index_to_path[stack_index]
            full_index_to_is_unsaved = [getattr(td, 'newly_created', False)
                                        for td in self.tab_data]
            self.full_index_to_short_path = \
                shorten_paths(self.full_index_to_path,
                              full_index_to_is_unsaved)
            self.path_to_line_count = None  # We only get this on demand
        else:
            current_path = self.current_path()  # Could be None

        # Get filter text
        filter_text = self.filter_text

        # Get optional line or symbol to define mode and method handler
        trying_for_symbol = ('@' in filter_text)

        self.list.clear()
        self.filtered_index_to_path = []

        if trying_for_symbol:
            self.mode = self.SYMBOL_MODE
            self.setup_symbol_list(filter_text, current_path)
        else:
            self.mode = self.FILE_MODE
            self.setup_file_list(filter_text, current_path)

    def fix_size(self, content, extra=50):
        """ """
        # Update size of dialog based on longest shortened path
        if content:
            fm = self.list.fontMetrics()
            max_width = max([fm.width(l) for l in content])
            self.list.setMinimumWidth(max_width + extra)
            self.set_position()


def get_symbol_icons(symbols):
    """ """
    class_icon = ima.icon('class')
    method_icon = ima.icon('method')
    function_icon = ima.icon('function')
    private_icon = ima.icon('private1')
    super_private_icon = ima.icon('private2')

    # line-1, name, fold level
    fold_levels = sorted(list(set([s[-1] for s in symbols])))
    parents = [None]*len(symbols)
    icons = [None]*len(symbols)
    indexes = []
    for level in fold_levels:
        for index, item in enumerate(symbols):
            line, name, fold_level = item
            if index in indexes:
                continue

            if fold_level == level:
                indexes.append(index)
                parent = item
            else:
                parents[index] = parent

    for index, item in enumerate(symbols):
        parent = parents[index]
        if item[1].startswith('def '):
            icons[index] = function_icon
        elif item[1].startswith('class '):
            icons[index] = class_icon

        if parent is not None:
            if parent[1].startswith('class '):
                if item[1].startswith('def __'):
                    icons[index] = super_private_icon
                elif item[1].startswith('def _'):
                    icons[index] = private_icon
                else:
                    icons[index] = method_icon
    return icons
