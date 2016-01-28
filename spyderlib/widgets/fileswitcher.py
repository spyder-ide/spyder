# -*- coding: utf-8 -*-
#
# Copyright © 2009- The Spyder Development Team
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

from __future__ import print_function

import os
import os.path as osp

from spyderlib.qt.QtGui import (QDialog, QHBoxLayout, QIcon, QLabel, QLineEdit,
                                QListWidget, QListWidgetItem, QRegExpValidator,
                                QTextCursor, QVBoxLayout)
from spyderlib.qt.QtCore import Signal, QEvent, QObject, QRegExp, QSize, Qt

# Local imports
from spyderlib.config.base import _
from spyderlib.py3compat import iteritems, to_text_string
from spyderlib.utils import icon_manager as ima
from spyderlib.utils.stringmatching import get_search_scores
from spyderlib.widgets.helperwidgets import HelperToolButton, HTMLDelegate


# --- Python Outline explorer helpers
def process_python_symbol_data(oedata):
    """Returns a list with line number, definition name, fold and token."""
    symbol_list = []
    for key in oedata:
        val = oedata[key]
        if val and key != 'found_cell_separators':
            if val.is_class_or_function():
                symbol_list.append((key, val.def_name, val.fold_level,
                                    val.get_token()))
    return sorted(symbol_list)


def get_python_symbol_icons(oedata):
    """Return a list of icons for oedata of a python file."""
    class_icon = ima.icon('class')
    method_icon = ima.icon('method')
    function_icon = ima.icon('function')
    private_icon = ima.icon('private1')
    super_private_icon = ima.icon('private2')

    symbols = process_python_symbol_data(oedata)

    # line - 1, name, fold level
    fold_levels = sorted(list(set([s[2] for s in symbols])))
    parents = [None]*len(symbols)
    icons = [None]*len(symbols)
    indexes = []

    parent = None
    for level in fold_levels:
        for index, item in enumerate(symbols):
            line, name, fold_level, token = item
            if index in indexes:
                continue

            if fold_level == level:
                indexes.append(index)
                parent = item
            else:
                parents[index] = parent

    for index, item in enumerate(symbols):
        parent = parents[index]

        if item[-1] == 'def':
            icons[index] = function_icon
        elif item[-1] == 'class':
            icons[index] = class_icon
        else:
            icons[index] = QIcon()

        if parent is not None:
            if parent[-1] == 'class':
                if item[-1] == 'def' and item[1].startswith('__'):
                    icons[index] = super_private_icon
                elif item[-1] == 'def' and item[1].startswith('_'):
                    icons[index] = private_icon
                else:
                    icons[index] = method_icon

    return icons


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
        sep = os.sep

        # If toks are all empty we need not have recursed here
        if not any(level_idx.values()):
            return

        # Firstly, find the longest common prefix for all in the level
        # s = len of longest common prefix
        sample_toks = list(level_idx.values())[0]
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
                short_form = sample_toks[0] + sep + sample_toks[1]
            else:
                short_form = "..." + sep + sample_toks[s-1]
            for idx in level_idx:
                new_path_list[idx] += short_form + sep
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
                _, sample_toks = next(iteritems(group))
                prospective_group = {idx: toks for idx, toks
                                     in group.items()
                                     if toks[k] == sample_toks[k]}
                if len(prospective_group) == len(group) or k == 0:
                    group = prospective_group
                    k += 1
                else:
                    break
            _, sample_toks = next(iteritems(group))
            if k == 0:
                short_form = ''
            elif k == 1:
                short_form = sample_toks[0]
            elif k == 2:
                short_form = sample_toks[0] + sep + sample_toks[1]
            else:  # k > 2
                short_form = sample_toks[0] + "..." + sep + sample_toks[k-1]
            for idx in group.keys():
                new_path_list[idx] += short_form + (sep if k > 0 else '')
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
    sig_goto_file = Signal(int)
    sig_close_file = Signal(int)

    # Constants that define the mode in which the list widget is working
    # FILE_MODE is for a list of files, SYMBOL_MODE if for a list of symbols
    # in a given file when using the '@' symbol.
    FILE_MODE, SYMBOL_MODE = [1, 2]

    def __init__(self, parent, tabs, data):
        QDialog.__init__(self, parent)

        # Variables
        self.tabs = tabs                  # Editor stack tabs
        self.data = data                  # Editor data
        self.mode = self.FILE_MODE        # By default start in this mode
        self.initial_cursors = None       # {fullpath: QCursor}
        self.initial_path = None          # Fullpath of initial active editor
        self.initial_editor = None        # Initial active editor
        self.line_number = None           # Selected line number in filer

        help_text = _("Press <b>Enter</b> to switch files or <b>Esc</b> to "
                      "cancel.<br><br>Type to filter filenames.<br><br>"
                      "Use <b>:number</b> to go to a line, e.g. "
                      "<b><code>main:42</code></b><br>"
                      "Use <b>@symbol_text</b> to go to a symbol, e.g. "
                      "<b><code>@init</code></b>"
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

        # Layout
        edit_layout = QHBoxLayout()
        edit_layout.addWidget(self.edit)
        edit_layout.addWidget(self.help)
        layout = QVBoxLayout()
        layout.addLayout(edit_layout)
        layout.addWidget(self.list)
        self.setLayout(layout)

        # Signals
        self.rejected.connect(self.restore_initial_state)
        self.filter.sig_up_key_pressed.connect(self.previous_row)
        self.filter.sig_down_key_pressed.connect(self.next_row)
        self.edit.returnPressed.connect(self.accept)
        self.edit.textChanged.connect(self.setup)
        self.list.itemSelectionChanged.connect(self.item_selection_changed)
        self.list.clicked.connect(self.edit.setFocus)

        # Setup
        self.save_initial_state()
        self.set_dialog_position()
        self.setup()

    # --- Properties
    @property
    def editors(self):
        return [self.tabs.widget(index) for index in range(self.tabs.count())]

    @property
    def line_count(self):
        return [editor.get_line_count() for editor in self.editors]

    @property
    def save_status(self):
        return [getattr(td, 'newly_created', False) for td in self.data]

    @property
    def paths(self):
        return [getattr(td, 'filename', None) for td in self.data]

    @property
    def filenames(self):
        return [self.tabs.tabText(index) for index in range(self.tabs.count())]

    @property
    def current_path(self):
        return self.paths_by_editor[self.get_editor()]

    @property
    def paths_by_editor(self):
        return dict(zip(self.editors, self.paths))

    @property
    def editors_by_path(self):
        return dict(zip(self.paths, self.editors))

    @property
    def filter_text(self):
        """Get the normalized (lowecase) content of the filter text."""
        return to_text_string(self.edit.text()).lower()

    def save_initial_state(self):
        """Saves initial cursors and initial active editor."""
        paths = self.paths
        self.initial_editor = self.get_editor()
        self.initial_cursors = {}

        for i, editor in enumerate(self.editors):
            if editor is self.initial_editor:
                self.initial_path = paths[i]
            self.initial_cursors[paths[i]] = editor.textCursor()

    def accept(self):
        QDialog.accept(self)
        self.list.clear()

    def restore_initial_state(self):
        """Restores initial cursors and initial active editor."""
        self.list.clear()
        editors = self.editors_by_path

        for path in self.initial_cursors:
            cursor = self.initial_cursors[path]
            if path in editors:
                self.set_editor_cursor(editors[path], cursor)

        if self.initial_editor in self.paths_by_editor:
            index = self.paths.index(self.initial_path)
            self.sig_goto_file.emit(index)

    def set_dialog_position(self):
        """Positions the file switcher dialog in the center of the editor."""
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

    def fix_size(self, content, extra=50):
        """Adjusts the width of the file switcher, based on the content."""
        # Update size of dialog based on longest shortened path
        strings = []
        if content:
            for rich_text in content:
                label = QLabel(rich_text)
                label.setTextFormat(Qt.PlainText)
                strings.append(label.text())
                fm = label.fontMetrics()
            max_width = max([fm.width(s)*1.3 for s in strings])
            self.list.setMinimumWidth(max_width + extra)
            self.set_dialog_position()

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

    # --- Helper methods: Editor
    def get_editor(self, index=None, path=None):
        """Get editor by index or path.
        
        If no path or index specified the current active editor is returned
        """
        if index:
            return self.tabs.widget(index)
        elif path:
            return self.tabs.widget(index)
        else:
            return self.parent().get_current_editor()

    def set_editor_cursor(self, editor, cursor):
        """Set the cursor of an editor."""
        pos = cursor.position()
        anchor = cursor.anchor()

        new_cursor = QTextCursor()
        if pos == anchor:
            new_cursor.movePosition(pos)
        else:
            new_cursor.movePosition(anchor)
            new_cursor.movePosition(pos, QTextCursor.KeepAnchor)
        editor.setTextCursor(cursor)

    def goto_line(self, line_number):
        """Go to specified line number in current active editor."""
        if line_number:
            line_number = int(line_number)
            editor = self.get_editor()
            editor.go_to_line(min(line_number, editor.get_line_count()))

    # --- Helper methods: Outline explorer
    def get_symbol_list(self):
        """Get the object explorer data."""
        return self.get_editor().highlighter.get_outlineexplorer_data()

    # --- Handlers
    def item_selection_changed(self):
        """List widget item selection change handler."""
        row = self.current_row()
        if self.count() and row >= 0:
            if self.mode == self.FILE_MODE:
                try:
                    stack_index = self.paths.index(self.filtered_path[row])
                    self.sig_goto_file.emit(stack_index)
                    self.goto_line(self.line_number)
                    self.edit.setFocus()
                except ValueError:
                    pass
            else:
                line_number = self.filtered_symbol_lines[row]
                self.goto_line(line_number)

    def setup_file_list(self, filter_text, current_path):
        """Setup list widget content for file list display."""
        short_paths = shorten_paths(self.paths, self.save_status)
        paths = self.paths
        results = []
        trying_for_line_number = ':' in filter_text

        # Get optional line number
        if trying_for_line_number:
            filter_text, line_number = filter_text.split(':')
        else:
            line_number = None

        # Get all available filenames and get the scores for "fuzzy" matching
        scores = get_search_scores(filter_text, self.filenames,
                                   template="<b>{0}</b>")

        # Build the text that will appear on the list widget
        for index, score in enumerate(scores):
            text, rich_text, score_value = score
            if score_value != -1:
                text_item = '<big>' + rich_text + '</big>'
                if trying_for_line_number:
                    text_item += " [{0:} {1:}]".format(self.line_count[index],
                                                       _("lines"))
                text_item += "<br><i>{0:}</i>".format(
                    short_paths[index])

                results.append((score_value, index, text_item))

        # Sort the obtained scores and populate the list widget
        self.filtered_path = []
        for result in sorted(results):
            index = result[1]
            text = result[-1]
            path = paths[index]
            item = QListWidgetItem(self.tabs.tabIcon(index), text)
            item.setToolTip(path)
            item.setSizeHint(QSize(0, 25))
            self.list.addItem(item)
            self.filtered_path.append(path)

        # Move selected item in list accordingly and update list size
        if current_path in self.filtered_path:
            self.set_current_row(self.filtered_path.index(current_path))
        elif self.filtered_path:
            self.set_current_row(0)
        self.fix_size(short_paths)

        # If a line number is searched look for it
        self.line_number = line_number
        self.goto_line(line_number)

    def setup_symbol_list(self, filter_text, current_path):
        """Setup list widget content for symbol list display."""
        # Get optional symbol name
        filter_text, symbol_text = filter_text.split('@')

        # Fetch the Outline explorer data, get the icons and values
        oedata = self.get_symbol_list()
        icons = get_python_symbol_icons(oedata)

        symbol_list = process_python_symbol_data(oedata)
        line_fold_token = [(item[0], item[2], item[3]) for item in symbol_list]
        choices = [item[1] for item in symbol_list]
        scores = get_search_scores(symbol_text, choices, template="<b>{0}</b>")

        # Build the text that will appear on the list widget
        results = []
        lines = []
        self.filtered_symbol_lines = []
        for index, score in enumerate(scores):
            text, rich_text, score_value = score
            line, fold_level, token = line_fold_token[index]
            lines.append(text)
            if score_value != -1:
                results.append((score_value, line, text, rich_text,
                                fold_level, icons[index], token))

        template_1 = '<code>{0}<big>{1} {2}</big></code>'
        template_2 = '<br><code>{0}</code><i>[Line {1}]</i>'

        for (score, line, text, rich_text, fold_level, icon,
             token) in sorted(results):
            fold_space = '&nbsp;'*(fold_level)
            line_number = line + 1
            self.filtered_symbol_lines.append(line_number)
            textline = template_1.format(fold_space, token, rich_text)
            textline += template_2.format(fold_space, line_number)
            item = QListWidgetItem(icon, textline)
            item.setSizeHint(QSize(0, 16))
            self.list.addItem(item)

        # Move selected item in list accordingly
        # NOTE: Doing this is causing two problems:
        # 1. It makes the cursor to auto-jump to the last selected
        #    symbol after opening or closing a different file
        # 2. It moves the cursor to the first symbol by default,
        #    which is very distracting.
        # That's why this line is commented!
        # self.set_current_row(0)

        # Update list size
        self.fix_size(lines, extra=125)

    def setup(self):
        """Setup list widget content."""
        if not self.tabs.count():
            self.close()
            return

        self.list.clear()
        current_path = self.current_path
        filter_text = self.filter_text

        # Get optional line or symbol to define mode and method handler
        trying_for_symbol = ('@' in self.filter_text)

        if trying_for_symbol:
            self.mode = self.SYMBOL_MODE
            self.setup_symbol_list(filter_text, current_path)
        else:
            self.mode = self.FILE_MODE
            self.setup_file_list(filter_text, current_path)
